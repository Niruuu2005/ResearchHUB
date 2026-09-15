from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.schemas import LiteratureReviewOut, LiteratureReviewRequest
from app.services.literature_review_service import LiteratureReviewService

router = APIRouter(prefix="/api/literature-review", tags=["Literature Review Builder"])
review_service = LiteratureReviewService()


@router.post("", response_model=LiteratureReviewOut, summary="Build Literature Review")
async def generate_literature_review(payload: LiteratureReviewRequest, db: Session = Depends(get_db)):
    """Generate an 11-section literature review from saved paper metadata (titles, venues, abstracts, citations)."""
    try:
        return review_service.build_literature_review(
            db=db,
            project_id=payload.project_id,
            paper_ids=payload.paper_ids,
            topic=payload.topic,
            citation_style=payload.citation_style,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate literature review: {exc}")
