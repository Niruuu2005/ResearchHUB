import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.database import ResearchSession
from app.models.schemas import ResearchRequest, ResearchResponse
from app.services.research_service import ResearchService

router = APIRouter(prefix="/api/research", tags=["Topic Research"])
research_service = ResearchService()


@router.post("", response_model=ResearchResponse, summary="Execute Topic Research")
async def execute_research(payload: ResearchRequest, db: Session = Depends(get_db)):
    """Execute topic research pipeline across Wikipedia, OpenAlex, and Crossref with advanced filters."""
    topic = payload.topic.strip()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Topic must not be empty.",
        )

    try:
        response = await research_service.perform_research(
            topic=topic,
            year_from=payload.year_from,
            year_to=payload.year_to,
            open_access_only=payload.open_access_only,
            sources_filter=payload.sources,
            db=db,
        )
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while executing the research pipeline: {str(exc)}",
        )


@router.get("/history", summary="Research Session History")
async def get_research_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve list of previous research queries."""
    sessions = (
        db.query(ResearchSession)
        .order_by(ResearchSession.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": s.id,
            "topic": s.topic,
            "year_from": s.year_from,
            "year_to": s.year_to,
            "open_access_only": s.open_access_only,
            "created_at": s.created_at,
            "summary_preview": s.summary[:150] + ("..." if len(s.summary) > 150 else ""),
        }
        for s in sessions
    ]


@router.get("/{session_id}", summary="Get Research Session")
async def get_research_session(session_id: int, db: Session = Depends(get_db)):
    """Retrieve full details of a saved research session."""
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found.")

    return {
        "id": session.id,
        "topic": session.topic,
        "summary": session.summary,
        "key_points": json.loads(session.key_points_json or "[]"),
        "warnings": json.loads(session.warnings_json or "[]"),
        "created_at": session.created_at,
    }


@router.delete("/{session_id}", summary="Delete Research Session")
async def delete_research_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a research session from history."""
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found.")
    db.delete(session)
    db.commit()
    return {"message": "Session deleted successfully"}
