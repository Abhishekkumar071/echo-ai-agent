"""
ORM model: User
One row per anonymous identity. Created automatically on first session creation.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # relationships
    sessions: Mapped[list["Session"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    memories: Mapped[list["Memory"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
