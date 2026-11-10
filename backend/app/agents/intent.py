"""
Intent analyzer module.
Determines whether the incoming user question requires:
- Memory retrieval only (e.g. 'What did I ask yesterday?')
- Web search only (e.g. 'What is the current stock price of Apple?')
- Hybrid memory + web search (e.g. 'Has anything changed since yesterday's discussion?')
- Then-vs-Now comparative analysis.
"""
from datetime import datetime, timezone
import json
import logging
import re
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class IntentClassification(BaseModel):
    needs_search: bool = False
    needs_memory: bool = False
    is_then_vs_now: bool = False
    search_query: str | None = None
    memory_query: str | None = None
    reasoning: str = Field(default="")


INTENT_SYSTEM_PROMPT = """You are an intent classification subsystem for ECHO, a context-aware AI agent.
Analyze the user's latest message and recent conversation context.
Decide:
1. "needs_search": true if the user asks for fresh factual information, current events, recent tech updates, or external documentation.
2. "needs_memory": true if the user asks about previous conversations, what was discussed in the past, historical decisions, or references 'yesterday', 'earlier', 'we discussed', etc.
3. "is_then_vs_now": true if the user asks whether previous findings or discussions have changed (e.g. 'Has anything changed since then?', 'Compare what we talked about yesterday with today').
4. "search_query": an optimized web search query string if needs_search is true, else null.
5. "memory_query": search keywords for past memory if needs_memory is true, else null.
6. "reasoning": brief explanation.

Output valid JSON matching this schema:
{
  "needs_search": boolean,
  "needs_memory": boolean,
  "is_then_vs_now": boolean,
  "search_query": string | null,
  "memory_query": string | null,
  "reasoning": string
}
"""


class IntentAnalyzer:
    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider or LLMProvider()
        self.settings = get_settings()

    def _heuristic_fallback(self, message: str, has_history: bool) -> IntentClassification:
        """Deterministic rule-based intent fallback when LLM is offline or unconfigured."""
        msg_lower = message.lower()

        # Then-vs-now indicators
        if any(p in msg_lower for p in ["has anything changed", "since then", "since yesterday", "any updates since", "compared to what we discussed"]):
            return IntentClassification(
                needs_search=True,
                needs_memory=True,
                is_then_vs_now=True,
                search_query=message,
                memory_query=message,
                reasoning="Heuristic: Then-vs-Now query detected.",
            )

        # Memory indicators
        memory_keywords = ["yesterday", "last week", "earlier", "remember", "what did i ask", "what did we discuss", "previously", "have we talked about"]
        needs_memory = any(kw in msg_lower for kw in memory_keywords) or has_history

        # Search indicators
        search_keywords = ["latest", "current", "news", "today", "best", "framework", "library", "documentation", "how to", "who is", "what is", "price", "release"]
        needs_search = any(kw in msg_lower for kw in search_keywords) or (not needs_memory and len(message.split()) > 3)

        return IntentClassification(
            needs_search=needs_search,
            needs_memory=needs_memory,
            is_then_vs_now=False,
            search_query=message if needs_search else None,
            memory_query=message if needs_memory else None,
            reasoning="Heuristic fallback classification.",
        )

    async def analyze(
        self,
        message: str,
        recent_messages: list[dict] | None = None,
    ) -> IntentClassification:
        """Classify user intent using fast Groq model with heuristic fallback."""
        has_history = bool(recent_messages and len(recent_messages) > 0)

        # Quick heuristic check for pure memory queries like "What did I ask yesterday?"
        pure_memory_pattern = re.compile(r"^(what did (i|we) (ask|discuss|talk about)|what were we talking about)", re.IGNORECASE)
        if pure_memory_pattern.match(message.strip()):
            return IntentClassification(
                needs_search=False,
                needs_memory=True,
                is_then_vs_now=False,
                search_query=None,
                memory_query=message.strip(),
                reasoning="Rule: Pure historical memory recall question.",
            )

        try:
            # Build mini-history for context
            context_summary = ""
            if recent_messages:
                last_few = recent_messages[-3:]
                context_summary = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in last_few)

            prompt_user = f"Current UTC Time: {datetime.now(timezone.utc).isoformat()}\n"
            if context_summary:
                prompt_user += f"Recent Conversation Context:\n{context_summary}\n\n"
            prompt_user += f"User Message:\n{message}"

            messages = [
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_user},
            ]

            raw_json = await self.llm.generate_json(
                messages=messages,
                model=self.settings.groq_intent_model,
                temperature=0.0,
            )

            if raw_json and "needs_search" in raw_json:
                return IntentClassification(
                    needs_search=bool(raw_json.get("needs_search", False)),
                    needs_memory=bool(raw_json.get("needs_memory", False)),
                    is_then_vs_now=bool(raw_json.get("is_then_vs_now", False)),
                    search_query=raw_json.get("search_query") or (message if raw_json.get("needs_search") else None),
                    memory_query=raw_json.get("memory_query") or (message if raw_json.get("needs_memory") else None),
                    reasoning=raw_json.get("reasoning", "LLM classification"),
                )

        except Exception as exc:
            logger.warning("Intent analysis LLM call failed, falling back to heuristics: %s", exc)

        return self._heuristic_fallback(message, has_history=has_history)
