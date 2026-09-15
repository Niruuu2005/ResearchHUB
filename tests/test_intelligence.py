import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_summarization_and_comparison_lifecycle():
    # 1. Create two test papers
    p1_res = client.post(
        "/api/papers/save",
        json={
            "title": "Quantum Resistance in Lattice-Based Cryptography",
            "authors": ["Alice Chen"],
            "year": 2024,
            "source": "OpenAlex",
            "doi": "10.1000/quantum.lattice",
            "abstract": "We analyze post-quantum key exchange mechanisms against Shor's algorithm.",
        },
    )
    p2_res = client.post(
        "/api/papers/save",
        json={
            "title": "Isogeny-Based Key Encapsulation Mechanisms",
            "authors": ["Bob Kumar"],
            "year": 2025,
            "source": "Crossref",
            "doi": "10.1000/quantum.isogeny",
            "abstract": "Evaluating memory overhead of supersingular isogeny Diffie-Hellman protocols.",
        },
    )

    paper1_id = p1_res.json()["id"]
    paper2_id = p2_res.json()["id"]

    # 2. Test Paper Summary
    sum_res = client.post(f"/api/papers/{paper1_id}/summarize")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert "research_problem" in sum_data
    assert "objective" in sum_data
    assert "methodology" in sum_data
    assert "key_results" in sum_data
    assert "limitations" in sum_data
    assert "future_work" in sum_data
    assert len(sum_data["keywords"]) > 0

    # 3. Test Paper Comparison
    comp_res = client.post("/api/compare", json={"paper_ids": [paper1_id, paper2_id]})
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert len(comp_data["matrix"]) == 2
    assert "similarities" in comp_data
    assert "differences" in comp_data
    assert "research_gaps" in comp_data

    # 4. Test Literature Review
    lit_res = client.post(
        "/api/literature-review",
        json={
            "paper_ids": [paper1_id, paper2_id],
            "topic": "Post-Quantum Cryptography",
            "citation_style": "IEEE",
        },
    )
    assert lit_res.status_code == 200
    lit_data = lit_res.json()
    assert "1. Introduction" in lit_data["sections"]
    assert "8. Research Gaps" in lit_data["sections"]
    assert len(lit_data["references"]) >= 2
    assert lit_data["papers_analyzed"] >= 2
    assert set(lit_data["paper_ids"]) == {paper1_id, paper2_id}


def test_list_summaries_empty_then_populated():
    empty = client.get("/api/summaries")
    assert empty.status_code == 200
    assert isinstance(empty.json(), list)
    before_count = len(empty.json())

    unique = "summaries-list-" + str(__import__("uuid").uuid4())
    paper_res = client.post(
        "/api/papers/save",
        json={
            "title": f"Summaries List Probe Paper {unique}",
            "authors": ["Test Author"],
            "year": 2024,
            "source": "OpenAlex",
            "doi": f"10.1000/{unique}",
            "abstract": "Probe abstract for list summaries endpoint.",
        },
    )
    assert paper_res.status_code in (200, 201)
    paper_id = paper_res.json()["id"]

    before_ids = {s["paper_id"] for s in client.get("/api/summaries").json()}
    assert paper_id not in before_ids

    sum_res = client.post(f"/api/papers/{paper_id}/summarize")
    assert sum_res.status_code == 200

    after = client.get("/api/summaries").json()
    assert len(after) >= before_count + 1
    assert any(s["paper_id"] == paper_id for s in after)
    match = next(s for s in after if s["paper_id"] == paper_id)
    assert match["title"]
    assert match["research_problem"]
