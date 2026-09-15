from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import os

from app.config import settings
from app.db.session import get_db
from app.models.schemas import HealthResponse, ReadyResponse
from app.services.operations_service import OperationsService

router = APIRouter(tags=["System & Observability"])


@router.get("/health", response_model=HealthResponse, summary="Liveness Probe")
async def liveness_check():
    """Returns 200 OK indicating the service process is alive."""
    return HealthResponse(
        status="running",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get("/ready", response_model=ReadyResponse, summary="Readiness Probe")
async def readiness_check(db: Session = Depends(get_db)):
    """Verifies that database and background components are healthy and ready to accept traffic."""
    health_map = OperationsService.get_service_health(db)
    overall_status = "ready" if health_map["database"] == "healthy" else "degraded"
    return ReadyResponse(
        status=overall_status,
        database=health_map["database"],
        redis=health_map["redis"],
        worker=health_map["worker"],
    )


@router.get("/metrics", response_class=PlainTextResponse, summary="Prometheus Metrics")
async def prometheus_metrics(db: Session = Depends(get_db)):
    """Exposes Prometheus scrape metrics format for monitoring dashboards."""
    return OperationsService.get_prometheus_metrics(db)


@router.get("/api/system/version", summary="System & Build Version")
async def system_version():
    """Returns application environment and deployment version details."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "commit": settings.git_commit,
        "build": settings.build_number,
    }


@router.get("/api/system/config", summary="Runtime Configuration (No Secrets)")
async def system_config():
    """Return non-secret runtime settings for the Settings UI. Does not expose API keys."""
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        database_dialect = "sqlite"
    elif "postgres" in db_url:
        database_dialect = "postgresql"
    else:
        database_dialect = "other"

    from app.services.embedding_service import EmbeddingService

    embedding_runtime = EmbeddingService().provider_in_use()

    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "commit": settings.git_commit,
        "build": settings.build_number,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "ollama_base_url": settings.ollama_base_url,
        "embedding_provider": settings.embedding_provider,
        "embedding_runtime": embedding_runtime,
        "embedding_model": settings.embedding_model,
        "storage_path": settings.storage_path,
        "export_storage_path": settings.export_storage_path,
        "database_dialect": database_dialect,
        "use_celery": os.getenv("USE_CELERY", "false").lower() in ("true", "1", "yes"),
        "enable_wikipedia": settings.enable_wikipedia,
        "enable_openalex": settings.enable_openalex,
        "enable_crossref": settings.enable_crossref,
    }
