import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_and_list_projects():
    # 1. Create project
    res = client.post(
        "/api/projects",
        json={
            "name": "Agentic AI Security",
            "description": "Exploration of autonomous agent vulnerabilities and defenses.",
            "objective": "Survey prompt injection and privilege escalation vectors in LLM agents.",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Agentic AI Security"
    assert data["id"] is not None
    project_id = data["id"]

    # 2. List projects
    list_res = client.get("/api/projects")
    assert list_res.status_code == 200
    projects = list_res.json()
    assert any(p["id"] == project_id for p in projects)

    # 3. Get project details
    detail_res = client.get(f"/api/projects/{project_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["name"] == "Agentic AI Security"
    assert "papers" in detail

    # 4. Update project
    update_res = client.patch(
        f"/api/projects/{project_id}",
        json={"name": "Agentic AI Security (Updated)"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Agentic AI Security (Updated)"

    # 5. Delete project
    del_res = client.delete(f"/api/projects/{project_id}")
    assert del_res.status_code == 200


def test_project_workspace_full_lifecycle():
    # 1. Save two test papers into library
    p1_res = client.post(
        "/api/papers/save",
        json={
            "title": "Adversarial Robustness in LLM Reasoning Pipelines",
            "authors": ["Alice Vance", "Bob Chen"],
            "year": 2025,
            "source": "OpenAlex",
            "venue": "IEEE S&P",
            "abstract": "We investigate adversarial prompt manipulation in multi-turn reasoning chains.",
        },
    )
    assert p1_res.status_code in [200, 201]
    paper1_id = p1_res.json()["id"]

    p2_res = client.post(
        "/api/papers/save",
        json={
            "title": "Defending Agent Workflows Against Tool Injection",
            "authors": ["Carol Danvers"],
            "year": 2026,
            "source": "Crossref",
            "venue": "ACM CCS",
            "abstract": "A sandbox verification framework preventing unconstrained subagent tool escalation.",
        },
    )
    assert p2_res.status_code in [200, 201]
    paper2_id = p2_res.json()["id"]

    # 2. Create workspace project
    proj_res = client.post(
        "/api/projects",
        json={
            "name": "Autonomous Agent Defense Lab",
            "description": "Comprehensive security analysis of agentic multi-tool architectures.",
            "objective": "Build automated mitigations against indirect prompt injection.",
        },
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 3. Add papers to workspace
    add1 = client.post(f"/api/projects/{project_id}/papers", json={"paper_id": paper1_id})
    assert add1.status_code == 200
    add2 = client.post(f"/api/projects/{project_id}/papers", json={"paper_id": paper2_id})
    assert add2.status_code == 200

    # 4. Verify project workspace reflects added papers
    get_proj = client.get(f"/api/projects/{project_id}")
    assert get_proj.status_code == 200
    proj_data = get_proj.json()
    assert proj_data["paper_count"] >= 2
    paper_ids = [p["id"] for p in proj_data["papers"]]
    assert paper1_id in paper_ids and paper2_id in paper_ids

    # 5. Generate project collection summary
    summary_res = client.post(f"/api/projects/{project_id}/summarize")
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["project_name"] == "Autonomous Agent Defense Lab"
    assert len(summary_data["major_themes"]) > 0
    assert summary_data["research_gaps"] is not None

    # 6. Chat with project workspace collection (RAG)
    chat_res = client.post(
        f"/api/chat/project/{project_id}",
        json={"question": "What are the common vulnerabilities in tool workflows?"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["answer"] is not None
    assert "citations" in chat_data

    # 7. Generate 11-section Literature Review for workspace
    lit_res = client.post(
        "/api/literature-review",
        json={"project_id": project_id, "citation_style": "IEEE"},
    )
    assert lit_res.status_code == 200
    lit_data = lit_res.json()
    assert "sections" in lit_data
    assert len(lit_data["sections"]) == 10  # 10 narrative sections + references
    assert len(lit_data["references"]) >= 2

    # 8. Remove paper from project
    rem_res = client.delete(f"/api/projects/{project_id}/papers/{paper1_id}")
    assert rem_res.status_code == 200
    verify_proj = client.get(f"/api/projects/{project_id}")
    rem_paper_ids = [p["id"] for p in verify_proj.json()["papers"]]
    assert paper1_id not in rem_paper_ids
