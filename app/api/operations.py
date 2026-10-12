import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user
from app.db.session import get_db
from app.models.database import AuditEvent, BackgroundJob, DeploymentRecord, User
from app.models.schemas import AuditEventOut, DevOpsOverview, JobStatusOut, ProviderStatusItem
from app.services.operations_service import OperationsService

router = APIRouter(prefix="/api/operations", tags=["ResearchOps Control Center"])


@router.get("/overview", response_model=DevOpsOverview, summary="DevOps Control Center Overview")
async def get_devops_overview(db: Session = Depends(get_db)):
    """Comprehensive system observability overview: health, background queue, metrics, counts."""
    return OperationsService.get_overview(db)


@router.get("/providers/health", response_model=List[ProviderStatusItem], summary="Provider Statuses")
async def get_providers_health():
    """Live status and latency measurements for external academic providers and databases."""
    return OperationsService.get_provider_statuses()


@router.get("/jobs", response_model=List[JobStatusOut], summary="List Background Jobs")
async def list_jobs(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    query = db.query(BackgroundJob)
    if current_user:
        query = query.filter(BackgroundJob.user_id == current_user.id)
    else:
        query = query.filter(BackgroundJob.user_id.is_(None))
    jobs = query.order_by(BackgroundJob.created_at.desc()).limit(50).all()
    return [
        JobStatusOut(
            id=j.id,
            job_type=j.job_type,
            status=j.status,
            progress=j.progress,
            payload=json.loads(j.payload_json or "{}"),
            result=json.loads(j.result_json or "{}"),
            error=j.error,
            created_at=j.created_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobStatusOut, summary="Get Job Status")
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Background job not found.")
    
    # Enforce user isolation: if job is owned by a user, only that user may view it
    if job.user_id:
        if not current_user or str(job.user_id) != str(current_user.id):
            raise HTTPException(status_code=404, detail="Background job not found.")
            
    return JobStatusOut(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        payload=json.loads(job.payload_json or "{}"),
        result=json.loads(job.result_json or "{}"),
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/audit", response_model=List[AuditEventOut], summary="Audit Trail Logs")
async def get_audit_trail(db: Session = Depends(get_db)):
    events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(50).all()
    return events


@router.get("/deployments", summary="Deployment History")
async def get_deployments(db: Session = Depends(get_db)):
    deploys = db.query(DeploymentRecord).order_by(DeploymentRecord.deployed_at.desc()).all()
    return deploys
