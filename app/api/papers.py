from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.database import Paper
from app.models.schemas import PaperOut, PaperSaveRequest
from app.services.citation_service import CitationService
from app.services.operations_service import OperationsService
from app.services.paper_service import PaperService

router = APIRouter(prefix="/api/papers", tags=["Paper Library"])


@router.get("", response_model=List[PaperOut], summary="List Saved Papers")
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    project_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve saved academic papers from personal library with filtering."""
    papers = PaperService.get_papers(db, skip=skip, limit=limit, project_id=project_id, search=search)
    results = []
    for p in papers:
        doc = p.documents[0] if p.documents else None
        results.append(
            PaperOut(
                id=p.id,
                title=p.title,
                authors=[a.author_name for a in p.authors],
                year=p.year,
                source=p.source,
                url=p.url,
                doi=p.doi,
                venue=p.venue,
                open_access=p.open_access,
                pdf_url=p.pdf_url,
                abstract=p.abstract,
                has_pdf=doc is not None,
                processing_status=doc.processing_status if doc else None,
                created_at=p.created_at,
            )
        )
    return results


@router.post("/save", response_model=PaperOut, status_code=status.HTTP_201_CREATED, summary="Save Paper")
async def save_paper(payload: PaperSaveRequest, db: Session = Depends(get_db)):
    """Save an academic paper to the library."""
    paper = PaperService.save_paper(db, payload)
    OperationsService.record_audit(db, "paper_saved", "paper", str(paper.id), paper.title)
    doc = paper.documents[0] if paper.documents else None
    return PaperOut(
        id=paper.id,
        title=paper.title,
        authors=[a.author_name for a in paper.authors],
        year=paper.year,
        source=paper.source,
        url=paper.url,
        doi=paper.doi,
        venue=paper.venue,
        open_access=paper.open_access,
        pdf_url=paper.pdf_url,
        abstract=paper.abstract,
        has_pdf=doc is not None,
        processing_status=doc.processing_status if doc else None,
        created_at=paper.created_at,
    )


@router.get("/{paper_id}", summary="Get Paper Intelligence Details")
async def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """Retrieve complete metadata and processing status for an academic paper."""
    paper = PaperService.get_paper_by_id(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    doc = paper.documents[0] if paper.documents else None
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": [a.author_name for a in paper.authors],
        "year": paper.year,
        "source": paper.source,
        "venue": paper.venue,
        "doi": paper.doi,
        "url": paper.url,
        "open_access": paper.open_access,
        "pdf_url": paper.pdf_url,
        "abstract": paper.abstract,
        "document": {
            "has_pdf": doc is not None,
            "status": doc.processing_status if doc else "none",
            "page_count": doc.page_count if doc else 0,
            "chunks_count": len(paper.chunks),
        },
        "has_summary": paper.summary is not None,
        "created_at": paper.created_at,
    }


@router.delete("/{paper_id}", summary="Delete Paper")
async def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    success = PaperService.delete_paper(db, paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found.")
    OperationsService.record_audit(db, "paper_deleted", "paper", str(paper_id))
    return {"message": "Paper removed from library"}


@router.get("/{paper_id}/related", summary="Get Related Papers")
async def get_related_papers(paper_id: int, db: Session = Depends(get_db)):
    related = PaperService.get_related_papers(db, paper_id)
    return [
        {
            "paper_id": item["paper"].id,
            "title": item["paper"].title,
            "year": item["paper"].year,
            "authors": [a.author_name for a in item["paper"].authors],
            "similarity_percent": item["similarity_percent"],
            "common_themes": item["common_themes"],
        }
        for item in related
    ]


@router.get("/{paper_id}/citation", summary="Format Paper Citation")
async def get_paper_citation(
    paper_id: int,
    style: str = Query("IEEE", pattern="^(IEEE|APA|MLA|Harvard)$"),
    db: Session = Depends(get_db),
):
    citations = CitationService.format_citations(db, [paper_id], style)
    if not citations:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return citations[0]
