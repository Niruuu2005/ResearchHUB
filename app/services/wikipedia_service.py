import logging
import urllib.parse
from typing import Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WikipediaService:
    """Async service adapter for the official public Wikipedia API."""

    def __init__(self, timeout: Optional[float] = None, user_agent: Optional[str] = None):
        self.timeout = timeout or settings.request_timeout
        self.headers = {"User-Agent": user_agent or settings.user_agent}

    async def fetch_summary(self, topic: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Fetch topic summary from Wikipedia.

        Returns:
            Tuple of (title, summary_extract, page_url)
            or (None, None, None) if not found or on error.
        """
        clean_topic = topic.strip()
        encoded_topic = urllib.parse.quote(clean_topic.replace(" ", "_"))

        # 1. Attempt direct summary REST endpoint
        rest_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            try:
                response = await client.get(rest_url)
                if response.status_code == 200:
                    data = response.json()
                    extract = data.get("extract")
                    title = data.get("title", clean_topic)
                    page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
                    if not page_url:
                        page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

                    if extract and len(extract.strip()) > 0:
                        return title, extract.strip(), page_url

                # 2. Fallback to Wikipedia search API if direct page not matched
                search_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": clean_topic,
                    "format": "json",
                    "utf8": "1",
                    "srlimit": "1",
                }
                search_resp = await client.get(search_url, params=params)
                if search_resp.status_code == 200:
                    search_data = search_resp.json()
                    search_results = search_data.get("query", {}).get("search", [])
                    if search_results:
                        top_title = search_results[0].get("title")
                        if top_title:
                            top_encoded = urllib.parse.quote(top_title.replace(" ", "_"))
                            top_resp = await client.get(
                                f"https://en.wikipedia.org/api/rest_v1/page/summary/{top_encoded}"
                            )
                            if top_resp.status_code == 200:
                                top_data = top_resp.json()
                                extract = top_data.get("extract")
                                title = top_data.get("title", top_title)
                                page_url = (
                                    top_data.get("content_urls", {})
                                    .get("desktop", {})
                                    .get("page", f"https://en.wikipedia.org/wiki/{top_encoded}")
                                )
                                if extract and len(extract.strip()) > 0:
                                    return title, extract.strip(), page_url

                return None, None, None

            except httpx.TimeoutException as exc:
                logger.warning(f"Wikipedia request timed out for topic '{topic}': {exc}")
                raise TimeoutError("Wikipedia service timed out.") from exc
            except httpx.HTTPError as exc:
                logger.warning(f"Wikipedia HTTP error for topic '{topic}': {exc}")
                raise RuntimeError(f"Wikipedia HTTP error: {exc}") from exc
            except Exception as exc:
                logger.error(f"Unexpected error querying Wikipedia for '{topic}': {exc}")
                raise
