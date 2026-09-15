import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.database import ChatMessage, ChatSession, Paper, ResearchProject
from app.models.schemas import ChatMessageOut, ChatQueryRequest, ChatResponse, CitationItem
from app.services.llm_service import LLMService
from app.services.operations_service import OperationsService
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/api/chat", tags=["Paper & Collection Chat (RAG)"])
retrieval_service = RetrievalService()
llm_service = LLMService()


def _get_or_create_session(
    db: Session, session_id: Optional[int], scope_type: str, scope_id: Optional[int], default_title: str
) -> ChatSession:
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            return session
    session = ChatSession(
        scope_type=scope_type,
        scope_id=scope_id,
        title=default_title[:200],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/paper/{paper_id}", response_model=ChatResponse, summary="Chat with Individual Paper")
async def chat_with_paper(
    paper_id: int,
    payload: ChatQueryRequest,
    db: Session = Depends(get_db),
):
    """Ask a question about a single paper and receive grounded answer with exact page/section citations."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    await _ensure_paper_abstract(db, paper)

    session = _get_or_create_session(
        db, payload.session_id, "paper", paper_id, f"Chat: {paper.title}"
    )

    # 1. Retrieve top relevant chunks for this paper
    citations = retrieval_service.retrieve(
        db=db,
        query=payload.question,
        paper_ids=[paper_id],
        top_k=4,
    )

    # 2. Generate grounded answer
    answer = await llm_service.answer_question(payload.question, citations)

    # 3. Store conversation messages
    user_msg = ChatMessage(session_id=session.id, role="user", content=payload.question)
    citations_data = [c.model_dump() for c in citations]
    bot_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        citations_json=json.dumps(citations_data),
    )
    db.add(user_msg)
    db.add(bot_msg)
    db.commit()

    OperationsService.record_audit(db, "chat_paper", "paper", str(paper_id), payload.question[:100])

    return ChatResponse(
        session_id=session.id,
        question=payload.question,
        answer=answer,
        citations=citations,
    )


async def _ensure_paper_abstract(db: Session, paper: Paper) -> None:
    """Backfill abstract from OpenAlex/Crossref when library record has none, then index it for RAG."""
    if (paper.abstract or "").strip():
        retrieval_service.ensure_abstract_chunk(db, paper)
        return

    if not paper.doi and not paper.title:
        return

    from app.services.crossref_service import CrossrefService
    from app.services.openalex_service import OpenAlexService

    fetched = None
    if paper.doi:
        oa = OpenAlexService()
        fetched = await oa.fetch_by_doi(paper.doi)
        if not fetched or not (fetched.abstract or "").strip():
            cr = CrossrefService()
            cr_paper = await cr.fetch_by_doi(paper.doi)
            if cr_paper and (cr_paper.abstract or "").strip():
                fetched = cr_paper
            elif fetched is None:
                fetched = cr_paper

        # Same title often has an OA abstract on another DOI (e.g. Zenodo mirror)
        if (not fetched or not (fetched.abstract or "").strip()) and paper.title:
            for candidate in await oa.search_papers(paper.title[:90]):
                if (candidate.abstract or "").strip():
                    fetched = candidate
                    break

    if fetched and (fetched.abstract or "").strip():
        paper.abstract = fetched.abstract.strip()
        if fetched.venue and not paper.venue:
            paper.venue = fetched.venue
        if fetched.pdf_url and not paper.pdf_url:
            paper.pdf_url = fetched.pdf_url
            paper.open_access = bool(fetched.open_access)
        db.commit()
        db.refresh(paper)
        retrieval_service.ensure_abstract_chunk(db, paper)


@router.post("/project/{project_id}", response_model=ChatResponse, summary="Chat with Project Collection")
async def chat_with_project(
    project_id: int,
    payload: ChatQueryRequest,
    db: Session = Depends(get_db),
):
    """Ask questions across all papers saved in a project workspace with cross-paper citations."""
    project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    session = _get_or_create_session(
        db, payload.session_id, "project", project_id, f"Project Chat: {project.name}"
    )

    citations = retrieval_service.retrieve(
        db=db,
        query=payload.question,
        project_id=project_id,
        top_k=6,
    )

    answer = await llm_service.answer_question(payload.question, citations)

    user_msg = ChatMessage(session_id=session.id, role="user", content=payload.question)
    bot_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        citations_json=json.dumps([c.model_dump() for c in citations]),
    )
    db.add(user_msg)
    db.add(bot_msg)
    db.commit()

    return ChatResponse(
        session_id=session.id,
        question=payload.question,
        answer=answer,
        citations=citations,
    )


@router.post("/library", response_model=ChatResponse, summary="Chat with Entire Research Library")
async def chat_with_library(
    payload: ChatQueryRequest,
    db: Session = Depends(get_db),
):
    """Ask questions across all saved papers in the user library."""
    session = _get_or_create_session(
        db, payload.session_id, "library", None, "Library-wide Synthesis Chat"
    )

    citations = retrieval_service.retrieve(
        db=db,
        query=payload.question,
        paper_ids=payload.paper_ids,
        top_k=6,
    )

    answer = await llm_service.answer_question(payload.question, citations)

    user_msg = ChatMessage(session_id=session.id, role="user", content=payload.question)
    bot_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        citations_json=json.dumps([c.model_dump() for c in citations]),
    )
    db.add(user_msg)
    db.add(bot_msg)
    db.commit()

    return ChatResponse(
        session_id=session.id,
        question=payload.question,
        answer=answer,
        citations=citations,
    )


@router.get("/{session_id}/messages", response_model=List[ChatMessageOut], summary="Get Chat Session History")
async def get_chat_messages(session_id: int, db: Session = Depends(get_db)):
    """Retrieve full message history and citations for a chat session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    results = []
    for m in msgs:
        raw_cites = json.loads(m.citations_json or "[]")
        cites = [CitationItem(**c) for c in raw_cites]
        results.append(
            ChatMessageOut(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                citations=cites,
                created_at=m.created_at,
            )
        )
    return results
