"""
ECHO FastAPI application factory.

Startup order:
1. Configure logging
2. Register exception handlers
3. Mount routers
4. CORS middleware

The app is imported by uvicorn: uvicorn app.main:app
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import (
    ConversationNotFoundError,
    EchoError,
    SessionNotFoundError,
)
from app.core.logging import configure_logging
from app.api.v1 import auth, health, conversations, chat, memory

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    @app.exception_handler(EchoError)
    async def echo_error_handler(request: Request, exc: EchoError) -> JSONResponse:
        logger.warning("Domain error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    # ── Routers ───────────────────────────────────────────────────────────────
    PREFIX = "/api/v1"
    app.include_router(health.router, prefix=PREFIX)
    app.include_router(auth.router, prefix=PREFIX)
    app.include_router(conversations.router, prefix=PREFIX)
    app.include_router(chat.router, prefix=PREFIX)
    app.include_router(memory.router, prefix=PREFIX)

    logger.info("ECHO %s started", settings.app_version)
    return app


app = create_app()
