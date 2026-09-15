from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.schemas import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import ComparisonService

router = APIRouter(prefix="/api/compare", tags=["Paper Comparison"])
comparison_service = ComparisonService()


@router.post("", response_model=ComparisonResponse, summary="Compare 2 to 5 Papers")
async def compare_papers(payload: ComparisonRequest, db: Session = Depends(get_db)):
    """Generate side-by-side comparison matrix and AI synthesis across selected papers."""
    try:
        return comparison_service.compare_papers(db, payload.paper_ids)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}")
