import io
import json
import uuid
import pytest
from starlette.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.database import BackgroundJob, Paper, ResearchProject, User
from app.services.auth_service import AuthService

client = TestClient(app)


@pytest.fixture
def user_a():
    """Create test User A (Alice) and return (User, token)."""
    with SessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            google_sub=f"sub_alice_{uuid.uuid4()}",
            email=f"alice_{uuid.uuid4().hex[:6]}@crypto.org",
            full_name="Alice Crypto",
            profile_picture="https://example.com/alice.png",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = AuthService.create_session_token(user)
        return user, token


@pytest.fixture
def user_b():
    """Create test User B (Bob) and return (User, token)."""
    with SessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            google_sub=f"sub_bob_{uuid.uuid4()}",
            email=f"bob_{uuid.uuid4().hex[:6]}@security.edu",
            full_name="Bob Security",
            profile_picture="https://example.com/bob.png",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = AuthService.create_session_token(user)
        return user, token


def test_papers_isolation_between_users(user_a, user_b):
    """Verify Alice's papers cannot be viewed, listed, updated, or deleted by Bob."""
    u_a, token_a = user_a
    u_b, token_b = user_b

    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Alice creates a private paper
    save_res = client.post(
        "/api/papers/save",
        json={
            "title": "Alice Private Cryptographic Protocols",
            "authors": ["Alice Crypto"],
            "year": 2026,
            "source": "OpenAlex",
            "doi": f"10.1000/alice.{uuid.uuid4().hex[:8]}",
            "abstract": "Confidential post-quantum lattice constructions.",
        },
        headers=auth_a,
    )
    assert save_res.status_code == 201
    paper_a_id = save_res.json()["id"]

    # 2. Alice can retrieve her paper
    get_alice = client.get(f"/api/papers/{paper_a_id}", headers=auth_a)
    assert get_alice.status_code == 200
    assert get_alice.json()["title"] == "Alice Private Cryptographic Protocols"

    # 3. Bob CANNOT retrieve Alice's paper (must return 404, not disclose existence)
    get_bob = client.get(f"/api/papers/{paper_a_id}", headers=auth_b)
    assert get_bob.status_code == 404

    # 4. Bob CANNOT see Alice's paper in his papers list
    list_bob = client.get("/api/papers", headers=auth_b)
    assert list_bob.status_code == 200
    bob_paper_ids = [p["id"] for p in list_bob.json()]
    assert paper_a_id not in bob_paper_ids

    # 5. Bob CANNOT delete Alice's paper
    del_bob = client.delete(f"/api/papers/{paper_a_id}", headers=auth_b)
    assert del_bob.status_code == 404

    # Paper must still exist for Alice
    get_alice_still = client.get(f"/api/papers/{paper_a_id}", headers=auth_a)
    assert get_alice_still.status_code == 200


def test_pdf_document_isolation(user_a, user_b):
    """Verify Alice's uploaded PDFs cannot be downloaded or accessed by Bob."""
    u_a, token_a = user_a
    u_b, token_b = user_b

    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Alice creates a paper
    save_res = client.post(
        "/api/papers/save",
        json={
            "title": "Zero-Knowledge PDF Specification",
            "authors": ["Alice"],
            "year": 2026,
            "source": "OpenAlex",
            "doi": f"10.1000/zk.{uuid.uuid4().hex[:8]}",
        },
        headers=auth_a,
    )
    paper_id = save_res.json()["id"]

    # 2. Alice uploads a PDF
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (Alice Confidential Proofs) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_res = client.post(
        f"/api/papers/{paper_id}/upload",
        files={"file": ("confidential_alice.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        headers=auth_a,
    )
    assert upload_res.status_code in (200, 201)

    # 3. Alice can serve / download her PDF
    dl_alice = client.get(f"/api/papers/{paper_id}/pdf", headers=auth_a)
    assert dl_alice.status_code == 200
    assert dl_alice.content == fake_pdf

    # 4. Bob CANNOT download Alice's PDF
    dl_bob = client.get(f"/api/papers/{paper_id}/pdf", headers=auth_b)
    assert dl_bob.status_code == 404

    # 5. Bob CANNOT upload a replacement PDF for Alice's paper
    upload_bob = client.post(
        f"/api/papers/{paper_id}/upload",
        files={"file": ("tamper.pdf", io.BytesIO(b"%PDF-1.4 tamper"), "application/pdf")},
        headers=auth_b,
    )
    assert upload_bob.status_code == 404


def test_summaries_and_comparisons_isolation(user_a, user_b):
    """Verify Alice's generated summaries and comparisons are inaccessible to Bob."""
    u_a, token_a = user_a
    u_b, token_b = user_b

    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # Alice saves a paper and generates summary
    p_res = client.post(
        "/api/papers/save",
        json={
            "title": "Quantum Entanglement Diagnostics",
            "authors": ["Alice"],
            "year": 2025,
            "source": "OpenAlex",
            "doi": f"10.1000/qe.{uuid.uuid4().hex[:8]}",
            "abstract": "Diagnostic benchmarks for multi-qubit coherence states.",
        },
        headers=auth_a,
    )
    paper_id = p_res.json()["id"]

    sum_res = client.post(f"/api/papers/{paper_id}/summarize", headers=auth_a)
    assert sum_res.status_code == 200

    # Bob lists summaries -> Alice's paper summary must NOT appear
    bob_sums = client.get("/api/summaries", headers=auth_b)
    assert bob_sums.status_code == 200
    assert paper_id not in [s["paper_id"] for s in bob_sums.json()]

    # Bob tries to compare using Alice's paper ID -> rejected (400 or 404)
    comp_res = client.post(
        "/api/compare",
        json={"paper_ids": [paper_id, 99999]},
        headers=auth_b,
    )
    assert comp_res.status_code in (400, 404)


def test_projects_and_notes_isolation(user_a, user_b):
    """Verify Alice's projects and notes cannot be accessed or manipulated by Bob."""
    u_a, token_a = user_a
    u_b, token_b = user_b

    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # Alice creates a project
    proj_res = client.post(
        "/api/projects",
        json={
            "name": "Alice Private Project",
            "description": "Secret research",
            "objective": "Classified",
        },
        headers=auth_a,
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # Bob cannot view Alice's project
    assert client.get(f"/api/projects/{project_id}", headers=auth_b).status_code == 404

    # Bob cannot see Alice's project in his list
    bob_projects = client.get("/api/projects", headers=auth_b).json()
    assert project_id not in [p["id"] for p in bob_projects]

    # Alice adds a note
    note_res = client.post(
        "/api/notes",
        json={
            "project_id": project_id,
            "title": "Private Research Note",
            "content": "Secret note contents",
        },
        headers=auth_a,
    )
    assert note_res.status_code == 201
    note_id = note_res.json()["id"]

    # Bob cannot read, update, or delete Alice's note
    assert client.get(f"/api/notes/{note_id}", headers=auth_b).status_code == 404
    assert client.patch(f"/api/notes/{note_id}", json={"content": "hacked"}, headers=auth_b).status_code == 404
    assert client.delete(f"/api/notes/{note_id}", headers=auth_b).status_code == 404


def test_export_reports_isolation(user_a, user_b):
    """Verify Alice's generated reports cannot be listed or downloaded by Bob."""
    u_a, token_a = user_a
    u_b, token_b = user_b

    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # Alice first saves a paper into her library to anchor the report
    p_res = client.post(
        "/api/papers/save",
        json={
            "title": "Post-Quantum Key Exchange Survey",
            "authors": ["Alice"],
            "year": 2026,
            "source": "OpenAlex",
            "doi": f"10.1000/export.{uuid.uuid4().hex[:8]}",
            "abstract": "Survey of lattice based protocols.",
        },
        headers=auth_a,
    )
    assert p_res.status_code == 201

    # Alice generates a report
    rep_res = client.post(
        "/api/exports/report",
        json={
            "title": "Alice Literature Review",
            "report_type": "literature_review",
            "format": "md",
            "citation_style": "IEEE",
        },
        headers=auth_a,
    )
    assert rep_res.status_code == 201
    report_id = rep_res.json()["id"]

    # Alice can download her report
    assert client.get(f"/api/exports/{report_id}/download", headers=auth_a).status_code == 200

    # Bob cannot download Alice's report
    assert client.get(f"/api/exports/{report_id}/download", headers=auth_b).status_code == 404

    # Bob's list does not contain Alice's report
    bob_reports = client.get("/api/exports", headers=auth_b).json()
    assert report_id not in [r["id"] for r in bob_reports]


def test_background_job_isolation(user_a, user_b):
    """Verify Alice's background jobs and Celery tasks are hidden from Bob."""
    u_a, token_a = user_a
    u_b, token_b = user_b

    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # Insert a job for Alice
    job_id = f"job_alice_{uuid.uuid4().hex[:10]}"
    with SessionLocal() as db:
        job = BackgroundJob(
            id=job_id,
            user_id=str(u_a.id),
            job_type="pdf_embedding",
            status="completed",
            progress=100,
            payload_json=json.dumps({"document": "secret.pdf"}),
            result_json=json.dumps({"chunks": 12}),
        )
        db.add(job)
        db.commit()

    # Alice can access her job
    res_a = client.get(f"/api/operations/jobs/{job_id}", headers=auth_a)
    assert res_a.status_code == 200

    # Bob CANNOT access Alice's job
    res_b = client.get(f"/api/operations/jobs/{job_id}", headers=auth_b)
    assert res_b.status_code == 404


def test_chat_paper_isolation(user_a, user_b):
    """Verify Bob cannot run RAG chat over Alice's paper."""
    u_a, token_a = user_a
    u_b, token_b = user_b

    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # Alice saves a paper
    p_res = client.post(
        "/api/papers/save",
        json={
            "title": "Quantum Resistance Benchmark",
            "authors": ["Alice"],
            "year": 2026,
            "source": "OpenAlex",
            "doi": f"10.1000/qr.{uuid.uuid4().hex[:8]}",
            "abstract": "Private findings on quantum resistance.",
        },
        headers=auth_a,
    )
    paper_id = p_res.json()["id"]

    # Bob tries to chat with Alice's paper
    chat_res = client.post(
        f"/api/chat/paper/{paper_id}",
        json={"question": "What are Alice's secrets?"},
        headers=auth_b,
    )
    assert chat_res.status_code == 404
