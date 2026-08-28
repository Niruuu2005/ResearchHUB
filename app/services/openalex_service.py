import logging
from typing import List, Optional
import httpx

from app.config import settings
from app.models.schemas import Paper

logger = logging.getLogger(__name__)


class OpenAlexService:
    """Async service adapter for the OpenAlex Academic Works API."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, timeout: Optional[float] = None, max_papers: Optional[int] = None):
        self.timeout = timeout or settings.request_timeout
        self.max_papers = max_papers or settings.max_papers_per_provider
        self.headers = {"User-Agent": settings.user_agent}

    async def search_papers(self, topic: str) -> List[Paper]:
        """
        Query OpenAlex for academic papers related to the given topic.

        Returns:
            List of normalized Paper models.
        """
        clean_topic = topic.strip()
        params = {
            "search": clean_topic,
            "per_page": self.max_papers,
            "sort": "relevance_score:desc",
        }

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            try:
                response = await client.get(self.BASE_URL, params=params)
                if response.status_code != 200:
                    logger.warning(f"OpenAlex returned status {response.status_code} for topic '{topic}'")
                    return []

                data = response.json()
                results = data.get("results", [])
                papers: List[Paper] = []

                for item in results:
                    title = item.get("display_name") or item.get("title")
                    if not title:
                        continue

                    # Extract author names
                    authors: List[str] = []
                    for authorship in item.get("authorships", []):
                        author_name = authorship.get("author", {}).get("display_name")
                        if author_name and author_name not in authors:
                            authors.append(author_name)

                    year = item.get("publication_year")

                    # Extract DOI and URL
                    doi = item.get("doi")
                    url = (
                        item.get("primary_location", {}).get("landing_page_url")
                        or doi
                        or item.get("id")
                    )

                    papers.append(
                        Paper(
                            title=title.strip(),
                            authors=authors[:5],  # Cap at 5 authors for readability
                            year=year,
                            source="OpenAlex",
                            url=url,
                            doi=doi,
                        )
                    )

                return papers

            except httpx.TimeoutException as exc:
                logger.warning(f"OpenAlex request timed out for topic '{topic}': {exc}")
                raise TimeoutError("OpenAlex service timed out.") from exc
            except httpx.HTTPError as exc:
                logger.warning(f"OpenAlex HTTP error for topic '{topic}': {exc}")
                raise RuntimeError(f"OpenAlex HTTP error: {exc}") from exc
            except Exception as exc:
                logger.error(f"Unexpected error querying OpenAlex for '{topic}': {exc}")
                raise
