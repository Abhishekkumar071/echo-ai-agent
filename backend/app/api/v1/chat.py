"""
Chat endpoints:
- POST /api/v1/chat: Non-streaming agent turn.
- POST /api/v1/chat/stream: SSE streaming agent turn with live chunks and metadata.
Strictly authenticated via session token header (Change 1).
"""
import logging
from typing import Any
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

orchestrator = AgentOrchestrator()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    content: str
    search_used: bool
    memory_used: bool
    is_then_vs_now: bool
    sources: list[dict[str, Any]]
    memory_references: list[dict[str, Any]]
    latency_ms: int


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Execute a synchronous, non-streaming chat turn with the agent."""
    result = await orchestrator.execute(
        user_message=request.message,
        user_id=current_user.id,
        db=db,
        conversation_id=request.conversation_id,
    )
    return ChatResponse(
        conversation_id=result.conversation_id,
        message_id=result.message_id,
        content=result.response_text,
        search_used=result.search_used,
        memory_used=result.memory_used,
        is_then_vs_now=result.is_then_vs_now,
        sources=result.sources,
        memory_references=result.memory_references,
        latency_ms=result.latency_ms,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream agent response tokens and metadata via Server-Sent Events (SSE)."""
    generator = orchestrator.execute_stream(
        user_message=request.message,
        user_id=current_user.id,
        db=db,
        conversation_id=request.conversation_id,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
