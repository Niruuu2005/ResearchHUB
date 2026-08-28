"""Research provider and aggregation services."""

from app.services.crossref_service import CrossrefService
from app.services.openalex_service import OpenAlexService
from app.services.research_service import ResearchService
from app.services.wikipedia_service import WikipediaService

__all__ = [
    "CrossrefService",
    "OpenAlexService",
    "ResearchService",
    "WikipediaService",
]
