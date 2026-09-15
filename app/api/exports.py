import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.database import ExportReport
from app.models.schemas import ExportOut, ExportRequest
from app.services.export_service import ExportService
from app.services.operations_service import OperationsService

router = APIRouter(prefix="/api/exports", tags=["Reports & Exports"])
export_service = ExportService()


def _to_export_out(report: ExportReport) -> ExportOut:
    return ExportOut(
        id=report.id,
        title=report.title,
        report_type=report.report_type,
        format=report.format,
        download_url=f"/api/exports/{report.id}/download",
        file_size_bytes=report.file_size_bytes,
        status=report.status,
        project_id=report.project_id,
        created_at=report.created_at,
    )


@router.post("/report", response_model=ExportOut, status_code=status.HTTP_201_CREATED, summary="Generate Export Report")
async def generate_report(payload: ExportRequest, db: Session = Depends(get_db)):
    """Generate academic research report or literature review in PDF, DOCX, Markdown, JSON, or BibTeX."""
    try:
        report = export_service.generate_report(
            db=db,
            title=payload.title,
            report_type=payload.report_type,
            format_type=payload.format,
            citation_style=payload.citation_style,
            project_id=payload.project_id,
            paper_ids=payload.paper_ids,
        )
        OperationsService.record_audit(db, "report_exported", "export_report", str(report.id), report.title)
        return _to_export_out(report)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export generation failed: {exc}")


@router.get("", response_model=List[ExportOut], summary="List Generated Reports")
async def list_reports(
    project_id: Optional[int] = Query(default=None, description="Filter exports by research project"),
    db: Session = Depends(get_db),
):
    query = db.query(ExportReport)
    if project_id is not None:
        query = query.filter(ExportReport.project_id == project_id)
    reports = query.order_by(ExportReport.created_at.desc()).all()
    return [_to_export_out(r) for r in reports]


@router.get("/{export_id}/download", summary="Download Report File")
async def download_report_file(export_id: int, db: Session = Depends(get_db)):
    report = db.query(ExportReport).filter(ExportReport.id == export_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Export record not found.")

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file missing from disk.")

    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "md": "text/markdown",
        "json": "application/json",
        "bibtex": "application/x-bibtex",
    }
    media_type = media_types.get(report.format, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )
