# ECHO — Context-Aware Web Intelligence Agent

> *"It doesn't just remember what you asked. It remembers when, why, and what happened next."*

ECHO is a production-oriented AI agent combining **live Tavily web search** with **persistent temporal memory** backed by PostgreSQL + pgvector.

---

## Quick Start

### Prerequisites
- Docker Desktop (with Compose)
- Python 3.11+
- Node.js 18+
- Gemini API key → [aistudio.google.com](https://aistudio.google.com)
- Tavily API key → [tavily.com](https://tavily.com)

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/echo-ai-agent
cd echo-ai-agent
cp .env.example .env
# Edit .env — set GEMINI_API_KEY and TAVILY_API_KEY
```

### 2. Start Postgres (with pgvector)

```bash
docker-compose up postgres -d
```

### 3. Install backend dependencies

```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt  # for tests
```

### 4. Run database migrations

```bash
# From backend/ directory
DATABASE_URL=postgresql+asyncpg://echo:echo_password@localhost:5432/echo_db \
  python -m alembic upgrade head
```

> **Windows (PowerShell):**
> ```powershell
> $env:DATABASE_URL="postgresql+asyncpg://echo:echo_password@localhost:5432/echo_db"
> python -m alembic upgrade head
> ```

### 5. Start the backend

```bash
# From backend/ directory
DATABASE_URL=postgresql+asyncpg://echo:echo_password@localhost:5432/echo_db \
  uvicorn app.main:app --reload
```

> **Windows (PowerShell):**
> ```powershell
> $env:DATABASE_URL="postgresql+asyncpg://echo:echo_password@localhost:5432/echo_db"
> uvicorn app.main:app --reload
> ```

### 6. Verify — Health check

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","db":"ok","version":"1.0.0"}
```

### 7. Run tests

```bash
# From backend/ directory
python -m pytest -v
```

---

## Architecture

See [design.md](./design.md) for the full architecture document including:
- Agent execution lifecycle
- Memory architecture (short-term / long-term / temporal)
- Hybrid retrieval strategy
- Database schema
- API contracts
- Security model

---

## API Reference

Interactive docs available at: `http://localhost:8000/docs`

Key endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/sessions` | Create anonymous session |
| `GET` | `/api/v1/conversations` | List conversations |
| `GET` | `/api/v1/conversations/{id}` | Get conversation + messages |
| `POST` | `/api/v1/chat` | Send message (non-streaming) |
| `POST` | `/api/v1/chat/stream` | Send message (SSE streaming) |
| `GET` | `/api/v1/memory/search` | Semantic memory search |
| `GET` | `/api/v1/memory/timeline` | Chronological memory timeline |

---

## Security Model

- **User isolation**: session tokens are cryptographically random (`secrets.token_urlsafe(32)`). `user_id` is never accepted from the client.
- **Search citations**: all citations shown to users are DB-backed (`search_results` table). The LLM cannot fabricate URLs.
- **Memory resilience**: embedding failures never cause memory loss. Rows are committed first; embeddings applied asynchronously.
- **API keys**: always server-side. Never exposed to the frontend.

---

## Development Phases

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ | Architecture & design |
| Phase 2 | ✅ | Backend foundation (FastAPI, Postgres, sessions, health) |
| Phase 3 | 🔜 | Web search (Tavily, normalization, citations) |
| Phase 4 | 🔜 | Memory engine (embeddings, pgvector, hybrid retrieval) |
| Phase 5 | 🔜 | Agent orchestrator (intent, context assembly, streaming) |
| Phase 6 | 🔜 | React frontend |
| Phase 7 | 🔜 | Tests & optimization |
| Phase 8 | 🔜 | Docker, CI, deployment |
