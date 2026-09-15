import json
import logging
import re
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.database import Paper, PaperChunk, ProjectPaper
from app.models.schemas import CitationItem
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

_ABSTRACT_SNIPPET_LIMIT = 1600
_CHUNK_SNIPPET_LIMIT = 500


class RetrievalService:
    """Retrieves contextually relevant chunks across papers using vector similarity."""

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedding_service = embedding_service or EmbeddingService()

    def retrieve(
        self,
        db: Session,
        query: str,
        paper_ids: Optional[List[int]] = None,
        project_id: Optional[int] = None,
        top_k: int = 5,
    ) -> List[CitationItem]:
        """Perform semantic vector retrieval over indexed paper chunks."""
        query_vec = self.embedding_service.embed_text(query)

        chunk_query = db.query(PaperChunk, Paper).join(Paper, Paper.id == PaperChunk.paper_id)

        if project_id:
            chunk_query = chunk_query.join(ProjectPaper, ProjectPaper.paper_id == Paper.id).filter(
                ProjectPaper.project_id == project_id
            )
        elif paper_ids:
            chunk_query = chunk_query.filter(PaperChunk.paper_id.in_(paper_ids))

        chunks_with_papers = chunk_query.all()
        if not chunks_with_papers:
            return self._fallback_metadata_search(db, query, paper_ids, project_id, top_k)

        scored = []
        for chunk, paper in chunks_with_papers:
            if not chunk.embedding_json:
                continue
            try:
                c_vec = json.loads(chunk.embedding_json)
                sim = self.embedding_service.cosine_similarity(query_vec, c_vec)
                scored.append((sim, chunk, paper))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[CitationItem] = []

        for sim, chunk, paper in scored[:top_k]:
            content = chunk.content or ""
            limit = _ABSTRACT_SNIPPET_LIMIT if (chunk.section or "").lower() == "abstract" else _CHUNK_SNIPPET_LIMIT
            results.append(
                CitationItem(
                    paper_id=paper.id,
                    paper_title=paper.title,
                    doi=paper.doi,
                    page=chunk.page_number,
                    section=chunk.section,
                    snippet=content[:limit] + ("..." if len(content) > limit else ""),
                )
            )

        # If vector hits are weak / empty, still surface abstracts for scoped papers
        if not results:
            return self._fallback_metadata_search(db, query, paper_ids, project_id, top_k)

        return results

    def _fallback_metadata_search(
        self,
        db: Session,
        query: str,
        paper_ids: Optional[List[int]],
        project_id: Optional[int],
        top_k: int,
    ) -> List[CitationItem]:
        """Fallback when PDFs have not yet been uploaded/indexed — use abstracts/titles."""
        pq = db.query(Paper)
        if project_id:
            pq = pq.join(ProjectPaper, ProjectPaper.paper_id == Paper.id).filter(
                ProjectPaper.project_id == project_id
            )
        elif paper_ids:
            pq = pq.filter(Paper.id.in_(paper_ids))

        papers = pq.all()
        if not papers:
            return []

        q_tokens = set(re.findall(r"[a-z0-9]{3,}", (query or "").lower()))
        scored = []
        for p in papers:
            abstract = (p.abstract or "").strip()
            hay = f"{p.title or ''} {abstract} {p.venue or ''}".lower()
            overlap = len(q_tokens.intersection(set(re.findall(r"[a-z0-9]{3,}", hay)))) if q_tokens else 0
            # Prefer papers with abstracts; keep scoped papers even with score 0
            score = overlap + (5 if abstract else 0)
            scored.append((score, p, abstract))

        scored.sort(key=lambda x: x[0], reverse=True)
        items: List[CitationItem] = []
        for score, p, abstract in scored[:top_k]:
            if abstract:
                snippet = abstract[:_ABSTRACT_SNIPPET_LIMIT] + (
                    "..." if len(abstract) > _ABSTRACT_SNIPPET_LIMIT else ""
                )
                section = "Abstract"
            else:
                snippet = (
                    f"No abstract is stored for this paper yet. "
                    f"Title: {p.title}. Year: {p.year or 'n.d.'}. Source: {p.source}. "
                    f"Ingest the PDF (or re-save after discovery) to answer methodology/dataset questions."
                )
                section = "Metadata"
            items.append(
                CitationItem(
                    paper_id=p.id,
                    paper_title=p.title,
                    doi=p.doi,
                    page=1,
                    section=section,
                    snippet=snippet,
                )
            )
        return items

    def ensure_abstract_chunk(self, db: Session, paper: Paper) -> None:
        """Index the stored abstract as a searchable chunk when no PDF chunks exist."""
        abstract = (paper.abstract or "").strip()
        if not abstract:
            return
        existing = (
            db.query(PaperChunk)
            .filter(PaperChunk.paper_id == paper.id, PaperChunk.section == "Abstract")
            .first()
        )
        if existing:
            if existing.content != abstract:
                existing.content = abstract
                existing.embedding_json = json.dumps(self.embedding_service.embed_text(abstract))
                db.commit()
            return

        has_any = db.query(PaperChunk).filter(PaperChunk.paper_id == paper.id).count()
        if has_any:
            return

        chunk = PaperChunk(
            paper_id=paper.id,
            content=abstract,
            page_number=1,
            section="Abstract",
            chunk_index=0,
            embedding_json=json.dumps(self.embedding_service.embed_text(abstract)),
        )
        db.add(chunk)
        db.commit()
