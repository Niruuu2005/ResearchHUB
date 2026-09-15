import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Minimal valid PDF binary
VALID_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n"
    b"4 0 obj<</Length 55>>stream\n"
    b"BT /F1 12 Tf 100 700 Td (Academic Verification Protocol and Results) Tj ET\n"
    b"endstream\n"
    b"endobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \n"
    b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n319\n%%EOF"
)


import uuid

def test_pdf_upload_and_serving_lifecycle():
    unique_suffix = str(uuid.uuid4())[:8]
    # 1. Create target paper
    save_res = client.post(
        "/api/papers/save",
        json={
            "title": f"Empirical Study on Distributed Vector Indices {unique_suffix}",
            "authors": ["Dr. Linus Miller"],
            "year": 2025,
            "source": "OpenAlex",
            "venue": "VLDB",
            "abstract": "Evaluation of vector retrieval indices under heavy concurrency.",
        },
    )
    assert save_res.status_code in [200, 201]
    paper_id = save_res.json()["id"]

    # 2. Verify initially no document
    status_res = client.get(f"/api/papers/{paper_id}/processing-status")
    assert status_res.status_code == 200
    assert status_res.json()["has_document"] is False

    # 3. Upload valid PDF
    pdf_file = io.BytesIO(VALID_PDF_BYTES)
    upload_res = client.post(
        f"/api/papers/{paper_id}/upload",
        files={"file": ("test_paper.pdf", pdf_file, "application/pdf")},
    )
    assert upload_res.status_code == 200
    doc_data = upload_res.json()
    assert doc_data["file_name"] == "test_paper.pdf"
    assert doc_data["page_count"] >= 1
    assert doc_data["processing_status"] in ["ready", "completed"]

    # 4. Check processing status reflects indexing
    updated_status = client.get(f"/api/papers/{paper_id}/processing-status")
    assert updated_status.status_code == 200
    assert updated_status.json()["has_document"] is True
    assert updated_status.json()["chunks_count"] >= 1

    # 5. Serve PDF endpoint returns application/pdf
    serve_res = client.get(f"/api/papers/{paper_id}/pdf")
    assert serve_res.status_code == 200
    assert "application/pdf" in serve_res.headers.get("content-type", "")
    assert len(serve_res.content) > 100


def test_pdf_upload_invalid_file_rejected():
    save_res = client.post(
        "/api/papers/save",
        json={
            "title": "Invalid Document Test Paper",
            "authors": ["Anon"],
            "year": 2024,
            "source": "Crossref",
        },
    )
    assert save_res.status_code in [200, 201]
    paper_id = save_res.json()["id"]

    # Upload corrupt text file claiming to be PDF
    corrupt_file = io.BytesIO(b"Plain text not a real PDF format")
    bad_upload = client.post(
        f"/api/papers/{paper_id}/upload",
        files={"file": ("corrupt.pdf", corrupt_file, "application/pdf")},
    )
    assert bad_upload.status_code in [400, 422, 500]


def test_serve_missing_pdf_returns_404():
    res = client.get("/api/papers/999999/pdf")
    assert res.status_code == 404
