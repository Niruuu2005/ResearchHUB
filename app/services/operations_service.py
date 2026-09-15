import datetime
import json
import logging
import time
from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import (
    AuditEvent,
    BackgroundJob,
    ChatMessage,
    ChatSession,
    DeploymentRecord,
    ExportReport,
    Paper,
    PaperChunk,
    PaperDocument,
    ResearchProject,
)
from app.models.schemas import DevOpsOverview, ProviderStatusItem

logger = logging.getLogger(__name__)


class OperationsService:
    """Manages system health, Prometheus metrics generation, audit trails, and DevOps telemetry."""

    @staticmethod
    def get_service_health(db: Session) -> Dict[str, str]:
        health = {
            "api": "healthy",
            "database": "healthy",
            "redis": "healthy",
            "worker": "in-process",
        }

        # Check DB
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            health["database"] = "unhealthy"

        # Check Redis if configured
        try:
            import redis
            r = redis.Redis.from_url(settings.redis_url, socket_timeout=1.0)
            r.ping()
        except Exception:
            health["redis"] = "offline (in-process fallback)"

        # Worker honesty: jobs are not dispatched to Celery today; PDF/summary/export run in-process.
        use_celery = False
        try:
            import os
            use_celery = os.getenv("USE_CELERY", "false").lower() in ("true", "1", "yes")
        except Exception:
            use_celery = False

        active_jobs = db.query(BackgroundJob).filter(BackgroundJob.status.in_(["queued", "running"])).count()
        if use_celery and active_jobs > 0:
            health["worker"] = "healthy"
        elif use_celery:
            health["worker"] = "idle"
        else:
            health["worker"] = "in-process"

        return health

    @staticmethod
    def get_provider_statuses() -> List[ProviderStatusItem]:
        """Probe enabled academic providers with short timeouts; no fabricated latencies."""
        now = datetime.datetime.utcnow()
        probes = []

        def probe(name: str, enabled: bool, url: str) -> ProviderStatusItem:
            if not enabled:
                return ProviderStatusItem(
                    name=name, status="disabled", latency_ms=0.0, last_checked=now, error=None
                )
            start = time.perf_counter()
            try:
                import httpx
                with httpx.Client(timeout=2.5, follow_redirects=True) as client:
                    resp = client.head(url)
                    if resp.status_code >= 500:
                        resp = client.get(url)
                latency = round((time.perf_counter() - start) * 1000, 1)
                status = "healthy" if resp.status_code < 500 else "degraded"
                return ProviderStatusItem(
                    name=name,
                    status=status,
                    latency_ms=latency,
                    last_checked=now,
                    error=None if resp.status_code < 500 else f"HTTP {resp.status_code}",
                )
            except Exception as exc:
                latency = round((time.perf_counter() - start) * 1000, 1)
                return ProviderStatusItem(
                    name=name,
                    status="unavailable",
                    latency_ms=latency,
                    last_checked=now,
                    error=str(exc)[:160],
                )

        probes.append(probe("Wikipedia", settings.enable_wikipedia, "https://en.wikipedia.org/wiki/Main_Page"))
        probes.append(probe("OpenAlex", settings.enable_openalex, "https://api.openalex.org/works?per-page=1"))
        probes.append(probe("Crossref", settings.enable_crossref, "https://api.crossref.org/works?rows=1"))

        # Local DB dialect label — not an external latency claim
        probes.append(
            ProviderStatusItem(
                name="Database",
                status="healthy",
                latency_ms=0.0,
                last_checked=now,
                error=None,
            )
        )
        return probes

    @staticmethod
    def get_overview(db: Session) -> DevOpsOverview:
        health = OperationsService.get_service_health(db)
        providers = OperationsService.get_provider_statuses()

        total_projects = db.query(ResearchProject).count()
        total_papers = db.query(Paper).count()
        total_docs = db.query(PaperDocument).count()
        total_chunks = db.query(PaperChunk).count()
        total_convos = db.query(ChatSession).count()
        total_reports = db.query(ExportReport).count()
        active_jobs = db.query(BackgroundJob).filter(BackgroundJob.status.in_(["queued", "running"])).count()

        return DevOpsOverview(
            app_name=settings.app_name,
            version=settings.app_version,
            git_commit=settings.git_commit,
            build_number=settings.build_number,
            environment=settings.app_env,
            api_health=health["api"],
            db_health=health["database"],
            redis_health=health["redis"],
            worker_health=health["worker"],
            providers=providers,
            active_jobs=active_jobs,
            total_projects=total_projects,
            total_papers=total_papers,
            total_documents=total_docs,
            total_chunks=total_chunks,
            total_conversations=total_convos,
            total_reports=total_reports,
        )

    @staticmethod
    def get_prometheus_metrics(db: Session) -> str:
        overview = OperationsService.get_overview(db)
        providers = overview.providers or []
        lines = [
            "# HELP researchops_app_info Application build and version info.",
            "# TYPE researchops_app_info gauge",
            f'researchops_app_info{{version="{settings.app_version}",env="{settings.app_env}",commit="{settings.git_commit}"}} 1',
            "",
            "# HELP researchops_total_papers Number of papers in library.",
            "# TYPE researchops_total_papers gauge",
            f"researchops_total_papers {overview.total_papers}",
            "",
            "# HELP researchops_total_documents Indexed documents count.",
            "# TYPE researchops_total_documents gauge",
            f"researchops_total_documents {overview.total_documents}",
            "",
            "# HELP researchops_total_chunks Total vectorized text chunks.",
            "# TYPE researchops_total_chunks gauge",
            f"researchops_total_chunks {overview.total_chunks}",
            "",
            "# HELP researchops_total_projects Number of active research projects.",
            "# TYPE researchops_total_projects gauge",
            f"researchops_total_projects {overview.total_projects}",
            "",
            "# HELP researchops_active_background_jobs Current jobs in queue or running.",
            "# TYPE researchops_active_background_jobs gauge",
            f"researchops_active_background_jobs {overview.active_jobs}",
            "",
            "# HELP researchops_provider_latency_ms Measured provider probe latency in milliseconds.",
            "# TYPE researchops_provider_latency_ms gauge",
        ]
        for p in providers:
            if p.name == "Database":
                continue
            safe = p.name.lower().replace(" ", "_")
            lines.append(f'researchops_provider_latency_ms{{provider="{safe}",status="{p.status}"}} {p.latency_ms}')
        return "\n".join(lines) + "\n"

    @staticmethod
    def record_audit(
        db: Session, action: str, entity_type: str, entity_id: Optional[str] = None, details: Optional[str] = None
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details,
        )
        db.add(event)
        db.commit()
        return event

    @staticmethod
    def record_job(db: Session, job_id: str, job_type: str, payload: dict) -> BackgroundJob:
        job = BackgroundJob(
            id=job_id,
            job_type=job_type,
            status="queued",
            progress=0,
            payload_json=json.dumps(payload),
        )
        db.add(job)
        db.commit()
        return job

    @staticmethod
    def update_job(
        db: Session,
        job_id: str,
        status: str,
        progress: int = 100,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if job:
            job.status = status
            job.progress = progress
            if result:
                job.result_json = json.dumps(result)
            if error:
                job.error = error
            if status in ("completed", "failed"):
                job.completed_at = datetime.datetime.utcnow()
            db.commit()
