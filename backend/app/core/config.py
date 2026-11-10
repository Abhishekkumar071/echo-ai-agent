"""
Application configuration loaded from environment variables.
Never hardcode credentials here — all secrets come from .env.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "ECHO"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str  # e.g. postgresql+asyncpg://user:pass@host/dbname
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Sessions ──────────────────────────────────────────────────────────
    session_expire_days: int = 30

    # ── Groq ──────────────────────────────────────────────────────────────
    # LLM inference via Groq's LPU hardware (fast, generous free tier)
    groq_api_key: str = ""
    groq_generation_model: str = "llama-3.3-70b-versatile"
    groq_intent_model: str = "llama-3.1-8b-instant"  # cheap fast model for routing
    groq_temperature: float = 0.7
    groq_max_tokens: int = 2048
    groq_timeout: int = 30  # seconds

    # ── Embeddings ────────────────────────────────────────────────────────
    # Local sentence-transformers — no API key, 768-dim, runs on CPU
    # Model: all-mpnet-base-v2 (best quality at 768-dim, ~420MB download once)
    embedding_model: str = "all-mpnet-base-v2"
    embedding_dim: int = 768  # matches pgvector column — no migration needed

    # ── Tavily ────────────────────────────────────────────────────────────
    tavily_api_key: str = ""
    tavily_max_results: int = 5
    tavily_search_timeout: int = 10  # seconds

    # ── Agent ─────────────────────────────────────────────────────────────
    max_search_calls_per_turn: int = 2
    max_context_tokens: int = 32000
    short_term_message_limit: int = 10

    # ── CORS ──────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
