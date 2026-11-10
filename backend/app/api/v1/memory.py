"""
Memory API endpoints.
Provides semantic memory search and chronological memory timeline.
Scoped strictly to authenticated user via session (Change 1).
"""
from datetime import datetime
import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.memory.retriever import HybridMemoryRetriever, ScoredMemory
from app.memory.temporal import TemporalMemory
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])

retriever = HybridMemoryRetriever()
temporal_memory = TemporalMemory()


class MemorySearchResponse(BaseModel):
    query: str
    results: list[ScoredMemory]


class TimelineEntry(BaseModel):
    id: str
    original_query: str | None
    content: str
    summary: str | None
    created_at: datetime
    topic_tags: list[str] | None = None
    conversation_id: str | None = None


class TimelineResponse(BaseModel):
    entries: list[TimelineEntry]


@router.get("/search", response_model=MemorySearchResponse)
async def search_memory(
    q: str = Query(..., description="Query to search memory for"),
    top_k: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemorySearchResponse:
    """
    Search past memories and conversations using hybrid semantic + recency ranking.
    """
    result = await retriever.retrieve(
        user_id=current_user.id,
        query=q,
        db=db,
        top_k=top_k,
    )
    return MemorySearchResponse(
        query=q,
        results=result.relevant_memories,
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    from_date: datetime | None = Query(None, description="Start date (ISO8601 UTC)"),
    to_date: datetime | None = Query(None, description="End date (ISO8601 UTC)"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    """
    Retrieve chronological memory records for the user.
    """
    memories = await temporal_memory.get_by_timerange(
        user_id=current_user.id,
        db=db,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )
    return TimelineResponse(
        entries=[
            TimelineEntry(
                id=str(m.id),
                original_query=m.original_query,
                content=m.content,
                summary=m.summary,
                created_at=m.created_at,
                topic_tags=m.topic_tags,
                conversation_id=str(m.conversation_id) if m.conversation_id else None,
            )
            for m in memories
        ]
    )
