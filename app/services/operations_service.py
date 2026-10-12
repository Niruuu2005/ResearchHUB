import datetime
import json
import logging
import os
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

        # Check Redis only if Celery is enabled
        use_celery = os.getenv("USE_CELERY", "false").lower() in ("true", "1", "yes")
        if use_celery:
            try:
                import redis
                r = redis.Redis.from_url(settings.redis_url, socket_timeout=0.3)
                r.ping()
            except Exception:
                health["redis"] = "offline (in-process fallback)"
        else:
            health["redis"] = "healthy (in-process mode)"

        active_jobs = db.query(BackgroundJob).filter(BackgroundJob.status.in_(["queued", "running"])).count()
        if use_celery and active_jobs > 0:
            health["worker"] = "healthy"
        elif use_celery:
            health["worker"] = "idle"
        else:
            health["worker"] = "in-process"

        return health

    _cached_provider_statuses: Optional[List[ProviderStatusItem]] = None
    _cached_provider_time: float = 0.0

    @staticmethod
    def get_provider_statuses() -> List[ProviderStatusItem]:
        """Probe enabled academic providers with short timeouts; cached for 25s to avoid scrape throttling."""
        now_ts = time.time()
        if (
            OperationsService._cached_provider_statuses is not None
            and (now_ts - OperationsService._cached_provider_time) < 25.0
        ):
            return OperationsService._cached_provider_statuses

        now = datetime.datetime.utcnow()

        def probe(name: str, enabled: bool, url: str) -> ProviderStatusItem:
            if not enabled:
                return ProviderStatusItem(
                    name=name, status="disabled", latency_ms=0.0, last_checked=now, error=None
                )
            start = time.perf_counter()
            try:
                import httpx
                with httpx.Client(timeout=1.5, follow_redirects=True) as client:
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

        import concurrent.futures
        tasks = [
            ("Wikipedia", settings.enable_wikipedia, "https://en.wikipedia.org/wiki/Main_Page"),
            ("OpenAlex", settings.enable_openalex, "https://api.openalex.org/works?per-page=1"),
            ("Crossref", settings.enable_crossref, "https://api.crossref.org/works?rows=1"),
        ]

        probes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_name = {
                executor.submit(probe, name, enabled, url): name for name, enabled, url in tasks
            }
            for future in concurrent.futures.as_completed(future_to_name):
                probes.append(future.result())

        # Local DB dialect label
        probes.append(
            ProviderStatusItem(
                name="Database",
                status="healthy",
                latency_ms=0.0,
                last_checked=now,
                error=None,
            )
        )
        OperationsService._cached_provider_statuses = probes
        OperationsService._cached_provider_time = now_ts
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

        # Database health check (1 = healthy, 0 = unhealthy)
        db_healthy = 1 if overview.api_health in ("healthy", "ready", "running") else 0

        # Telemetry collector stats
        try:
            from app.services.telemetry import telemetry
            uptime = telemetry.get_uptime_seconds()
            request_counts = telemetry.get_request_counts()
            duration_sum = telemetry.request_duration_sum
            duration_count = telemetry.request_duration_count
            error_counts = telemetry.get_error_counts()
        except Exception:
            uptime = 0.0
            request_counts = {}
            duration_sum = 0.0
            duration_count = 0
            error_counts = {}

        lines = [
            "# HELP researchops_app_info Application build and version info.",
            "# TYPE researchops_app_info gauge",
            f'researchops_app_info{{version="{settings.app_version}",env="{settings.app_env}",commit="{settings.git_commit}"}} 1',
            "",
            "# HELP researchops_process_uptime_seconds Platform process uptime in seconds.",
            "# TYPE researchops_process_uptime_seconds gauge",
            f"researchops_process_uptime_seconds {uptime:.1f}",
            "",
            "# HELP researchops_database_healthy Database connection status (1=healthy, 0=unhealthy).",
            "# TYPE researchops_database_healthy gauge",
            f"researchops_database_healthy {db_healthy}",
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
            "# HELP researchops_circuit_breaker_state Current state of provider circuit breaker (0=CLOSED, 1=HALF_OPEN, 2=OPEN).",
            "# TYPE researchops_circuit_breaker_state gauge",
        ]

        # Circuit breaker states
        try:
            from app.utils.circuit_breaker import CircuitBreaker, CircuitState
            cb_map = CircuitBreaker.get_all()
        except Exception:
            cb_map = {}

        for default_name in ["wikipedia", "openalex", "crossref"]:
            cb = next((c for k, c in cb_map.items() if k.lower() == default_name), None)
            val = 0
            if cb:
                val = 0 if cb.state == CircuitState.CLOSED else (1 if cb.state == CircuitState.HALF_OPEN else 2)
            lines.append(f'researchops_circuit_breaker_state{{provider="{default_name}"}} {val}')

        lines.extend([
            "",
            "# HELP researchops_provider_latency_ms Measured provider probe latency in milliseconds.",
            "# TYPE researchops_provider_latency_ms gauge",
        ])
        for p in providers:
            if p.name == "Database":
                continue
            safe = p.name.lower().replace(" ", "_")
            lines.append(f'researchops_provider_latency_ms{{provider="{safe}",status="{p.status}"}} {p.latency_ms}')

        # HTTP request metrics
        lines.extend([
            "",
            "# HELP http_requests_total Total HTTP requests handled.",
            "# TYPE http_requests_total counter",
        ])
        if request_counts:
            for (method, path, status_code), count in request_counts.items():
                lines.append(f'http_requests_total{{method="{method}",path="{path}",status="{status_code}"}} {count}')
        else:
            lines.append('http_requests_total{method="GET",path="/metrics",status="200"} 1')

        lines.extend([
            "",
            "# HELP http_request_duration_seconds Total time spent processing HTTP requests in seconds.",
            "# TYPE http_request_duration_seconds summary",
            f"http_request_duration_seconds_sum {duration_sum:.4f}",
            f"http_request_duration_seconds_count {duration_count}",
        ])

        if error_counts:
            lines.extend([
                "",
                "# HELP http_errors_total Total HTTP 4xx and 5xx responses.",
                "# TYPE http_errors_total counter",
            ])
            for sc, count in error_counts.items():
                lines.append(f'http_errors_total{{status="{sc}"}} {count}')

        return "\n".join(lines) + "\n"

    @staticmethod
    def record_audit(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AuditEvent:
        event_details = f"[user:{user_id}] {details}" if user_id and details else details
        event = AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=event_details,
        )
        db.add(event)
        db.commit()
        return event

    @staticmethod
    def record_job(
        db: Session, job_id: str, job_type: str, payload: dict, user_id: Optional[str] = None
    ) -> BackgroundJob:
        job = BackgroundJob(
            id=job_id,
            user_id=str(user_id) if user_id else None,
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
