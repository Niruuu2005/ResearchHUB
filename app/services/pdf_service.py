import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import Paper, PaperDocument, PaperChunk
from app.services.embedding_service import EmbeddingService
from app.utils.files import sanitize_filename, validate_pdf_content
from app.utils.hashing import compute_sha256
from app.utils.text import chunk_text

logger = logging.getLogger(__name__)


class PDFService:
    """Handles PDF ingestion, validation, text extraction, and vector chunking."""

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedding_service = embedding_service or EmbeddingService()
        self.storage_dir = Path(settings.storage_path)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_uploaded_pdf(
        self,
        db: Session,
        paper_id: int,
        filename: str,
        content: bytes,
    ) -> PaperDocument:
        """Validate and persist uploaded PDF file, then schedule/execute text processing."""
        # 1. Validation
        if len(content) > settings.max_pdf_size_mb * 1024 * 1024:
            raise ValueError(f"File size exceeds limit of {settings.max_pdf_size_mb} MB")

        if not validate_pdf_content(content):
            raise ValueError("Invalid PDF format. File must begin with %PDF- header.")

        safe_name = sanitize_filename(filename)
        checksum = compute_sha256(content)
        storage_key = f"paper_{paper_id}_{checksum[:8]}_{safe_name}"
        file_path = self.storage_dir / storage_key

        with open(file_path, "wb") as f:
            f.write(content)

        # Create or update document record
        document = db.query(PaperDocument).filter(PaperDocument.paper_id == paper_id).first()
        if not document:
            document = PaperDocument(
                paper_id=paper_id,
                storage_key=storage_key,
                file_name=safe_name,
                file_size=len(content),
                page_count=0,
                processing_status="processing",
                checksum=checksum,
            )
            db.add(document)
        else:
            document.storage_key = storage_key
            document.file_name = safe_name
            document.file_size = len(content)
            document.checksum = checksum
            document.processing_status = "processing"
            document.error_message = None

        db.commit()
        db.refresh(document)

        self._schedule_or_process(db, document.id)
        return document

    def _schedule_or_process(self, db: Session, document_id: int) -> None:
        """Dispatch PDF processing to Celery when enabled; otherwise run in-process."""
        import os
        import uuid

        use_celery = os.getenv("USE_CELERY", "false").lower() in ("true", "1", "yes")
        if use_celery:
            try:
                from app.services.operations_service import OperationsService
                from app.workers.pdf_tasks import process_pdf_document_task

                job_id = str(uuid.uuid4())
                OperationsService.record_job(
                    db, job_id, "process_pdf", {"document_id": document_id}
                )
                process_pdf_document_task.delay(document_id, job_id)
                logger.info(f"Queued Celery PDF job {job_id} for document {document_id}")
                return
            except Exception as exc:
                logger.warning(f"Celery dispatch failed ({exc}); processing PDF in-process.")

        self.process_document_text(db, document_id)
    async def fetch_open_access_pdf(self, db: Session, paper_id: int, pdf_url: str) -> PaperDocument:
        """Download open-access PDF from remote source and process it."""
        logger.info(f"Downloading Open-Access PDF for paper {paper_id} from {pdf_url}")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {"User-Agent": settings.user_agent}
            resp = await client.get(pdf_url, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch PDF. Remote server returned status {resp.status_code}")

            content = resp.content
            filename = pdf_url.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename = f"paper_{paper_id}.pdf"

            return self.save_uploaded_pdf(db, paper_id, filename, content)

    def extract_pages(self, file_path: Path) -> List[Tuple[int, str]]:
        """Extract text per page using PyMuPDF (fitz) or pypdf fallback."""
        pages: List[Tuple[int, str]] = []

        # Try PyMuPDF first
        try:
            import fitz
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                text = page.get_text("text")
                pages.append((i + 1, text))
            doc.close()
            return pages
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}. Trying pypdf...")

        # Fallback to pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append((i + 1, text))
            return pages
        except Exception as e2:
            logger.error(f"pypdf extraction failed: {e2}")
            raise RuntimeError(f"Unable to extract text from PDF: {e2}")

    def process_document_text(self, db: Session, document_id: int):
        """Extract text, create chunks with metadata, compute embeddings, and store in DB."""
        document = db.query(PaperDocument).filter(PaperDocument.id == document_id).first()
        if not document:
            return

        file_path = self.storage_dir / document.storage_key
        if not file_path.exists():
            document.processing_status = "failed"
            document.error_message = "File not found on disk."
            db.commit()
            return

        try:
            pages = self.extract_pages(file_path)
            document.page_count = len(pages)

            # Generate chunks
            chunks_data = chunk_text(pages)

            # Clear any old chunks for this paper
            db.query(PaperChunk).filter(PaperChunk.paper_id == document.paper_id).delete()

            for c in chunks_data:
                vector = self.embedding_service.embed_text(c["content"])
                chunk = PaperChunk(
                    paper_document_id=document.id,
                    paper_id=document.paper_id,
                    page_number=c["page_number"],
                    section=c["section"],
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    embedding_json=json.dumps(vector),
                )
                db.add(chunk)

            document.processing_status = "ready"
            document.error_message = None
            db.commit()
            logger.info(f"Successfully indexed document {document.id} with {len(chunks_data)} chunks.")

        except Exception as exc:
            logger.error(f"Error processing document {document.id}: {exc}")
            document.processing_status = "failed"
            document.error_message = str(exc)
            db.commit()
