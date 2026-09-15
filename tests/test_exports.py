import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_citation_bulk_export():
    # Save a paper
    paper_res = client.post(
        "/api/papers/save",
        json={
            "title": "Continuous Integration in Cloud-Native Systems",
            "authors": ["Dr. Maya Lin"],
            "year": 2026,
            "source": "OpenAlex",
            "doi": "10.1109/cicd.2026.1",
        },
    )
    paper_id = paper_res.json()["id"]

    # Export citations
    res = client.post(
        "/api/citations/export",
        json={"paper_ids": [paper_id], "style": "IEEE"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["citations"]) == 1
    assert "bibtex" in data
    assert "@article" in data["bibtex"]


def test_report_export_lifecycle():
    # 1. Export as Markdown
    res_md = client.post(
        "/api/exports/report",
        json={
            "title": "Automated Cloud DevOps Review",
            "report_type": "literature_review",
            "format": "md",
            "citation_style": "IEEE",
        },
    )
    assert res_md.status_code == 201
    data_md = res_md.json()
    assert data_md["format"] == "md"
    assert "download_url" in data_md

    # 2. Export as PDF
    res_pdf = client.post(
        "/api/exports/report",
        json={
            "title": "Automated Cloud DevOps Review",
            "report_type": "literature_review",
            "format": "pdf",
            "citation_style": "IEEE",
        },
    )
    assert res_pdf.status_code == 201
    assert res_pdf.json()["format"] == "pdf"

    # 3. List exports
    list_res = client.get("/api/exports")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 2


def test_export_project_id_filter():
    proj = client.post(
        "/api/projects",
        json={"name": "Export Filter Project", "description": "Filter test", "objective": "Scope exports"},
    )
    assert proj.status_code in (200, 201)
    project_id = proj.json()["id"]

    paper = client.post(
        "/api/papers/save",
        json={
            "title": "Export Scope Anchor Paper",
            "authors": ["Filter Author"],
            "year": 2025,
            "source": "OpenAlex",
            "doi": "10.1000/export.scope.anchor",
            "abstract": "Paper used to allow project-scoped export generation.",
        },
    )
    assert paper.status_code in (200, 201)
    paper_id = paper.json()["id"]
    link = client.post(f"/api/projects/{project_id}/papers", json={"paper_id": paper_id})
    assert link.status_code in (200, 201)

    scoped = client.post(
        "/api/exports/report",
        json={
            "title": "Project Scoped Export",
            "report_type": "literature_review",
            "format": "md",
            "citation_style": "IEEE",
            "project_id": project_id,
        },
    )
    assert scoped.status_code == 201
    assert scoped.json()["project_id"] == project_id

    other = client.post(
        "/api/exports/report",
        json={
            "title": "Global Export Unscoped",
            "report_type": "literature_review",
            "format": "md",
            "citation_style": "IEEE",
            "paper_ids": [paper_id],
        },
    )
    assert other.status_code == 201
    assert other.json().get("project_id") is None

    filtered = client.get(f"/api/exports?project_id={project_id}")
    assert filtered.status_code == 200
    rows = filtered.json()
    assert len(rows) >= 1
    assert all(r["project_id"] == project_id for r in rows)
    assert any(r["title"] == "Project Scoped Export" for r in rows)
    assert not any(r["title"] == "Global Export Unscoped" for r in rows)
