"""
Context Assembler.
Combines system instructions, current temporal anchor, short-term history,
retrieved memories, and DB-grounded search results into a clean prompt.
"""
from datetime import datetime, timezone
import logging
from typing import Any
from pydantic import BaseModel, Field

from app.memory.retriever import ScoredMemory
from app.search.result_models import NormalizedSearchResult

logger = logging.getLogger(__name__)


class AssembledContext(BaseModel):
    messages: list[dict[str, str]]
    sources_used: list[dict[str, Any]] = Field(default_factory=list)
    memories_used: list[dict[str, Any]] = Field(default_factory=list)
    is_then_vs_now: bool = False
    system_prompt: str = ""


SYSTEM_PROMPT_TEMPLATE = """You are ECHO, a context-aware conversational AI agent with persistent temporal memory and live web intelligence.
Your tagline: "It doesn't just remember what you asked. It remembers when, why, and what happened next."

Current UTC Time: {current_time}

CORE OPERATIONAL RULES:
1. TRUTHFULNESS & GROUNDING:
   - Never fabricate or hallucinate historical conversations. If the user asks about something not in your memories, explicitly state that you have no record of that discussion.
   - Never invent or fabricate URLs, website titles, or sources.
   - When stating facts learned from Web Search, use bracketed numbers like [1], [2] corresponding to the exact search results provided.

2. TEMPORAL INTEGRITY:
   - Always be aware of the exact dates and times when past topics were discussed.
   - When answering questions about past discussions (e.g., "What did I ask yesterday?", "When did we research X?"), cite the exact dates/times from your retrieved memories.

3. THEN VS NOW COMPARISON:
   - When the user asks "Has anything changed since then?", "Any updates?", or compares past findings with the present:
     - Clearly label what was previously discussed/known (under a "Then / Previous Findings" heading or paragraph with past dates).
     - Clearly label what fresh web search reveals today (under a "Now / Current Status" heading with citations).
     - Directly summarize the key differences or evolutions.

4. UNCERTAINTY & DEGRADED SEARCH:
   - If web search was unavailable or encountered an error, explicitly inform the user that you are answering from existing memory or general knowledge because web search is currently offline.
"""


class ContextAssembler:
    def assemble(
        self,
        user_message: str,
        recent_messages: list[dict[str, Any]],
        memories: list[ScoredMemory],
        search_results: list[NormalizedSearchResult],
        is_then_vs_now: bool = False,
        search_error: str | None = None,
    ) -> AssembledContext:
        """
        Assemble the full prompt payload for the LLM.
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(current_time=now_str)

        # 1. Format retrieved memories
        memory_section = ""
        memories_metadata: list[dict[str, Any]] = []
        if memories:
            memory_section = "\n--- RETRIEVED MEMORIES (Source of Truth for Past Discussions) ---\n"
            for i, mem in enumerate(memories, 1):
                created_iso = mem.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                snippet = mem.original_query or mem.content
                memory_section += f"[Memory {i} | Recorded: {created_iso}]\n"
                memory_section += f"Type: {mem.memory_type}\n"
                if mem.original_query:
                    memory_section += f"Original User Query: {mem.original_query}\n"
                memory_section += f"Details: {mem.content}\n"
                if mem.summary:
                    memory_section += f"Summary: {mem.summary}\n"
                memory_section += "\n"

                memories_metadata.append({
                    "id": str(mem.id),
                    "content": mem.content,
                    "original_query": mem.original_query,
                    "created_at": mem.created_at.isoformat(),
                    "memory_type": mem.memory_type,
                    "similarity_score": mem.similarity_score,
                })

        # 2. Format web search results
        search_section = ""
        sources_metadata: list[dict[str, Any]] = []
        if search_results:
            search_section = "\n--- LIVE WEB SEARCH RESULTS (Retrieved Today via Tavily) ---\n"
            for i, res in enumerate(search_results, 1):
                search_section += f"[{i}] Title: {res.title}\n"
                search_section += f"    URL: {res.url}\n"
                search_section += f"    Snippet: {res.snippet}\n\n"

                sources_metadata.append({
                    "index": i,
                    "title": res.title,
                    "url": res.url,
                    "snippet": res.snippet,
                    "score": res.score,
                    "metadata": res.source_metadata,
                })
        elif search_error:
            search_section = f"\n--- WEB SEARCH STATUS ---\nWeb search attempt failed: {search_error}. Answer based on memory or general knowledge, and notify the user.\n"

        # 3. Build messages list
        full_system = system_instruction
        if memory_section:
            full_system += f"\n{memory_section}"
        if search_section:
            full_system += f"\n{search_section}"

        messages: list[dict[str, str]] = [{"role": "system", "content": full_system}]

        # Append recent short-term messages for natural dialogue flow
        for msg in recent_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Append latest user message
        messages.append({"role": "user", "content": user_message})

        return AssembledContext(
            messages=messages,
            sources_used=sources_metadata,
            memories_used=memories_metadata,
            is_then_vs_now=is_then_vs_now,
            system_prompt=full_system,
        )
