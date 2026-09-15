import logging
from app.db.session import SessionLocal
from app.services.operations_service import OperationsService
from app.services.pdf_service import PDFService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_pdf_document")
def process_pdf_document_task(self, document_id: int, job_id: str = None):
    """Background task to extract text and generate chunk embeddings for a PDF document."""
    logger.info(f"Starting background PDF processing for document {document_id}")
    with SessionLocal() as db:
        try:
            if job_id:
                OperationsService.update_job(db, job_id, status="running", progress=10)
            service = PDFService()
            service.process_document_text(db, document_id)
            if job_id:
                OperationsService.update_job(
                    db, job_id, status="completed", progress=100, result={"document_id": document_id}
                )
            return {"status": "success", "document_id": document_id}
        except Exception as exc:
            logger.error(f"PDF task failed for document {document_id}: {exc}")
            if job_id:
                OperationsService.update_job(db, job_id, status="failed", progress=100, error=str(exc))
            raise
