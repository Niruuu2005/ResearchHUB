import logging
from typing import List, Optional
import httpx

from app.config import settings
from app.models.schemas import Paper

logger = logging.getLogger(__name__)


def reconstruct_openalex_abstract(inverted_index: Optional[dict]) -> Optional[str]:
    """Rebuild plain-text abstract from OpenAlex abstract_inverted_index."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return None
    positions = []
    for word, idxs in inverted_index.items():
        if not isinstance(idxs, list):
            continue
        for idx in idxs:
            try:
                positions.append((int(idx), str(word)))
            except (TypeError, ValueError):
                continue
    if not positions:
        return None
    positions.sort(key=lambda x: x[0])
    text = " ".join(word for _, word in positions).strip()
    return text or None


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    d = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.lower().startswith(prefix):
            d = d[len(prefix) :]
            break
    return d.strip() or None


class OpenAlexService:
    """Async service adapter for the OpenAlex Academic Works API."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, timeout: Optional[float] = None, max_papers: Optional[int] = None):
        self.timeout = timeout or settings.request_timeout
        self.max_papers = max_papers or settings.max_papers_per_provider
        self.headers = {"User-Agent": settings.user_agent}

    def _parse_work(self, item: dict) -> Optional[Paper]:
        title = item.get("display_name") or item.get("title")
        if not title:
            return None

        authors: List[str] = []
        for authorship in item.get("authorships", []):
            author_name = authorship.get("author", {}).get("display_name")
            if author_name and author_name not in authors:
                authors.append(author_name)

        year = item.get("publication_year")
        doi = item.get("doi")
        url = (
            item.get("primary_location", {}).get("landing_page_url")
            or doi
            or item.get("id")
        )

        abstract = reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
        if not abstract and isinstance(item.get("abstract"), str):
            abstract = item.get("abstract").strip() or None

        open_access = bool(item.get("open_access", {}).get("is_oa"))
        pdf_url = (
            item.get("open_access", {}).get("oa_url")
            or item.get("best_oa_location", {}).get("pdf_url")
            or item.get("primary_location", {}).get("pdf_url")
        )

        venue = None
        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}
        if isinstance(source, dict):
            venue = source.get("display_name")

        return Paper(
            title=title.strip(),
            authors=authors[:5],
            year=year,
            source="OpenAlex",
            url=url,
            doi=doi,
            venue=venue,
            open_access=open_access,
            pdf_url=pdf_url,
            abstract=abstract,
        )

    async def search_papers(self, topic: str) -> List[Paper]:
        """Query OpenAlex for academic papers related to the given topic."""
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
                    paper = self._parse_work(item)
                    if paper:
                        papers.append(paper)
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

    async def fetch_by_doi(self, doi: str) -> Optional[Paper]:
        """Fetch a single OpenAlex work by DOI and return normalized Paper metadata."""
        clean = normalize_doi(doi)
        if not clean:
            return None
        work_id = f"https://doi.org/{clean}"
        url = f"{self.BASE_URL}/{work_id}"

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.info(f"OpenAlex DOI lookup failed ({response.status_code}) for {clean}")
                    return None
                return self._parse_work(response.json())
            except Exception as exc:
                logger.warning(f"OpenAlex DOI lookup error for {clean}: {exc}")
                return None
