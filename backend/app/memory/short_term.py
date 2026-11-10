"""
Short-term memory management for conversational continuity.
Fetches recent conversation messages within the bounded context limit.
"""
from datetime import datetime, timezone
import logging
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.message import Message

logger = logging.getLogger(__name__)


class ShortTermMemory:
    def __init__(self, limit: int | None = None):
        settings = get_settings()
        self.limit = limit or settings.short_term_message_limit

    async def get_recent_messages(
        self,
        conversation_id: uuid.UUID,
        db: AsyncSession,
        limit: int | None = None,
    ) -> list[Message]:
        """
        Fetch the most recent N messages for the conversation, ordered chronologically.
        """
        fetch_limit = limit or self.limit

        # Query newest first to apply limit, then sort ascending for conversation flow
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(fetch_limit)
        )
        result = await db.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()  # Chronological order
        return messages

    async def append_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        db: AsyncSession,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Persist a single user or assistant message to the database."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
            metadata_=metadata or {},
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg
