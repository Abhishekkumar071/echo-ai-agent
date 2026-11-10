"""
Agent Orchestrator.
Coordinates Intent Analysis, Memory Retrieval, Web Search, Context Assembly,
LLM Generation, and Memory Persistence across the full agent lifecycle.
"""
import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import json
import logging
import time
import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context_assembler import ContextAssembler
from app.agents.intent import IntentAnalyzer
from app.core.config import get_settings
from app.memory.long_term import LongTermMemory
from app.memory.retriever import HybridMemoryRetriever
from app.memory.short_term import ShortTermMemory
from app.memory.temporal import TemporalMemory
from app.models.conversation import Conversation
from app.models.message import Message
from app.search.result_models import NormalizedSearchResult
from app.search.search_service import SearchService
from app.services.embedding_service import EmbeddingService
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class AgentTurnResult(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    response_text: str
    search_used: bool = False
    memory_used: bool = False
    is_then_vs_now: bool = False
    sources: list[dict[str, Any]] = Field(default_factory=list)
    memory_references: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int = 0


class AgentOrchestrator:
    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        search_service: SearchService | None = None,
        retriever: HybridMemoryRetriever | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        self.llm = llm_provider or LLMProvider()
        self.search_service = search_service or SearchService()
        self.embedding_service = embedding_service or EmbeddingService()
        self.retriever = retriever or HybridMemoryRetriever(embedding_service=self.embedding_service)
        self.intent_analyzer = IntentAnalyzer(llm_provider=self.llm)
        self.context_assembler = ContextAssembler()
        self.short_term = ShortTermMemory()
        self.temporal_memory = TemporalMemory()
        self.long_term = LongTermMemory()
        self.settings = get_settings()

    async def _ensure_conversation(
        self,
        conversation_id: uuid.UUID | None,
        user_id: uuid.UUID,
        user_message: str,
        db: AsyncSession,
    ) -> Conversation:
        """Ensure conversation exists and belongs to user (Change 1)."""
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv

        # Generate a concise title from the user query
        words = user_message.strip().split()
        title = " ".join(words[:6]) if words else "New Conversation"
        new_conv = Conversation(
            user_id=user_id,
            title=title[:80],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_conv)
        await db.flush()
        return new_conv

    async def _persist_memory_async(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_message: str,
        assistant_response: str,
        db: AsyncSession,
    ) -> None:
        """
        Persist temporal memory record and generate embeddings asynchronously (Change 2).
        If embedding generation fails, embedding is None, embedding_failed=True, and row is safely kept.
        """
        try:
            # Generate embedding in background
            embedding = await self.embedding_service.generate_embedding(user_message)

            # Record verbatim question in temporal memory
            await self.temporal_memory.record_temporal_memory(
                user_id=user_id,
                conversation_id=conversation_id,
                original_query=user_message,
                db=db,
                summary=assistant_response[:300],
                embedding=embedding,
            )
        except Exception as exc:
            logger.error("Failed to asynchronously persist memory: %s", exc, exc_info=True)

    async def execute(
        self,
        user_message: str,
        user_id: uuid.UUID,
        db: AsyncSession,
        conversation_id: uuid.UUID | None = None,
    ) -> AgentTurnResult:
        """Execute a full non-streaming turn of the agent."""
        start_time = time.time()

        # 1. Ensure conversation
        conv = await self._ensure_conversation(conversation_id, user_id, user_message, db)

        # 2. Persist user message immediately to DB (source of truth)
        user_msg_record = await self.short_term.append_message(
            conversation_id=conv.id,
            role="user",
            content=user_message,
            db=db,
        )

        # 3. Retrieve short-term memory & classify intent
        recent_messages = await self.short_term.get_recent_messages(conv.id, db)
        recent_dicts = [{"role": m.role, "content": m.content} for m in recent_messages[:-1]]

        intent = await self.intent_analyzer.analyze(user_message, recent_messages=recent_dicts)

        # 4. Memory retrieval
        memory_result = await self.retriever.retrieve(
            user_id=user_id,
            query=intent.memory_query or user_message,
            db=db,
            conversation_id=conv.id,
            top_k=5,
        )

        # 5. Web Search (if needed)
        search_results: list[NormalizedSearchResult] = []
        search_error: str | None = None
        if intent.needs_search:
            search_query = intent.search_query or user_message
            exec_result = await self.search_service.execute_and_persist(
                query=search_query,
                conversation_id=conv.id,
                message_id=user_msg_record.id,
                db=db,
            )
            if exec_result.success:
                search_results = exec_result.results
            else:
                search_error = exec_result.error_message

        # 6. Assemble context
        assembled = self.context_assembler.assemble(
            user_message=user_message,
            recent_messages=recent_dicts,
            memories=memory_result.relevant_memories,
            search_results=search_results,
            is_then_vs_now=intent.is_then_vs_now,
            search_error=search_error,
        )

        # 7. LLM Generation
        response_text = await self.llm.generate_text(
            messages=assembled.messages,
            model=self.settings.groq_generation_model,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # 8. Persist assistant message with metadata
        metadata = {
            "search_used": intent.needs_search,
            "memory_used": bool(memory_result.relevant_memories),
            "is_then_vs_now": intent.is_then_vs_now,
            "sources": assembled.sources_used,
            "latency_ms": latency_ms,
        }
        asst_msg_record = await self.short_term.append_message(
            conversation_id=conv.id,
            role="assistant",
            content=response_text,
            db=db,
            metadata=metadata,
        )

        # 9. Asynchronously persist memory
        asyncio.create_task(
            self._persist_memory_async(
                user_id=user_id,
                conversation_id=conv.id,
                user_message=user_message,
                assistant_response=response_text,
                db=db,
            )
        )

        return AgentTurnResult(
            conversation_id=conv.id,
            message_id=asst_msg_record.id,
            response_text=response_text,
            search_used=intent.needs_search,
            memory_used=bool(memory_result.relevant_memories),
            is_then_vs_now=intent.is_then_vs_now,
            sources=assembled.sources_used,
            memory_references=assembled.memories_used,
            latency_ms=latency_ms,
        )

    async def execute_stream(
        self,
        user_message: str,
        user_id: uuid.UUID,
        db: AsyncSession,
        conversation_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Execute streaming agent turn, yielding standard Server-Sent Events (SSE).
        Events:
        - event: metadata  data: {"sources": [...], "memory_references": [...], "search_used": bool}
        - event: chunk     data: {"text": "..."}
        - event: done      data: {"message_id": "...", "latency_ms": 1234}
        - event: error     data: {"code": "...", "message": "..."}
        """
        start_time = time.time()

        # 1. Ensure conversation & save user message
        conv = await self._ensure_conversation(conversation_id, user_id, user_message, db)
        user_msg = await self.short_term.append_message(
            conversation_id=conv.id,
            role="user",
            content=user_message,
            db=db,
        )

        # 2. Short-term history & intent classification
        recent = await self.short_term.get_recent_messages(conv.id, db)
        recent_dicts = [{"role": m.role, "content": m.content} for m in recent[:-1]]
        intent = await self.intent_analyzer.analyze(user_message, recent_messages=recent_dicts)

        # 3. Retrieve memories
        memory_result = await self.retriever.retrieve(
            user_id=user_id,
            query=intent.memory_query or user_message,
            db=db,
            conversation_id=conv.id,
            top_k=5,
        )

        # 4. Web search if required
        search_results: list[NormalizedSearchResult] = []
        search_error: str | None = None
        if intent.needs_search:
            search_query = intent.search_query or user_message
            exec_result = await self.search_service.execute_and_persist(
                query=search_query,
                conversation_id=conv.id,
                message_id=user_msg.id,
                db=db,
            )
            if exec_result.success:
                search_results = exec_result.results
            else:
                search_error = exec_result.error_message
                yield f"event: error\ndata: {json.dumps({'code': 'SEARCH_UNAVAILABLE', 'message': search_error})}\n\n"

        # 5. Assemble context
        assembled = self.context_assembler.assemble(
            user_message=user_message,
            recent_messages=recent_dicts,
            memories=memory_result.relevant_memories,
            search_results=search_results,
            is_then_vs_now=intent.is_then_vs_now,
            search_error=search_error,
        )

        # Emit metadata event first so frontend can display sources/context immediately
        meta_payload = {
            "conversation_id": str(conv.id),
            "search_used": intent.needs_search,
            "memory_used": bool(memory_result.relevant_memories),
            "is_then_vs_now": intent.is_then_vs_now,
            "sources": assembled.sources_used,
            "memory_references": assembled.memories_used,
        }
        yield f"event: metadata\ndata: {json.dumps(meta_payload)}\n\n"

        # 6. Stream tokens
        full_text_chunks: list[str] = []
        try:
            async for token in self.llm.stream_text(assembled.messages):
                full_text_chunks.append(token)
                yield f"event: chunk\ndata: {json.dumps({'text': token})}\n\n"
        except Exception as exc:
            logger.error("Streaming error: %s", exc)
            yield f"event: error\ndata: {json.dumps({'code': 'LLM_ERROR', 'message': str(exc)})}\n\n"
            return

        full_response = "".join(full_text_chunks)
        latency_ms = int((time.time() - start_time) * 1000)

        # 7. Persist assistant message
        asst_msg = await self.short_term.append_message(
            conversation_id=conv.id,
            role="assistant",
            content=full_response,
            db=db,
            metadata={
                "search_used": intent.needs_search,
                "memory_used": bool(memory_result.relevant_memories),
                "is_then_vs_now": intent.is_then_vs_now,
                "sources": assembled.sources_used,
                "latency_ms": latency_ms,
            },
        )

        # 8. Asynchronously persist memory
        asyncio.create_task(
            self._persist_memory_async(
                user_id=user_id,
                conversation_id=conv.id,
                user_message=user_message,
                assistant_response=full_response,
                db=db,
            )
        )

        # Done event
        done_payload = {
            "message_id": str(asst_msg.id),
            "conversation_id": str(conv.id),
            "latency_ms": latency_ms,
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
