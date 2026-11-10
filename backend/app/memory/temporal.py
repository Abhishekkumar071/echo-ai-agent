"""
Temporal memory layer.
Stores exact original questions with UTC timestamps and topic tags.
Answers questions like 'What did I ask yesterday?' or 'When did I discuss Spring Boot?'.
"""
from datetime import datetime, timedelta, timezone
import logging
import re
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory

logger = logging.getLogger(__name__)


def extract_temporal_range(query: str, now: datetime | None = None) -> tuple[datetime | None, datetime | None]:
    """
    Heuristically parse natural language temporal expressions from user query.
    Returns (start_time, end_time) in UTC, or (None, None) if no temporal filter matches.
    """
    ref_time = now or datetime.now(timezone.utc)
    q_lower = query.lower()

    # Yesterday
    if "yesterday" in q_lower:
        start = (ref_time - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return (start, end)

    # Today / earlier today
    if "today" in q_lower or "earlier" in q_lower:
        start = ref_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return (start, ref_time)

    # Last week
    if "last week" in q_lower or "past week" in q_lower:
        start = ref_time - timedelta(days=7)
        return (start, ref_time)

    # Last month
    if "last month" in q_lower or "past month" in q_lower:
        start = ref_time - timedelta(days=30)
        return (start, ref_time)

    # Days ago: e.g. "2 days ago", "3 days ago"
    match = re.search(r"(\d+)\s+days?\s+ago", q_lower)
    if match:
        days = int(match.group(1))
        start = (ref_time - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return (start, end)

    return (None, None)


class TemporalMemory:
    async def record_temporal_memory(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        original_query: str,
        db: AsyncSession,
        summary: str | None = None,
        topic_tags: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> Memory:
        """
        Record verbatim user question with exact UTC timestamp and optional tags.
        ★ Change 2: Saves immediately; embedding is nullable.
        """
        now = datetime.now(timezone.utc)
        memory = Memory(
            user_id=user_id,
            conversation_id=conversation_id,
            memory_type="temporal",
            content=original_query.strip(),
            original_query=original_query.strip(),
            summary=summary,
            topic_tags=topic_tags or [],
            embedding=embedding,
            embedding_failed=(embedding is None),
            created_at=now,
            updated_at=now,
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory

    async def get_by_timerange(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        """
        Retrieve chronological memories within a specified UTC timestamp window.
        """
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
        )

        if from_date:
            stmt = stmt.where(Memory.created_at >= from_date)
        if to_date:
            stmt = stmt.where(Memory.created_at <= to_date)

        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())
