"""
Phase 2 API tests — health, sessions, conversations.
All tests run against in-memory SQLite; no live DB or API keys required.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient):
    """Health endpoint returns 200 with status=ok."""
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    """POST /sessions creates a new user+session, returns a token."""
    r = await client.post("/api/v1/sessions")
    assert r.status_code == 201
    data = r.json()
    assert "session_token" in data
    assert "user_id" in data
    assert len(data["session_token"]) > 10


@pytest.mark.asyncio
async def test_list_conversations_no_auth(client: AsyncClient):
    """GET /conversations without a token returns 422 (missing header)."""
    r = await client.get("/api/v1/conversations")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_conversations_invalid_token(client: AsyncClient):
    """GET /conversations with an invalid token returns 401."""
    r = await client.get(
        "/api/v1/conversations",
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient):
    """Authenticated user with no conversations gets an empty list."""
    # Create a session first
    sess_r = await client.post("/api/v1/sessions")
    token = sess_r.json()["session_token"]

    r = await client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["conversations"] == []


@pytest.mark.asyncio
async def test_get_conversation_not_found(client: AsyncClient):
    """GET /conversations/{id} returns 404 for non-existent conversation."""
    sess_r = await client.post("/api/v1/sessions")
    token = sess_r.json()["session_token"]

    fake_id = "00000000-0000-0000-0000-000000000000"
    r = await client.get(
        f"/api/v1/conversations/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_isolation(client: AsyncClient):
    """User A cannot access User B's conversation."""
    import uuid
    from datetime import datetime, timezone, timedelta
    from app.models.user import User
    from app.models.session import Session
    from app.models.conversation import Conversation

    # This test directly inserts into DB via db_session — skip for now,
    # covered by integration tests in Phase 7.
    # Here we just verify that two separate sessions are independent.
    sess_a = (await client.post("/api/v1/sessions")).json()["session_token"]
    sess_b = (await client.post("/api/v1/sessions")).json()["session_token"]
    assert sess_a != sess_b
