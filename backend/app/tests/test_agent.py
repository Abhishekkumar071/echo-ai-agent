"""
Unit and integration tests for the Agent Orchestration pipeline.
Uses mocked LLM and Search clients running against in-memory SQLite.
"""
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import uuid
import pytest
from httpx import AsyncClient

from app.agents.context_assembler import ContextAssembler
from app.agents.intent import IntentAnalyzer, IntentClassification
from app.agents.orchestrator import AgentOrchestrator
from app.memory.retriever import ScoredMemory
from app.models.conversation import Conversation
from app.models.user import User
from app.search.result_models import NormalizedSearchResult, SearchExecutionResult


class MockLLMProvider:
    """Mock LLM Provider that returns deterministic text and structured JSON."""
    def __init__(self, response_text: str = "This is a mocked answer."):
        self.response_text = response_text

    async def generate_text(self, messages, model=None, temperature=0.7, max_tokens=2048):
        return self.response_text

    async def stream_text(self, messages, model=None, temperature=0.7, max_tokens=2048) -> AsyncGenerator[str, None]:
        for token in ["This ", "is ", "a ", "streamed ", "mocked ", "answer."]:
            yield token

    async def generate_json(self, messages, model=None, temperature=0.1):
        return {
            "needs_search": True,
            "needs_memory": False,
            "is_then_vs_now": False,
            "search_query": "mock search query",
            "memory_query": None,
            "reasoning": "Mocked intent",
        }


class MockSearchService:
    """Mock search service returning deterministic DB-grounded search results."""
    async def execute_and_persist(self, query, conversation_id, db, message_id=None, max_results=None):
        return SearchExecutionResult(
            query=query,
            search_query_id=uuid.uuid4(),
            results=[
                NormalizedSearchResult(
                    title="Mock Search Result",
                    url="https://example.com/mock-article",
                    snippet="Detailed mock content about the topic.",
                    score=0.99,
                    source_metadata={"domain": "example.com"},
                )
            ],
            success=True,
        )


def test_context_assembler_with_memories_and_sources():
    assembler = ContextAssembler()
    memories = [
        ScoredMemory(
            id=uuid.uuid4(),
            content="Discussed FastAPI vs Django",
            original_query="What are the best frameworks?",
            memory_type="temporal",
            created_at=datetime(2026, 11, 9, 14, 0, 0, tzinfo=timezone.utc),
            similarity_score=0.95,
        )
    ]
    sources = [
        NormalizedSearchResult(
            title="FastAPI Official",
            url="https://fastapi.tiangolo.com",
            snippet="High performance, easy to learn.",
            score=0.9,
        )
    ]

    ctx = assembler.assemble(
        user_message="Has anything changed since yesterday?",
        recent_messages=[],
        memories=memories,
        search_results=sources,
        is_then_vs_now=True,
    )

    assert len(ctx.sources_used) == 1
    assert ctx.sources_used[0]["url"] == "https://fastapi.tiangolo.com"
    assert len(ctx.memories_used) == 1
    assert "Discussed FastAPI vs Django" in ctx.system_prompt
    assert "https://fastapi.tiangolo.com" in ctx.system_prompt
    assert "THEN VS NOW" in ctx.system_prompt


@pytest.mark.asyncio
async def test_intent_analyzer_heuristics():
    analyzer = IntentAnalyzer(llm_provider=MockLLMProvider())

    # Pure historical recall
    intent_mem = await analyzer.analyze("What did I ask yesterday?")
    assert intent_mem.needs_memory is True
    assert intent_mem.needs_search is False

    # Then vs Now
    intent_tvn = await analyzer.analyze("Has anything changed since then?")
    assert intent_tvn.is_then_vs_now is True
    assert intent_tvn.needs_search is True
    assert intent_tvn.needs_memory is True


@pytest.mark.asyncio
async def test_orchestrator_execute(db_session):
    user = User()
    db_session.add(user)
    await db_session.flush()

    orchestrator = AgentOrchestrator(
        llm_provider=MockLLMProvider("Grounded test response."),
        search_service=MockSearchService(),
    )

    result = await orchestrator.execute(
        user_message="Tell me about scalable backend architectures",
        user_id=user.id,
        db=db_session,
    )

    assert result.conversation_id is not None
    assert result.message_id is not None
    assert result.response_text == "Grounded test response."
    assert len(result.sources) == 1
    assert result.sources[0]["url"] == "https://example.com/mock-article"


@pytest.mark.asyncio
async def test_orchestrator_execute_stream(db_session):
    user = User()
    db_session.add(user)
    await db_session.flush()

    orchestrator = AgentOrchestrator(
        llm_provider=MockLLMProvider(),
        search_service=MockSearchService(),
    )

    events: list[str] = []
    async for event in orchestrator.execute_stream(
        user_message="Stream test message",
        user_id=user.id,
        db=db_session,
    ):
        events.append(event)

    assert any(e.startswith("event: metadata") for e in events)
    assert any(e.startswith("event: chunk") for e in events)
    assert any(e.startswith("event: done") for e in events)


@pytest.mark.asyncio
async def test_chat_api_endpoints(client: AsyncClient, monkeypatch):
    """Test POST /api/v1/chat and POST /api/v1/chat/stream endpoints."""
    # Patch orchestrator in chat router with mocked version
    from app.api.v1 import chat
    mock_orch = AgentOrchestrator(
        llm_provider=MockLLMProvider("API test answer"),
        search_service=MockSearchService(),
    )
    monkeypatch.setattr(chat, "orchestrator", mock_orch)

    # 1. Unauthenticated request should fail with 422
    r_unauth = await client.post("/api/v1/chat", json={"message": "hello"})
    assert r_unauth.status_code == 422

    # 2. Create valid session
    sess_r = await client.post("/api/v1/sessions")
    token = sess_r.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Authenticated unary chat
    r_chat = await client.post(
        "/api/v1/chat",
        json={"message": "What is FastAPI?"},
        headers=headers,
    )
    assert r_chat.status_code == 200
    data = r_chat.json()
    assert data["content"] == "API test answer"
    assert "sources" in data
    assert "conversation_id" in data

    # 4. Authenticated streaming chat
    r_stream = await client.post(
        "/api/v1/chat/stream",
        json={"message": "Stream this test"},
        headers=headers,
    )
    assert r_stream.status_code == 200
    assert "text/event-stream" in r_stream.headers["content-type"]
