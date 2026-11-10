"""ORM model: Conversation"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, default="New Conversation"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="conversations")  # noqa: F821
    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    memories: Mapped[list["Memory"]] = relationship(  # noqa: F821
        back_populates="conversation", cascade="all, delete-orphan"
    )
    search_queries: Mapped[list["SearchQuery"]] = relationship(  # noqa: F821
        back_populates="conversation", cascade="all, delete-orphan"
    )
