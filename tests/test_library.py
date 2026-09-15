import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_save_and_retrieve_paper():
    payload = {
        "title": "Adversarial Robustness in Multi-Agent Systems",
        "authors": ["Dr. Elena Rostova", "Marcus Vance"],
        "year": 2025,
        "source": "OpenAlex",
        "doi": "10.1145/example.adv.2025",
        "venue": "ACM Conference on Computer and Communications Security",
        "open_access": True,
        "pdf_url": "https://example.edu/paper.pdf",
        "abstract": "We evaluate privilege escalation dynamics in multi-agent environments.",
    }

    # Save
    res = client.post("/api/papers/save", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == payload["title"]
    paper_id = data["id"]

    # Retrieve by ID
    get_res = client.get(f"/api/papers/{paper_id}")
    assert get_res.status_code == 200
    assert get_res.json()["doi"] == payload["doi"]

    # Related papers
    rel_res = client.get(f"/api/papers/{paper_id}/related")
    assert rel_res.status_code == 200
    assert isinstance(rel_res.json(), list)

    # Citation
    cite_res = client.get(f"/api/papers/{paper_id}/citation?style=IEEE")
    assert cite_res.status_code == 200
    cite_data = cite_res.json()
    assert "Elena Rostova" in cite_data["formatted_text"] or "E. Rostova" in cite_data["formatted_text"]
    assert "bibtex" in cite_data
