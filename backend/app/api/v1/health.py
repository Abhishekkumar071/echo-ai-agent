"""Health check endpoint — no auth required."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_db

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


class HealthResponse(BaseModel):
    status: str
    db: str
    version: str


@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Returns application and database health."""
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok",
        db=db_status,
        version=settings.app_version,
    )
