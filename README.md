# ECHO — Context-Aware Web Intelligence Agent

> *"It doesn't just remember what you asked. It remembers when, why, and what happened next."*

**ECHO** is a production-oriented AI agent built for the **minimi Software Engineering Intern Hiring Challenge**. It pairs high-throughput live web intelligence (**Tavily Search** + **Groq LPU**) with persistent temporal memory (**PostgreSQL + pgvector**).

---

## Key Differentiators

1. **True Temporal Memory**: ECHO preserves your verbatim queries with exact UTC timestamps. Ask *"What did I ask yesterday?"* or *"When did we discuss FastAPI?"* and ECHO retrieves the exact conversation without hallucinating.
2. **Then vs Now Comparative Analysis**: Ask *"Has anything changed since then?"*, and ECHO retrieves past discussions, performs a fresh web search, and produces a structured comparative diff.
3. **100% Grounded Citations**: Citations shown in the UI are never hallucinated by the LLM. They are pulled directly from persisted `search_results` database rows.
4. **Resilient Memory Engine**: Memory saving never fails if embedding generation encounters an issue. Rows are committed immediately, and retrieval falls back to temporal date-range and full-text search.
5. **Strict User Isolation**: Anonymous session tokens resolve user identity entirely server-side. Clients cannot forge or access other users' conversations.
6. **Ultra-Fast Streaming**: Powered by Groq LPU inference (`llama-3.3-70b-versatile`) with sub-second time-to-first-token.

---

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React, React Markdown (GFM)
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (Async), Alembic
- **AI / LLM**: Groq API (`llama-3.3-70b-versatile` for generation, `llama-3.1-8b-instant` for intent routing)
- **Search**: Tavily Search API
- **Embeddings**: FastEmbed / Sentence-Transformers (768-dim local embeddings)
- **Database**: PostgreSQL 16 with `pgvector`
- **Testing**: Pytest, Pytest-Asyncio, HTTPX Mock, aiosqlite

---

## Quick Start Guide

### 1. Clone & Configure Environment

```bash
git clone https://github.com/YOUR_USERNAME/echo-ai-agent.git
cd echo-ai-agent
```

Create your `.env` file:
```bash
cp .env.example .env
```
Open `.env` and set your API keys:
- `GROQ_API_KEY`: Get a free key at [console.groq.com](https://console.groq.com)
- `TAVILY_API_KEY`: Get a free key at [tavily.com](https://tavily.com)

---

### 2. Run with Docker Compose (Recommended)

Start the complete system (Postgres + pgvector, Backend, Frontend):

```bash
docker-compose up --build -d
```

- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### 3. Running Locally (Development Mode)

#### A. Start Database (PostgreSQL with pgvector)
```bash
docker-compose up postgres -d
```

#### B. Setup Backend
```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install aiosqlite pytest-asyncio pytest-httpx  # for tests

# Run database migrations
python -m alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

#### C. Setup Frontend
```bash
cd ../frontend
npm install
npm run dev
```
Open your browser at [http://localhost:5173](http://localhost:5173).

---

## Running the Automated Test Suite

ECHO includes a complete automated test suite testing search, memory, agent intent classification, streaming, and user isolation. Tests use in-memory SQLite and mocked network services (no external API calls or live database required):

```bash
cd backend
python -m pytest -v
```

**Test Coverage Highlights:**
- `test_api.py`: Session creation, user isolation checks, conversation retrieval, health check.
- `test_search.py`: Tavily client timeout handling, URL deduplication, snippet sanitization, DB persistence, graceful degradation on 500 error.
- `test_memory.py`: Recency score decay, natural language temporal range extraction, temporal memory saving, user data isolation, memory search API.
- `test_agent.py`: Context assembly, Then-vs-Now prompt grounding, intent classifier heuristics, orchestrator streaming SSE pipeline.

---

## Project Structure

```
echo/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── context_assembler.py # Grounds context with memory & search rows
│   │   │   ├── intent.py            # Fast intent classifier (Groq 8B)
│   │   │   └── orchestrator.py      # 8-stage agent execution pipeline
│   │   ├── api/
│   │   │   ├── deps.py              # Server-side user identity resolution
│   │   │   └── v1/
│   │   │       ├── auth.py          # Session token issuance
│   │   │       ├── chat.py          # SSE streaming & unary chat endpoints
│   │   │       ├── conversations.py # Conversation CRUD
│   │   │       ├── health.py        # Health probe
│   │   │       └── memory.py        # Timeline & semantic search endpoints
│   │   ├── core/                    # Config, exceptions, logging
│   │   ├── database/                # Async engine & session pooling
│   │   ├── memory/                  # Short-term, long-term, temporal, hybrid retriever
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── search/                  # Tavily client, deduplication, search service
│   │   ├── services/                # Groq LLM provider, embedding service
│   │   └── tests/                   # Complete automated test suite
│   ├── alembic/                     # Database migrations
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatArea.tsx         # Main chat, suggestions, streaming UI
│   │   │   ├── ContextPanel.tsx     # Right panel showing verified sources & memories
│   │   │   ├── MessageBubble.tsx    # Markdown rendering, citations, badges
│   │   │   ├── Sidebar.tsx          # Conversation history & timeline navigation
│   │   │   └── TimelineModal.tsx    # Chronological memory inspector
│   │   ├── services/api.ts          # Session handling & SSE stream parser
│   │   └── App.tsx
│   └── Dockerfile
├── .github/workflows/ci.yml         # GitHub Actions CI workflow
├── docker-compose.yml               # Multi-container orchestration
├── design.md                        # Comprehensive architecture & design document
└── README.md
```

---

## Hiring Challenge Acceptance Verification

| Test Scenario | How ECHO Handles It |
|---|---|
| **1. Web Search Query** | Queries Tavily, normalizes and deduplicates URLs, persists to database, and cites sources with clickable verified badges. |
| **2. Memory-Only Query** | Intent analyzer bypasses web search, queries pgvector and temporal records, and answers from conversation history. |
| **3. Cross-Session Recall ("What did I ask yesterday?")** | Resolves user session, matches timestamp boundaries, and returns verbatim previous query and findings without fabrication. |
| **4. Then vs Now ("Has anything changed since then?")** | Pulls historical research, executes fresh search, and formats structured comparative findings. |
| **5. Unmentioned Topic** | Explicitly notifies the user that the topic has not been discussed rather than making up answers. |
| **6. Search Outage** | Catches search errors and gracefully continues in memory-only mode with user notification. |
| **7. Real-Time Streaming** | Streams tokens via SSE with time-to-first-token under 1.5s. |

---

## License

MIT License. Built with ❤️ for the minimi Engineering Hiring Challenge.
