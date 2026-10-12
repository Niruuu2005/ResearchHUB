from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.database import User
from app.models.schemas import LiteratureReviewOut, LiteratureReviewRequest
from app.services.literature_review_service import LiteratureReviewService

router = APIRouter(prefix="/api/literature-review", tags=["Literature Review Builder"])
review_service = LiteratureReviewService()


@router.post("", response_model=LiteratureReviewOut, summary="Build Literature Review")
async def generate_literature_review(
    payload: LiteratureReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an 11-section literature review from papers owned by the authenticated user."""
    try:
        return review_service.build_literature_review(
            db=db,
            project_id=payload.project_id,
            paper_ids=payload.paper_ids,
            topic=payload.topic,
            citation_style=payload.citation_style,
            user_id=current_user.id,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate literature review: {exc}")
