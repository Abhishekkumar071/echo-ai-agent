"""
Conversation endpoints.

All queries are scoped to current_user.id — users can only see their own data.
"""
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.exceptions import http_404
from app.database.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])


# ── Response schemas ──────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    metadata: dict

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """Return all conversations for the authenticated user, newest first."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ]
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    """Return a conversation with all its messages. 404 if not owned by user."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,  # ownership check
        )
        .options(selectinload(Conversation.messages))
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise http_404(f"Conversation {conversation_id} not found")

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                metadata=m.metadata_,
            )
            for m in conv.messages
        ],
    )
