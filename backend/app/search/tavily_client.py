"""
Async Tavily Search API client.
Uses httpx for non-blocking I/O with strict timeouts and error mapping.
"""
import logging
from typing import Any
import httpx

from app.core.config import get_settings
from app.core.exceptions import SearchTimeoutError, SearchUnavailableError

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"


class TavilyClient:
    def __init__(self, api_key: str | None = None, timeout: int | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.tavily_api_key
        self.timeout = timeout or settings.tavily_search_timeout

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
    ) -> list[dict[str, Any]]:
        """
        Execute an asynchronous search request to Tavily.
        Returns the raw results list from Tavily.
        Raises SearchUnavailableError or SearchTimeoutError on failures.
        """
        if not self.api_key or self.api_key.startswith("your_"):
            logger.warning("Tavily API key is missing or not configured.")
            raise SearchUnavailableError("Tavily API key is not configured.")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": False,
            "include_raw_content": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(TAVILY_API_URL, json=payload)

            if response.status_code == 401:
                logger.error("Tavily authentication failed: 401 Unauthorized")
                raise SearchUnavailableError("Tavily authentication failed.")

            if response.status_code == 429:
                logger.warning("Tavily rate limit exceeded: 429")
                raise SearchUnavailableError("Tavily rate limit exceeded.")

            response.raise_for_status()
            data = response.json()
            return data.get("results", [])

        except httpx.TimeoutException as exc:
            logger.error("Tavily search timed out for query '%s': %s", query, exc)
            raise SearchTimeoutError(f"Tavily search timed out after {self.timeout}s.") from exc
        except httpx.HTTPStatusError as exc:
            logger.error("Tavily HTTP error (%s) for query '%s': %s", exc.response.status_code, query, exc)
            raise SearchUnavailableError(f"Tavily search returned HTTP {exc.response.status_code}.") from exc
        except httpx.RequestError as exc:
            logger.error("Tavily connection error for query '%s': %s", query, exc)
            raise SearchUnavailableError("Failed to connect to Tavily search service.") from exc
