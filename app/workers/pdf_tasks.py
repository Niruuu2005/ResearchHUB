import logging
from app.db.session import SessionLocal
from app.models.database import PaperDocument
from app.services.operations_service import OperationsService
from app.services.pdf_service import PDFService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_pdf_document")
def process_pdf_document_task(self, document_id: int, job_id: str = None, user_id: str = None):
    """Background task to extract text and generate chunk embeddings for a PDF document with ownership verification."""
    logger.info(f"Starting background PDF processing for document {document_id}")
    with SessionLocal() as db:
        try:
            doc = db.query(PaperDocument).filter(PaperDocument.id == document_id).first()
            if not doc:
                raise ValueError(f"Document {document_id} not found.")
            if user_id and doc.user_id and str(doc.user_id) != str(user_id):
                raise PermissionError("Access denied: Document does not belong to authorized user.")

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
