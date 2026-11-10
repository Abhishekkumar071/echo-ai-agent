"""
Session management endpoints.

POST /api/v1/sessions — create an anonymous session (auto-creates a User row).
The returned token is the only credential the client ever holds.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_db
from app.models.session import Session
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])
settings = get_settings()


class SessionResponse(BaseModel):
    session_token: str
    user_id: str
    expires_at: datetime


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """
    Create a new anonymous user + session.
    Call this once on first visit; store the returned token.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.session_expire_days)

    user = User(created_at=now)
    db.add(user)
    await db.flush()  # generate user.id

    token = secrets.token_urlsafe(32)
    session = Session(
        user_id=user.id,
        token=token,
        created_at=now,
        last_seen_at=now,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    logger.info("New session created for user %s", user.id)
    return SessionResponse(
        session_token=token,
        user_id=str(user.id),
        expires_at=expires_at,
    )
