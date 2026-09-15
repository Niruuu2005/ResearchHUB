from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.database import Paper, PaperChunk, PaperDocument
from app.models.schemas import DocumentOut, ProcessingStatusOut
from app.services.operations_service import OperationsService
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api/papers", tags=["PDF Ingestion & Processing"])
pdf_service = PDFService()


class FetchPDFRequest(BaseModel):
    pdf_url: str


@router.post("/{paper_id}/upload", response_model=DocumentOut, summary="Upload PDF Document")
async def upload_pdf(
    paper_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a research paper PDF for automated extraction and vector embedding."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    try:
        content = await file.read()
        doc = pdf_service.save_uploaded_pdf(db, paper_id, file.filename or "paper.pdf", content)
        OperationsService.record_audit(db, "pdf_uploaded", "paper_document", str(doc.id), doc.file_name)
        return doc
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {exc}")


@router.post("/{paper_id}/fetch-pdf", response_model=DocumentOut, summary="Fetch Open-Access PDF")
async def fetch_open_access_pdf(
    paper_id: int,
    payload: FetchPDFRequest,
    db: Session = Depends(get_db),
):
    """Fetch an open-access PDF from a verified direct link and index it."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    try:
        doc = await pdf_service.fetch_open_access_pdf(db, paper_id, payload.pdf_url)
        OperationsService.record_audit(db, "pdf_fetched", "paper_document", str(doc.id), payload.pdf_url)
        return doc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch remote PDF: {exc}")


@router.get("/{paper_id}/pdf", summary="Serve Paper PDF")
async def serve_pdf(paper_id: int, db: Session = Depends(get_db)):
    """Serve the stored PDF binary file for embedded browser reader."""
    doc = db.query(PaperDocument).filter(PaperDocument.paper_id == paper_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No document found for this paper.")

    file_path = Path(settings.storage_path) / doc.storage_key
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file missing from storage.")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=doc.file_name,
    )


@router.get("/{paper_id}/processing-status", response_model=ProcessingStatusOut, summary="Get Document Indexing Status")
async def get_processing_status(paper_id: int, db: Session = Depends(get_db)):
    """Check whether paper PDF is parsed, chunked, and embedded."""
    doc = db.query(PaperDocument).filter(PaperDocument.paper_id == paper_id).first()
    if not doc:
        return ProcessingStatusOut(
            paper_id=paper_id,
            has_document=False,
            status="none",
            page_count=0,
            chunks_count=0,
        )

    chunks_count = db.query(PaperChunk).filter(PaperChunk.paper_id == paper_id).count()
    return ProcessingStatusOut(
        paper_id=paper_id,
        has_document=True,
        status=doc.processing_status,
        page_count=doc.page_count,
        chunks_count=chunks_count,
        error=doc.error_message,
    )
