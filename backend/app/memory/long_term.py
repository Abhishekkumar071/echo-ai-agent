"""
Long-term memory management for cross-session knowledge retention.
Stores conversation summaries, key research takeaways, and synthesized findings.
"""
from datetime import datetime, timezone
import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory

logger = logging.getLogger(__name__)


class LongTermMemory:
    async def record_summary(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        summary: str,
        key_findings: str,
        db: AsyncSession,
        embedding: list[float] | None = None,
        topic_tags: list[str] | None = None,
    ) -> Memory:
        """
        Record a distilled cross-session summary.
        Embedding is nullable (Change 2).
        """
        now = datetime.now(timezone.utc)
        memory = Memory(
            user_id=user_id,
            conversation_id=conversation_id,
            memory_type="long_term",
            content=key_findings.strip(),
            summary=summary.strip(),
            embedding=embedding,
            embedding_failed=(embedding is None),
            topic_tags=topic_tags or [],
            created_at=now,
            updated_at=now,
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory

    async def get_recent_summaries(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 5,
    ) -> list[Memory]:
        """Fetch the latest cross-session summaries for the user."""
        stmt = (
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.memory_type == "long_term",
            )
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
