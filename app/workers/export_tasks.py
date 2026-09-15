import logging
from typing import List, Optional
from app.db.session import SessionLocal
from app.services.export_service import ExportService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="generate_export_report_task")
def generate_export_report_task(
    title: str,
    report_type: str,
    format_type: str,
    citation_style: str = "IEEE",
    project_id: Optional[int] = None,
    paper_ids: Optional[List[int]] = None,
):
    """Asynchronously generates and compiles heavy research reports in PDF/DOCX/MD/BibTeX."""
    logger.info(f"Starting asynchronous report generation: '{title}' ({format_type.upper()})")
    with SessionLocal() as db:
        try:
            service = ExportService()
            report = service.generate_report(
                db=db,
                title=title,
                report_type=report_type,
                format_type=format_type,
                citation_style=citation_style,
                project_id=project_id,
                paper_ids=paper_ids,
            )
            logger.info(f"Report export generated successfully: ID {report.id} at {report.file_path}")
            return {
                "status": "success",
                "report_id": report.id,
                "file_path": report.file_path,
                "file_size": report.file_size_bytes,
            }
        except Exception as exc:
            logger.error(f"Asynchronous export task failed: {exc}")
            raise
