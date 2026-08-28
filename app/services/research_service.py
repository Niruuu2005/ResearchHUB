import asyncio
import logging
import re
from typing import List, Optional, Set
from app.models.schemas import Paper, ResearchResponse, Source
from app.services.crossref_service import CrossrefService
from app.services.openalex_service import OpenAlexService
from app.services.wikipedia_service import WikipediaService

logger = logging.getLogger(__name__)


class ResearchService:
    """Orchestrates topic research across multiple academic and informational providers."""

    def __init__(
        self,
        wikipedia_service: Optional[WikipediaService] = None,
        openalex_service: Optional[OpenAlexService] = None,
        crossref_service: Optional[CrossrefService] = None,
    ):
        self.wikipedia = wikipedia_service or WikipediaService()
        self.openalex = openalex_service or OpenAlexService()
        self.crossref = crossref_service or CrossrefService()

    async def perform_research(self, topic: str) -> ResearchResponse:
        """
        Execute comprehensive research for a topic concurrently across all providers.
        Handles partial provider failures gracefully without failing the overall request.
        """
        clean_topic = topic.strip()
        warnings: List[str] = []
        sources: List[Source] = []

        # Run provider queries in parallel
        wiki_task = self.wikipedia.fetch_summary(clean_topic)
        openalex_task = self.openalex.search_papers(clean_topic)
        crossref_task = self.crossref.search_papers(clean_topic)

        results = await asyncio.gather(
            wiki_task,
            openalex_task,
            crossref_task,
            return_exceptions=True,
        )

        # 1. Process Wikipedia Result
        wiki_result = results[0]
        summary_text = ""
        canonical_title = clean_topic
        wiki_url = None

        if isinstance(wiki_result, Exception):
            logger.warning(f"Wikipedia provider failed: {wiki_result}")
            warnings.append(f"Wikipedia service encountered an issue: {str(wiki_result)}")
        elif isinstance(wiki_result, tuple):
            title, extract, url = wiki_result
            if extract:
                summary_text = extract
                canonical_title = title or clean_topic
                wiki_url = url
                sources.append(
                    Source(
                        name="Wikipedia",
                        title=canonical_title,
                        url=wiki_url or "https://en.wikipedia.org",
                    )
                )
            else:
                warnings.append(f"No direct Wikipedia article found for '{clean_topic}'.")

        # 2. Process OpenAlex Result
        openalex_papers: List[Paper] = []
        openalex_result = results[1]
        if isinstance(openalex_result, Exception):
            logger.warning(f"OpenAlex provider failed: {openalex_result}")
            warnings.append(f"OpenAlex service is temporarily unavailable: {str(openalex_result)}")
        elif isinstance(openalex_result, list):
            openalex_papers = openalex_result
            if openalex_papers:
                sources.append(
                    Source(
                        name="OpenAlex",
                        title=f"OpenAlex Works Index ({len(openalex_papers)} publications)",
                        url=f"https://openalex.org/works?search={clean_topic}",
                    )
                )

        # 3. Process Crossref Result
        crossref_papers: List[Paper] = []
        crossref_result = results[2]
        if isinstance(crossref_result, Exception):
            logger.warning(f"Crossref provider failed: {crossref_result}")
            warnings.append(f"Crossref service is temporarily unavailable: {str(crossref_result)}")
        elif isinstance(crossref_result, list):
            crossref_papers = crossref_result
            if crossref_papers:
                sources.append(
                    Source(
                        name="Crossref",
                        title=f"Crossref Bibliographic Registry ({len(crossref_papers)} publications)",
                        url="https://search.crossref.org",
                    )
                )

        # Merge and deduplicate academic papers
        all_papers = self._deduplicate_papers(openalex_papers + crossref_papers)

        # Fallback summary if Wikipedia was empty
        if not summary_text:
            if all_papers:
                summary_text = (
                    f"Academic overview for '{clean_topic}'. Retrieved {len(all_papers)} "
                    f"relevant publications from scholarly indexes."
                )
            else:
                summary_text = (
                    f"No detailed summary could be retrieved for '{clean_topic}'. "
                    "Please verify the topic spelling or query terms."
                )

        # Derive key points from the summary
        key_points = self._extract_key_points(summary_text)

        return ResearchResponse(
            topic=clean_topic,
            summary=summary_text,
            key_points=key_points,
            papers=all_papers,
            sources=sources,
            warnings=warnings,
        )

    async def get_papers_only(self, topic: str) -> List[Paper]:
        """Query and deduplicate scholarly publications from academic providers."""
        clean_topic = topic.strip()
        openalex_task = self.openalex.search_papers(clean_topic)
        crossref_task = self.crossref.search_papers(clean_topic)

        results = await asyncio.gather(openalex_task, crossref_task, return_exceptions=True)
        papers: List[Paper] = []

        if isinstance(results[0], list):
            papers.extend(results[0])
        if isinstance(results[1], list):
            papers.extend(results[1])

        return self._deduplicate_papers(papers)

    def _deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        """Remove duplicate papers by matching DOI or normalized title."""
        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()
        unique_papers: List[Paper] = []

        for paper in papers:
            # Check DOI duplication
            if paper.doi:
                norm_doi = paper.doi.lower().strip()
                if norm_doi in seen_dois:
                    continue
                seen_dois.add(norm_doi)

            # Check Title duplication
            norm_title = re.sub(r"[^\w\s]", "", paper.title.lower()).strip()
            if not norm_title or norm_title in seen_titles:
                continue

            seen_titles.add(norm_title)
            unique_papers.append(paper)

        # Sort papers: preference for known publication year descending
        return sorted(
            unique_papers,
            key=lambda p: (p.year if p.year is not None else 0),
            reverse=True,
        )

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract structured key points from introductory text using deterministic NLP."""
        if not text:
            return []

        # Split text into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        key_points: List[str] = []

        for s in sentences:
            s_clean = s.strip()
            # Retain sentences with sufficient semantic length
            if len(s_clean) >= 25 and not s_clean.startswith("("):
                # Ensure it ends with punctuation
                if not s_clean[-1] in ".!?":
                    s_clean += "."
                key_points.append(s_clean)
                if len(key_points) >= 4:
                    break

        if not key_points and text:
            key_points = [text[:200].strip() + ("..." if len(text) > 200 else "")]

        return key_points
