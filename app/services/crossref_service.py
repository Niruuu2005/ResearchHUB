import logging
from typing import List, Optional
import httpx

from app.config import settings
from app.models.schemas import Paper

logger = logging.getLogger(__name__)


class CrossrefService:
    """Async service adapter for the Crossref Academic Works API."""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, timeout: Optional[float] = None, max_papers: Optional[int] = None):
        self.timeout = timeout or settings.request_timeout
        self.max_papers = max_papers or settings.max_papers_per_provider
        self.headers = {"User-Agent": settings.user_agent}

    async def search_papers(self, topic: str) -> List[Paper]:
        """
        Query Crossref for academic publications matching the topic.

        Returns:
            List of normalized Paper models.
        """
        clean_topic = topic.strip()
        params = {
            "query.bibliographic": clean_topic,
            "rows": self.max_papers,
            "sort": "relevance",
        }

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            try:
                response = await client.get(self.BASE_URL, params=params)
                if response.status_code != 200:
                    logger.warning(f"Crossref returned status {response.status_code} for topic '{topic}'")
                    return []

                data = response.json()
                items = data.get("message", {}).get("items", [])
                papers: List[Paper] = []

                for item in items:
                    titles = item.get("title", [])
                    if not titles or not titles[0]:
                        continue
                    title = titles[0].strip()

                    # Extract author names
                    authors: List[str] = []
                    for author_dict in item.get("author", []):
                        given = author_dict.get("given", "").strip()
                        family = author_dict.get("family", "").strip()
                        if given and family:
                            authors.append(f"{given} {family}")
                        elif family:
                            authors.append(family)
                        elif given:
                            authors.append(given)

                    # Extract year
                    year = None
                    date_parts = (
                        item.get("published-print", {}).get("date-parts")
                        or item.get("published-online", {}).get("date-parts")
                        or item.get("issued", {}).get("date-parts")
                        or item.get("created", {}).get("date-parts")
                    )
                    if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
                        try:
                            year = int(date_parts[0][0])
                        except (ValueError, TypeError):
                            year = None

                    doi = item.get("DOI")
                    url = (
                        item.get("URL")
                        or (f"https://doi.org/{doi}" if doi else None)
                    )

                    papers.append(
                        Paper(
                            title=title,
                            authors=authors[:5],
                            year=year,
                            source="Crossref",
                            url=url,
                            doi=doi,
                        )
                    )

                return papers

            except httpx.TimeoutException as exc:
                logger.warning(f"Crossref request timed out for topic '{topic}': {exc}")
                raise TimeoutError("Crossref service timed out.") from exc
            except httpx.HTTPError as exc:
                logger.warning(f"Crossref HTTP error for topic '{topic}': {exc}")
                raise RuntimeError(f"Crossref HTTP error: {exc}") from exc
            except Exception as exc:
                logger.error(f"Unexpected error querying Crossref for '{topic}': {exc}")
                raise
