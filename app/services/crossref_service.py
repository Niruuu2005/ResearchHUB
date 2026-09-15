import html
import logging
import re
from typing import List, Optional
import httpx

from app.config import settings
from app.models.schemas import Paper
from app.services.openalex_service import normalize_doi

logger = logging.getLogger(__name__)


def clean_crossref_abstract(raw: Optional[str]) -> Optional[str]:
    """Strip JATS/HTML and unescape entities from Crossref abstract fields."""
    if not raw or not isinstance(raw, str):
        return None
    text = html.unescape(html.unescape(raw))
    text = re.sub(r"</?jats:[^>\s]+[^>]*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


class CrossrefService:
    """Async service adapter for the Crossref Academic Works API."""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, timeout: Optional[float] = None, max_papers: Optional[int] = None):
        self.timeout = timeout or settings.request_timeout
        self.max_papers = max_papers or settings.max_papers_per_provider
        self.headers = {"User-Agent": settings.user_agent}

    def _parse_item(self, item: dict) -> Optional[Paper]:
        titles = item.get("title", [])
        if not titles or not titles[0]:
            return None
        title = titles[0].strip()

        authors: List[str] = []
        for author_dict in item.get("author", []):
            given = (author_dict.get("given") or "").strip()
            family = (author_dict.get("family") or "").strip()
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)

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
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else None)
        abstract = clean_crossref_abstract(item.get("abstract"))
        container = item.get("container-title") or []
        venue = container[0] if container else None

        return Paper(
            title=title,
            authors=authors[:5],
            year=year,
            source="Crossref",
            url=url,
            doi=doi,
            venue=venue,
            abstract=abstract,
        )

    async def search_papers(self, topic: str) -> List[Paper]:
        """Query Crossref for academic publications matching the topic."""
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
                    paper = self._parse_item(item)
                    if paper:
                        papers.append(paper)
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

    async def fetch_by_doi(self, doi: str) -> Optional[Paper]:
        """Fetch a single Crossref work by DOI."""
        clean = normalize_doi(doi)
        if not clean:
            return None
        url = f"{self.BASE_URL}/{clean}"
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.info(f"Crossref DOI lookup failed ({response.status_code}) for {clean}")
                    return None
                return self._parse_item(response.json().get("message", {}))
            except Exception as exc:
                logger.warning(f"Crossref DOI lookup error for {clean}: {exc}")
                return None
