"""
LLM Provider using the official Groq client.
Supports fast streaming completions and structured JSON schema output.
"""
from collections.abc import AsyncGenerator
import json
import logging
from typing import Any
from groq import AsyncGroq

from app.core.config import get_settings
from app.core.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMProvider:
    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.client: AsyncGroq | None = None
        if self.api_key and not self.api_key.startswith("your_"):
            self.client = AsyncGroq(api_key=self.api_key)
        else:
            logger.warning("Groq API key not configured or using placeholder.")

    def _ensure_client(self) -> AsyncGroq:
        if self.client is None:
            raise LLMError("Groq API key is not configured. Please set GROQ_API_KEY in .env.")
        return self.client

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Execute a non-streaming chat completion."""
        client = self._ensure_client()
        settings = get_settings()
        target_model = model or settings.groq_generation_model

        try:
            response = await client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("Groq chat completion failed: %s", exc)
            raise LLMError(f"LLM generation failed: {exc}") from exc

    async def stream_text(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Stream incremental text tokens from Groq."""
        client = self._ensure_client()
        settings = get_settings()
        target_model = model or settings.groq_generation_model

        try:
            stream = await client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as exc:
            logger.error("Groq streaming completion failed: %s", exc)
            raise LLMError(f"LLM streaming failed: {exc}") from exc

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate structured JSON using Groq's json_object response format."""
        client = self._ensure_client()
        settings = get_settings()
        target_model = model or settings.groq_intent_model

        try:
            response = await client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:
            logger.warning("Groq JSON generation failed or returned invalid JSON: %s", exc)
            # Return safe default dict
            return {}
