import asyncio
import json
import logging
import re
from typing import List, Optional, Set
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import ResearchSession
from app.models.schemas import Paper, ResearchResponse, Source
from app.services.crossref_service import CrossrefService
from app.services.openalex_service import OpenAlexService
from app.services.wikipedia_service import WikipediaService
from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

logger = logging.getLogger(__name__)


class ResearchService:
    """Orchestrates topic research across multiple academic and informational providers with caching and circuit breakers."""

    def __init__(
        self,
        wikipedia_service: Optional[WikipediaService] = None,
        openalex_service: Optional[OpenAlexService] = None,
        crossref_service: Optional[CrossrefService] = None,
    ):
        self.wikipedia = wikipedia_service or WikipediaService()
        self.openalex = openalex_service or OpenAlexService()
        self.crossref = crossref_service or CrossrefService()

        # Circuit breakers for each provider
        self.cb_wiki = CircuitBreaker("Wikipedia", failure_threshold=3, recovery_timeout=30.0)
        self.cb_alex = CircuitBreaker("OpenAlex", failure_threshold=3, recovery_timeout=30.0)
        self.cb_cross = CircuitBreaker("Crossref", failure_threshold=3, recovery_timeout=30.0)

    def _get_redis_client(self):
        """Lazy Redis connection helper."""
        try:
            import redis
            r = redis.Redis.from_url(settings.redis_url, socket_timeout=0.5, decode_responses=True)
            r.ping()
            return r
        except Exception:
            return None

    async def perform_research(
        self,
        topic: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        open_access_only: bool = False,
        sources_filter: Optional[List[str]] = None,
        db: Optional[Session] = None,
    ) -> ResearchResponse:
        """
        Execute comprehensive research for a topic concurrently across all providers.
        Employs Redis caching and circuit breakers with graceful partial failure handling.
        """
        clean_topic = topic.strip()
        cache_key = f"research:{clean_topic.lower()}:{year_from}:{year_to}:{open_access_only}:{','.join(sorted(sources_filter or []))}"

        # 1. Attempt Redis Cache Lookup
        r_client = self._get_redis_client()
        if r_client:
            try:
                cached = r_client.get(cache_key)
                if cached:
                    logger.info(f"Cache hit in Redis for topic '{clean_topic}'")
                    data = json.loads(cached)
                    return ResearchResponse(**data)
            except Exception as e:
                logger.warning(f"Redis cache lookup failed: {e}")

        warnings: List[str] = []
        sources: List[Source] = []

        # Determine which providers to query
        run_wiki = not sources_filter or "wikipedia" in [s.lower() for s in sources_filter]
        run_openalex = not sources_filter or "openalex" in [s.lower() for s in sources_filter]
        run_crossref = not sources_filter or "crossref" in [s.lower() for s in sources_filter]

        tasks = []
        if run_wiki:
            tasks.append(self.cb_wiki.call_async(self.wikipedia.fetch_summary, clean_topic))
        else:
            tasks.append(asyncio.sleep(0, result=None))

        if run_openalex:
            tasks.append(self.cb_alex.call_async(self.openalex.search_papers, clean_topic))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        if run_crossref:
            tasks.append(self.cb_cross.call_async(self.crossref.search_papers, clean_topic))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 1. Process Wikipedia Result
        wiki_result = results[0]
        summary_text = ""
        canonical_title = clean_topic
        wiki_url = None

        if isinstance(wiki_result, CircuitBreakerOpenException):
            warnings.append(str(wiki_result))
        elif isinstance(wiki_result, Exception):
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
        if isinstance(openalex_result, CircuitBreakerOpenException):
            warnings.append(str(openalex_result))
        elif isinstance(openalex_result, Exception):
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
        if isinstance(crossref_result, CircuitBreakerOpenException):
            warnings.append(str(crossref_result))
        elif isinstance(crossref_result, Exception):
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

        # Apply filtering by year range and open-access status
        if year_from is not None:
            all_papers = [p for p in all_papers if p.year is None or p.year >= year_from]
        if year_to is not None:
            all_papers = [p for p in all_papers if p.year is None or p.year <= year_to]
        if open_access_only:
            all_papers = [p for p in all_papers if p.open_access]

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

        session_id = None
        if db is not None:
            try:
                session_rec = ResearchSession(
                    topic=clean_topic,
                    year_from=year_from,
                    year_to=year_to,
                    open_access_only=open_access_only,
                    summary=summary_text,
                    key_points_json=json.dumps(key_points),
                    warnings_json=json.dumps(warnings),
                )
                db.add(session_rec)
                db.commit()
                session_id = session_rec.id
            except Exception as e:
                logger.warning(f"Could not persist research session: {e}")

        response = ResearchResponse(
            topic=clean_topic,
            summary=summary_text,
            key_points=key_points,
            papers=all_papers,
            sources=sources,
            warnings=warnings,
            session_id=session_id,
        )

        # Cache in Redis (TTL: 1800s = 30 min)
        if r_client:
            try:
                r_client.setex(cache_key, 1800, response.model_dump_json())
            except Exception as e:
                logger.warning(f"Failed to cache research result in Redis: {e}")

        return response

    async def get_papers_only(self, topic: str) -> List[Paper]:
        """Query and deduplicate scholarly publications from academic providers."""
        clean_topic = topic.strip()
        openalex_task = self.cb_alex.call_async(self.openalex.search_papers, clean_topic)
        crossref_task = self.cb_cross.call_async(self.crossref.search_papers, clean_topic)

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

        return sorted(
            unique_papers,
            key=lambda p: (p.year if p.year is not None else 0),
            reverse=True,
        )

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract structured key points from introductory text using deterministic NLP."""
        if not text:
            return []

        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        key_points: List[str] = []

        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) >= 25 and not s_clean.startswith("("):
                if not s_clean[-1] in ".!?":
                    s_clean += "."
                key_points.append(s_clean)
                if len(key_points) >= 4:
                    break

        if not key_points and text:
            key_points = [text[:200].strip() + ("..." if len(text) > 200 else "")]

        return key_points
