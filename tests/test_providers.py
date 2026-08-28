from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.models.schemas import Paper
from app.services.crossref_service import CrossrefService
from app.services.openalex_service import OpenAlexService
from app.services.research_service import ResearchService
from app.services.wikipedia_service import WikipediaService


@pytest.mark.asyncio
async def test_wikipedia_service_mocked():
    """Test Wikipedia service parsing with mocked response."""
    service = WikipediaService()

    mock_resp = {
        "title": "Quantum Computing",
        "extract": "Quantum computing is a type of computation whose operations can exploit phenomena of quantum mechanics.",
        "content_urls": {
            "desktop": {
                "page": "https://en.wikipedia.org/wiki/Quantum_computing"
            }
        },
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            status_code=200,
            json=mock_resp,
            request=httpx.Request("GET", "https://en.wikipedia.org"),
        )

        title, extract, url = await service.fetch_summary("Quantum Computing")
        assert title == "Quantum Computing"
        assert "Quantum computing is a type of computation" in extract
        assert url == "https://en.wikipedia.org/wiki/Quantum_computing"


@pytest.mark.asyncio
async def test_openalex_service_mocked():
    """Test OpenAlex service parsing with mocked works response."""
    service = OpenAlexService()

    mock_data = {
        "results": [
            {
                "display_name": "Deep Residual Learning for Image Recognition",
                "authorships": [
                    {"author": {"display_name": "Kaiming He"}},
                    {"author": {"display_name": "Xiangyu Zhang"}},
                ],
                "publication_year": 2016,
                "doi": "https://doi.org/10.1109/cvpr.2016.90",
                "primary_location": {
                    "landing_page_url": "https://doi.org/10.1109/cvpr.2016.90"
                },
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            status_code=200,
            json=mock_data,
            request=httpx.Request("GET", "https://api.openalex.org"),
        )

        papers = await service.search_papers("Deep Residual Learning")
        assert len(papers) == 1
        assert papers[0].title == "Deep Residual Learning for Image Recognition"
        assert papers[0].authors == ["Kaiming He", "Xiangyu Zhang"]
        assert papers[0].year == 2016
        assert papers[0].source == "OpenAlex"


@pytest.mark.asyncio
async def test_crossref_service_mocked():
    """Test Crossref service parsing with mocked items response."""
    service = CrossrefService()

    mock_data = {
        "message": {
            "items": [
                {
                    "title": ["Attention Is All You Need"],
                    "author": [
                        {"given": "Ashish", "family": "Vaswani"},
                        {"given": "Noam", "family": "Shazeer"},
                    ],
                    "published-print": {
                        "date-parts": [[2017, 12]]
                    },
                    "DOI": "10.5555/3295222.3295349",
                    "URL": "http://dx.doi.org/10.5555/3295222.3295349",
                }
            ]
        }
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            status_code=200,
            json=mock_data,
            request=httpx.Request("GET", "https://api.crossref.org"),
        )

        papers = await service.search_papers("Attention Is All You Need")
        assert len(papers) == 1
        assert papers[0].title == "Attention Is All You Need"
        assert papers[0].authors == ["Ashish Vaswani", "Noam Shazeer"]
        assert papers[0].year == 2017
        assert papers[0].source == "Crossref"


@pytest.mark.asyncio
async def test_research_service_partial_failure_handling():
    """
    Test that when Crossref throws a TimeoutError, the research service still
    successfully returns Wikipedia summary and OpenAlex papers, attaching a warning.
    """
    mock_wiki = AsyncMock(spec=WikipediaService)
    mock_wiki.fetch_summary.return_value = (
        "Quantum Computing",
        "Quantum computing harnesses quantum phenomena to perform calculations.",
        "https://en.wikipedia.org/wiki/Quantum_computing",
    )

    mock_openalex = AsyncMock(spec=OpenAlexService)
    mock_openalex.search_papers.return_value = [
        Paper(
            title="Quantum Computation and Quantum Information",
            authors=["Michael A. Nielsen", "Isaac L. Chuang"],
            year=2010,
            source="OpenAlex",
            url="https://doi.org/10.1017/cbo9780511976667",
            doi="10.1017/cbo9780511976667",
        )
    ]

    mock_crossref = AsyncMock(spec=CrossrefService)
    mock_crossref.search_papers.side_effect = TimeoutError("Crossref upstream gateway timeout")

    research_svc = ResearchService(
        wikipedia_service=mock_wiki,
        openalex_service=mock_openalex,
        crossref_service=mock_crossref,
    )

    response = await research_svc.perform_research("Quantum Computing")

    assert response.topic == "Quantum Computing"
    assert "Quantum computing harnesses" in response.summary
    assert len(response.papers) == 1
    assert response.papers[0].source == "OpenAlex"
    assert len(response.warnings) == 1
    assert "Crossref service is temporarily unavailable" in response.warnings[0]
    assert len(response.sources) >= 1


def test_research_service_deduplication():
    """Verify deduplication filters duplicate DOIs and titles."""
    svc = ResearchService()
    papers = [
        Paper(title="Paper One", authors=["A"], year=2021, source="OpenAlex", doi="10.1234/abc"),
        Paper(title="Paper ONE", authors=["A"], year=2021, source="Crossref", doi="10.1234/abc"),
        Paper(title="Paper Two", authors=["B"], year=2022, source="OpenAlex", doi="10.1234/def"),
        Paper(title="paper two", authors=["B"], year=2022, source="Crossref", doi="10.1234/other"),
    ]

    deduped = svc._deduplicate_papers(papers)
    assert len(deduped) == 2
    assert deduped[0].title in ["Paper Two", "paper two"]  # Year 2022 sorted first
    assert deduped[1].title in ["Paper One", "Paper ONE"]
