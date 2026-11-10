"""
Search service responsible for executing, normalizing, deduplicating,
and persisting web search queries and results.
"""
from datetime import datetime, timezone
import logging
from urllib.parse import urlparse, urlunparse
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import SearchUnavailableError
from app.models.search import SearchQuery, SearchResult
from app.search.result_models import NormalizedSearchResult, SearchExecutionResult
from app.search.tavily_client import TavilyClient

logger = logging.getLogger(__name__)


def clean_url(url: str) -> str:
    """Normalize URL by stripping fragments and trailing slashes for deduplication."""
    try:
        parsed = urlparse(url.strip())
        path = parsed.path.rstrip("/")
        # Reconstruct without fragment
        clean = urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, ""))
        return clean or url.strip()
    except Exception:
        return url.strip()


def sanitize_text(text: str | None) -> str:
    """Clean whitespace and strip potentially dangerous control characters/injection delimiters."""
    if not text:
        return ""
    cleaned = " ".join(text.split())
    # Guard against prompt injection delimiters commonly used in jailbreaks
    cleaned = cleaned.replace("<|im_start|>", "").replace("<|im_end|>", "")
    return cleaned


class SearchService:
    def __init__(self, tavily_client: TavilyClient | None = None):
        self.client = tavily_client or TavilyClient()
        self.settings = get_settings()

    def normalize_results(self, raw_results: list[dict]) -> list[NormalizedSearchResult]:
        """
        Normalize raw Tavily result dicts:
        - Deduplicate by URL
        - Clean snippet and title
        - Extract score and source metadata
        """
        seen_urls = set()
        normalized: list[NormalizedSearchResult] = []

        for item in raw_results:
            raw_url = item.get("url", "")
            if not raw_url:
                continue

            normalized_url = clean_url(raw_url)
            if normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)

            title = sanitize_text(item.get("title") or "Source")
            snippet = sanitize_text(item.get("content") or item.get("snippet") or "")
            score = float(item.get("score") or 0.0)

            # Preserve source metadata (domain, published date if present)
            domain = urlparse(normalized_url).netloc
            metadata = {
                "domain": domain,
                "raw_score": score,
            }
            if "published_date" in item:
                metadata["published_date"] = item["published_date"]

            normalized.append(
                NormalizedSearchResult(
                    title=title,
                    url=normalized_url,
                    snippet=snippet,
                    score=score,
                    source_metadata=metadata,
                )
            )

        return normalized

    async def execute_and_persist(
        self,
        query: str,
        conversation_id: uuid.UUID,
        db: AsyncSession,
        message_id: uuid.UUID | None = None,
        max_results: int | None = None,
    ) -> SearchExecutionResult:
        """
        Execute web search via Tavily, normalize results, and persist to database.
        If search fails or times out, returns SearchExecutionResult with success=False
        and does NOT raise an unhandled exception, ensuring graceful degradation.
        """
        max_res = max_results or self.settings.tavily_max_results

        # 1. Record search query in DB
        search_query_record = SearchQuery(
            conversation_id=conversation_id,
            message_id=message_id,
            query=query.strip(),
            created_at=datetime.now(timezone.utc),
        )
        db.add(search_query_record)
        await db.flush()

        # 2. Call Tavily
        try:
            raw_results = await self.client.search(query=query, max_results=max_res)
        except SearchUnavailableError as exc:
            logger.warning("Search failed gracefully for query '%s': %s", query, exc)
            return SearchExecutionResult(
                query=query,
                search_query_id=search_query_record.id,
                results=[],
                success=False,
                error_message=str(exc),
            )
        except Exception as exc:
            logger.error("Unexpected search error for query '%s': %s", query, exc, exc_info=True)
            return SearchExecutionResult(
                query=query,
                search_query_id=search_query_record.id,
                results=[],
                success=False,
                error_message="Unexpected error during web search.",
            )

        # 3. Normalize & Deduplicate
        normalized = self.normalize_results(raw_results)

        # 4. Persist search results in DB
        db_results = [
            SearchResult(
                search_query_id=search_query_record.id,
                title=res.title,
                url=res.url,
                snippet=res.snippet,
                score=res.score,
                source_metadata=res.source_metadata,
            )
            for res in normalized
        ]
        db.add_all(db_results)
        await db.commit()

        logger.info(
            "Persisted %d search results for query '%s' in conversation %s",
            len(normalized),
            query,
            conversation_id,
        )

        return SearchExecutionResult(
            query=query,
            search_query_id=search_query_record.id,
            results=normalized,
            success=True,
        )
