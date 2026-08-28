from typing import List
from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.models.schemas import (
    HealthResponse,
    Paper,
    ResearchRequest,
    ResearchResponse,
)
from app.services.research_service import ResearchService

router = APIRouter()
research_service = ResearchService()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check endpoint",
    description="Returns the operational status and version of the ResearchLite microservice.",
)
async def health_check() -> HealthResponse:
    """Check service health and metadata."""
    return HealthResponse(
        status="running",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.post(
    "/research",
    response_model=ResearchResponse,
    tags=["Research"],
    summary="Perform comprehensive topic research",
    description="Queries Wikipedia, OpenAlex, and Crossref to synthesize an introductory summary, key points, and relevant publications.",
    status_code=status.HTTP_200_OK,
)
async def perform_research(payload: ResearchRequest) -> ResearchResponse:
    """Execute topic research pipeline across all connected providers."""
    topic = payload.topic.strip()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Topic must not be empty.",
        )

    try:
        response = await research_service.perform_research(topic)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while executing the research pipeline: {str(exc)}",
        )


@router.get(
    "/papers",
    response_model=List[Paper],
    tags=["Research"],
    summary="Search academic publications",
    description="Fetches and deduplicates scholarly papers for a topic from OpenAlex and Crossref.",
)
async def search_papers(
    topic: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="The topic or subject to query for publications.",
        examples=["Quantum Computing"],
    )
) -> List[Paper]:
    """Retrieve normalized academic papers matching the query."""
    clean_topic = topic.strip()
    if not clean_topic:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Topic query parameter must not be empty.",
        )

    try:
        return await research_service.get_papers_only(clean_topic)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query academic papers: {str(exc)}",
        )
