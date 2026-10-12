from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.database import User
from app.models.schemas import CollectionSummaryOut, PaperSummaryOut
from app.services.summary_service import SummaryService

router = APIRouter(prefix="/api", tags=["Structured Summaries"])
summary_service = SummaryService()


@router.get("/summaries", response_model=List[PaperSummaryOut], summary="List Saved Paper Summaries")
async def list_summaries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return structured summaries belonging to papers in the authenticated user's library."""
    return summary_service.list_summaries(db, user_id=current_user.id)


@router.post("/papers/{paper_id}/summarize", response_model=PaperSummaryOut, summary="Generate Structured Paper Summary")
async def generate_paper_summary(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate or retrieve 16-parameter academic summary for a paper owned by the authenticated user."""
    try:
        return summary_service.summarize_paper(db, paper_id, user_id=current_user.id)
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {exc}")


@router.get("/papers/{paper_id}/summary", response_model=PaperSummaryOut, summary="Get Paper Summary")
async def get_paper_summary(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve existing structured summary for a paper owned by the user."""
    return await generate_paper_summary(paper_id, current_user, db)


@router.post("/projects/{project_id}/summarize", response_model=CollectionSummaryOut, summary="Generate Collection Summary")
async def generate_project_summary(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Synthesize project collection summary with themes, findings, and research gaps for a user-owned project."""
    try:
        return summary_service.summarize_project(db, project_id, user_id=current_user.id)
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to summarize collection: {exc}")


@router.get("/projects/{project_id}/summary", response_model=CollectionSummaryOut, summary="Get Collection Summary")
async def get_project_summary(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await generate_project_summary(project_id, current_user, db)
