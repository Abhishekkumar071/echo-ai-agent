"""
Unit tests for the Memory Engine (Short-term, Long-term, Temporal, Hybrid Retriever, and API).
Runs in-memory with SQLite and mocked embeddings.
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient

from app.memory.long_term import LongTermMemory
from app.memory.retriever import HybridMemoryRetriever, compute_recency_score
from app.memory.short_term import ShortTermMemory
from app.memory.temporal import TemporalMemory, extract_temporal_range
from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.session import Session
from app.models.user import User
from app.services.embedding_service import EmbeddingService


def test_recency_score_decay():
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    score_now = compute_recency_score(now, now=now)
    score_1d = compute_recency_score(one_day_ago, now=now)
    score_7d = compute_recency_score(seven_days_ago, now=now)
    score_30d = compute_recency_score(thirty_days_ago, now=now)

    assert 0.99 <= score_now <= 1.0
    assert 0.8 < score_1d < 1.0
    # Half-life is 7 days, so score_7d should be ~0.5
    assert 0.45 <= score_7d <= 0.55
    assert score_30d < 0.1


def test_extract_temporal_range():
    now = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)

    # Yesterday
    start, end = extract_temporal_range("What did we talk about yesterday?", now=now)
    assert start is not None and end is not None
    assert start.day == 9
    assert end.day == 10

    # Last week
    start, end = extract_temporal_range("What frameworks did we research last week?", now=now)
    assert start is not None
    assert (now - start).days == 7

    # 3 days ago
    start, end = extract_temporal_range("What did I ask 3 days ago?", now=now)
    assert start is not None
    assert start.day == 7


@pytest.mark.asyncio
async def test_short_term_memory(db_session):
    user = User()
    db_session.add(user)
    await db_session.flush()

    conv = Conversation(user_id=user.id, title="Short Term Test")
    db_session.add(conv)
    await db_session.commit()

    stm = ShortTermMemory(limit=2)
    await stm.append_message(conv.id, "user", "Message 1", db_session)
    await stm.append_message(conv.id, "assistant", "Response 1", db_session)
    await stm.append_message(conv.id, "user", "Message 2", db_session)

    # Should fetch only the last 2 in chronological order
    recent = await stm.get_recent_messages(conv.id, db_session, limit=2)
    assert len(recent) == 2
    assert recent[0].content == "Response 1"
    assert recent[1].content == "Message 2"


@pytest.mark.asyncio
async def test_temporal_memory_preservation(db_session):
    """Verify that temporal memory saves original query and exact timestamps without requiring embeddings (Change 2)."""
    user = User()
    db_session.add(user)
    await db_session.flush()

    conv = Conversation(user_id=user.id, title="Temporal Test")
    db_session.add(conv)
    await db_session.commit()

    tm = TemporalMemory()
    mem = await tm.record_temporal_memory(
        user_id=user.id,
        conversation_id=conv.id,
        original_query="What are the best backend frameworks for scalable applications?",
        db=db_session,
        summary="Researched backend frameworks",
        topic_tags=["backend", "scalability"],
        embedding=None,  # Nullable embedding
    )

    assert mem.id is not None
    assert mem.original_query == "What are the best backend frameworks for scalable applications?"
    assert mem.content == "What are the best backend frameworks for scalable applications?"
    assert mem.embedding is None
    assert mem.embedding_failed is True
    assert mem.created_at is not None

    # Retrieve by timerange
    found = await tm.get_by_timerange(user_id=user.id, db=db_session)
    assert len(found) >= 1
    assert found[0].original_query == mem.original_query


@pytest.mark.asyncio
async def test_hybrid_retriever_user_isolation(db_session):
    """Verify that user A cannot retrieve user B's memories (Change 1)."""
    user_a = User()
    user_b = User()
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    # User A creates a memory
    mem_a = Memory(
        user_id=user_a.id,
        memory_type="temporal",
        content="User A's secret project notes",
        original_query="User A's secret project notes",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    # User B creates a memory
    mem_b = Memory(
        user_id=user_b.id,
        memory_type="temporal",
        content="User B's public research notes",
        original_query="User B's public research notes",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add_all([mem_a, mem_b])
    await db_session.commit()

    retriever = HybridMemoryRetriever()

    # Query as User A
    res_a = await retriever.retrieve(user_id=user_a.id, query="secret notes", db=db_session)
    assert any(m.content == "User A's secret project notes" for m in res_a.relevant_memories)
    assert not any(m.content == "User B's public research notes" for m in res_a.relevant_memories)

    # Query as User B
    res_b = await retriever.retrieve(user_id=user_b.id, query="secret notes", db=db_session)
    assert not any(m.content == "User A's secret project notes" for m in res_b.relevant_memories)


@pytest.mark.asyncio
async def test_memory_api_endpoints(client: AsyncClient):
    """Test /api/v1/memory/search and /api/v1/memory/timeline endpoints."""
    # 1. Create a session to get valid token
    sess_res = await client.post("/api/v1/sessions")
    token = sess_res.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Timeline initially empty
    timeline_res = await client.get("/api/v1/memory/timeline", headers=headers)
    assert timeline_res.status_code == 200
    assert timeline_res.json()["entries"] == []

    # 3. Search endpoint
    search_res = await client.get("/api/v1/memory/search?q=test", headers=headers)
    assert search_res.status_code == 200
    assert "results" in search_res.json()
