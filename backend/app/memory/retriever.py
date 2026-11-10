"""
Hybrid memory retriever.
Combines semantic search (pgvector cosine), recency decay, and temporal filtering.
Gracefully falls back to text/date search if embeddings are unavailable (Change 2).
Strictly scopes all queries to user_id (Change 1).
"""
from datetime import datetime, timezone
import logging
import math
from typing import Any
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.memory.temporal import extract_temporal_range
from app.models.memory import Memory
from app.models.message import Message
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Recency decay half-life: 7 days (in seconds)
HALF_LIFE_SECONDS = 7 * 24 * 3600
LAMBDA_DECAY = math.log(2) / HALF_LIFE_SECONDS


class ScoredMemory(BaseModel):
    id: uuid.UUID
    content: str
    summary: str | None = None
    original_query: str | None = None
    memory_type: str
    created_at: datetime
    conversation_id: uuid.UUID | None = None
    similarity_score: float = 0.0
    recency_score: float = 0.0
    combined_score: float = 0.0


class MemoryRetrievalResult(BaseModel):
    short_term_messages: list[dict[str, Any]] = Field(default_factory=list)
    relevant_memories: list[ScoredMemory] = Field(default_factory=list)
    temporal_filter_applied: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None


def compute_recency_score(created_at: datetime, now: datetime | None = None) -> float:
    """Compute exponential decay score between 0.0 and 1.0 based on elapsed time."""
    ref = now or datetime.now(timezone.utc)
    # Ensure timezone aware
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    delta_seconds = max(0.0, (ref - created_at).total_seconds())
    return math.exp(-LAMBDA_DECAY * delta_seconds)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class HybridMemoryRetriever:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        short_term: ShortTermMemory | None = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.short_term = short_term or ShortTermMemory()

    async def retrieve(
        self,
        user_id: uuid.UUID,
        query: str,
        db: AsyncSession,
        conversation_id: uuid.UUID | None = None,
        top_k: int = 5,
    ) -> MemoryRetrievalResult:
        """
        Execute hybrid retrieval across all memory layers for the user.
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch short-term context if conversation_id provided
        recent_msgs: list[dict[str, Any]] = []
        if conversation_id:
            db_msgs = await self.short_term.get_recent_messages(conversation_id, db)
            recent_msgs = [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in db_msgs
            ]

        # 2. Check for natural language temporal filter
        start_time, end_time = extract_temporal_range(query, now=now)
        has_temporal = start_time is not None

        # 3. Base query: always scoped to user_id (Change 1)
        stmt = select(Memory).where(Memory.user_id == user_id)

        # Apply temporal boundaries if present
        if start_time:
            stmt = stmt.where(Memory.created_at >= start_time)
        if end_time:
            stmt = stmt.where(Memory.created_at <= end_time)

        # 4. Generate query embedding if possible
        query_embedding = await self.embedding_service.generate_embedding(query)

        # 5. Fetch candidate memory rows
        # If no temporal filter, fetch candidate rows by keyword or top recency
        if not has_temporal and query.strip():
            terms = [f"%{t}%" for t in query.strip().split() if len(t) > 2]
            if terms:
                text_filters = [
                    or_(
                        Memory.content.ilike(term),
                        Memory.summary.ilike(term),
                        Memory.original_query.ilike(term),
                    )
                    for term in terms[:3]
                ]
                # Combine with general recency candidates
                stmt = stmt.where(or_(*text_filters, Memory.embedding.is_not(None)))

        stmt = stmt.order_by(Memory.created_at.desc()).limit(50)
        candidates_res = await db.execute(stmt)
        candidates = list(candidates_res.scalars().all())

        if not candidates:
            # Fallback: get newest 10 memories for the user
            fallback_stmt = (
                select(Memory)
                .where(Memory.user_id == user_id)
                .order_by(Memory.created_at.desc())
                .limit(10)
            )
            fallback_res = await db.execute(fallback_stmt)
            candidates = list(fallback_res.scalars().all())

        # 6. Rank candidates
        scored_list: list[ScoredMemory] = []
        for mem in candidates:
            recency = compute_recency_score(mem.created_at, now=now)
            similarity = 0.0

            # Calculate semantic similarity if vector is available
            if query_embedding and mem.embedding is not None:
                try:
                    # In pgvector / python, embedding is a list/array
                    mem_vec = list(mem.embedding)
                    similarity = cosine_similarity(query_embedding, mem_vec)
                except Exception:
                    similarity = 0.0
            else:
                # Text-overlap heuristic fallback when embeddings are absent
                q_words = set(query.lower().split())
                content_words = set((mem.content + " " + (mem.original_query or "")).lower().split())
                overlap = len(q_words.intersection(content_words))
                similarity = min(1.0, overlap / max(1, len(q_words)))

            # If temporal query matched exact time window, boost score
            if has_temporal:
                combined = 0.7 * recency + 0.3 * similarity
            else:
                combined = 0.6 * similarity + 0.4 * recency

            scored_list.append(
                ScoredMemory(
                    id=mem.id,
                    content=mem.content,
                    summary=mem.summary,
                    original_query=mem.original_query,
                    memory_type=mem.memory_type,
                    created_at=mem.created_at,
                    conversation_id=mem.conversation_id,
                    similarity_score=round(similarity, 3),
                    recency_score=round(recency, 3),
                    combined_score=round(combined, 3),
                )
            )

        # Sort by combined score descending
        scored_list.sort(key=lambda x: x.combined_score, reverse=True)
        top_memories = scored_list[:top_k]

        return MemoryRetrievalResult(
            short_term_messages=recent_msgs,
            relevant_memories=top_memories,
            temporal_filter_applied=has_temporal,
            start_time=start_time,
            end_time=end_time,
        )
