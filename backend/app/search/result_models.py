"""
Pydantic models for search queries, raw Tavily responses, and normalized results.
"""
from typing import Any
import uuid
from pydantic import BaseModel, Field, HttpUrl


class NormalizedSearchResult(BaseModel):
    """Normalized search result used by the agent context and stored in DB."""
    title: str = Field(default="Untitled")
    url: str
    snippet: str = Field(default="")
    score: float = Field(default=0.0)
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class SearchExecutionResult(BaseModel):
    """Container for the full search execution for a given query."""
    query: str
    search_query_id: uuid.UUID | None = None
    results: list[NormalizedSearchResult] = Field(default_factory=list)
    success: bool = True
    error_message: str | None = None
    cached: bool = False
