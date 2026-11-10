"""
ORM model: Memory
★ Change 2 — Reliable Memory

embedding is NULLABLE. The row is committed immediately with content + exact
created_at. Embedding is applied asynchronously. If embedding fails,
embedding_failed=True is set so the retriever can skip retry and fall back
to date/text retrieval.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from app.database.base import Base

# pgvector type — imported lazily to avoid hard failure if extension absent
try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_TYPE = Vector(768)
except ImportError:
    # During initial migration generation without pgvector installed, use Text
    _VECTOR_TYPE = Text  # type: ignore[assignment]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    memory_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # short_term | long_term | temporal

    # Content — always populated, never null
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Embedding — nullable; never blocks memory save
    embedding: Mapped[Any | None] = mapped_column(_VECTOR_TYPE, nullable=True)
    embedding_failed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Temporal fields — always populated for temporal memories; enables date-only retrieval
    original_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    related_conv_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="memories")  # noqa: F821
    conversation: Mapped["Conversation | None"] = relationship(  # noqa: F821
        back_populates="memories"
    )
