import logging
from typing import List
from sqlalchemy.orm import Session

from app.models.database import Paper
from app.models.schemas import CitationExportResponse, CitationItemOut
from app.utils.citations import format_bibtex, format_citation

logger = logging.getLogger(__name__)


class CitationService:
    """Manages bibliographic styling, BibTeX generation, and bulk citation exports."""

    @staticmethod
    def format_citations(db: Session, paper_ids: List[int], style: str = "IEEE") -> List[CitationItemOut]:
        papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
        results = []

        for p in papers:
            authors = [a.author_name for a in p.authors]
            formatted = format_citation(style, authors, p.title, p.venue, p.year, p.doi)
            bibtex = format_bibtex(p.id, authors, p.title, p.venue, p.year, p.doi)
            results.append(
                CitationItemOut(
                    paper_id=p.id,
                    title=p.title,
                    style=style,
                    formatted_text=formatted,
                    bibtex=bibtex,
                )
            )

        return results

    @staticmethod
    def export_bulk_citations(db: Session, paper_ids: List[int], style: str = "IEEE") -> CitationExportResponse:
        items = CitationService.format_citations(db, paper_ids, style)
        citations_list = [it.formatted_text for it in items]
        bibtex_combined = "\n\n".join([it.bibtex for it in items])

        return CitationExportResponse(
            style=style,
            citations=citations_list,
            bibtex=bibtex_combined,
        )
