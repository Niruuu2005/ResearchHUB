from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Paper, ResearchResponse

client = TestClient(app)


def test_research_endpoint_empty_topic():
    """Verify that an empty topic returns HTTP 422 Unprocessable Entity."""
    response = client.post("/research", json={"topic": ""})
    assert response.status_code == 422

    response_spaces = client.post("/research", json={"topic": "   "})
    assert response_spaces.status_code == 422


def test_research_endpoint_missing_body():
    """Verify that missing payload returns HTTP 422."""
    response = client.post("/research", json={})
    assert response.status_code == 422


@patch("app.api.routes.research_service.perform_research")
def test_research_endpoint_success(mock_perform_research):
    """Verify successful research execution returns valid ResearchResponse schema."""
    mock_perform_research.return_value = ResearchResponse(
        topic="Quantum Computing",
        summary="Quantum computing is a rapidly-emerging technology that harnesses quantum mechanics.",
        key_points=[
            "Quantum computing harnesses the laws of quantum mechanics.",
            "Solves problems too complex for classical computers.",
        ],
        papers=[
            Paper(
                title="Quantum supremacy using a programmable superconducting processor",
                authors=["Frank Arute", "John M. Martinis"],
                year=2019,
                source="OpenAlex",
                url="https://doi.org/10.1038/s41586-019-1666-5",
                doi="10.1038/s41586-019-1666-5",
            )
        ],
        sources=[],
        warnings=[],
    )

    response = client.post("/research", json={"topic": "Quantum Computing"})
    assert response.status_code == 200
    data = response.json()

    assert data["topic"] == "Quantum Computing"
    assert "Quantum computing" in data["summary"]
    assert len(data["key_points"]) == 2
    assert len(data["papers"]) == 1
    assert data["papers"][0]["source"] == "OpenAlex"
    assert data["warnings"] == []


@patch("app.api.routes.research_service.get_papers_only")
def test_papers_endpoint_success(mock_get_papers):
    """Verify that /papers returns a list of papers."""
    mock_get_papers.return_value = [
        Paper(
            title="A survey on DevOps tools and practices",
            authors=["Alice Smith", "Bob Jones"],
            year=2023,
            source="Crossref",
            url="https://doi.org/10.1000/example",
            doi="10.1000/example",
        )
    ]

    response = client.get("/papers?topic=DevOps")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "A survey on DevOps tools and practices"
    assert data[0]["source"] == "Crossref"


def test_papers_endpoint_missing_param():
    """Verify that omitting topic query parameter returns HTTP 422."""
    response = client.get("/papers")
    assert response.status_code == 422
