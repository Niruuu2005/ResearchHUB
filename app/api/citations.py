from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.schemas import CitationExportResponse, CitationFormatRequest, CitationItemOut
from app.services.citation_service import CitationService

router = APIRouter(prefix="/api/citations", tags=["Citation Manager"])


@router.post("/format", response_model=List[CitationItemOut], summary="Format Citations")
async def format_citations(payload: CitationFormatRequest, db: Session = Depends(get_db)):
    """Format papers in specified academic citation style (IEEE, APA, MLA, Harvard)."""
    return CitationService.format_citations(db, payload.paper_ids, payload.style)


@router.post("/export", response_model=CitationExportResponse, summary="Bulk Export Citations")
async def export_citations(payload: CitationFormatRequest, db: Session = Depends(get_db)):
    """Bulk export citations and generated BibTeX."""
    return CitationService.export_bulk_citations(db, payload.paper_ids, payload.style)
