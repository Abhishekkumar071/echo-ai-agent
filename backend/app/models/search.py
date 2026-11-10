"""
ORM models: SearchQuery and SearchResult
★ Change 3 — Reliable Search & Citations

LLM context is built from SearchResult rows, not raw API text.
URLs in the UI are always fetched from this table.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from app.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(  # noqa: F821
        back_populates="search_queries"
    )
    results: Mapped[list["SearchResult"]] = relationship(
        back_populates="search_query", cascade="all, delete-orphan"
    )


class SearchResult(Base):
    __tablename__ = "search_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    search_query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("search_queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    search_query: Mapped["SearchQuery"] = relationship(back_populates="results")
