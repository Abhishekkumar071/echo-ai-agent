"""
FastAPI dependency injection.

get_current_user() is the single gate for user identity.
It resolves user_id from the session token — NEVER from the request body.
Every route that needs the user identity uses: Depends(get_current_user).
"""
import logging
from datetime import datetime, timezone

from fastapi import Depends, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import http_401
from app.database.session import get_db
from app.models.session import Session
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: str = Header(..., description="Bearer <session_token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate the Authorization: Bearer <token> header.
    Returns the User row if the token is valid and not expired.
    Raises HTTP 401 otherwise.
    """
    if not authorization.startswith("Bearer "):
        raise http_401("Authorization header must be: Bearer <token>")

    token = authorization.removeprefix("Bearer ").strip()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Session)
        .where(Session.token == token, Session.expires_at > now)
        .join(Session.user)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise http_401()

    # Bump last_seen_at (non-blocking — fire and forget within same transaction)
    await db.execute(
        update(Session).where(Session.id == session.id).values(last_seen_at=now)
    )
    await db.commit()

    return session.user
