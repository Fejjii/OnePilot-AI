# OnePilot AI

**OnePilot AI** is a production-style AI-powered business workspace for small and medium businesses. It combines a company knowledge base, retrieval-augmented generation (RAG), agentic workflow automation, email drafting, lead management, human approval gates, usage tracking, memory, and security guardrails in a single multi-tenant SaaS platform.

> **Capstone project status:** All 8 phases complete. 494 backend tests passing. Full Docker stack validated. Frontend TypeScript build passing.

---

## Problem Solved

Small businesses use many disconnected AI tools and lose time managing scattered knowledge, customer messages, leads, approvals, and operations. Generic chatbots are not enough — business AI needs company knowledge, safe workflows, usage controls, auditability, and human approval before acting.

**OnePilot AI** centralizes:
- Business knowledge (RAG over uploaded documents)
- AI agents with intent routing and tool calling (LangGraph)
- Human approval gates before any external action
- Usage tracking, audit logs, and memory per conversation
- Multi-tenant isolation so each organization's data stays private

---

## How It Works

1. **Upload knowledge** — markdown, text, CSV, PDF, or DOCX files are chunked and embedded into a vector store (Qdrant or in-memory fallback).
2. **Ask questions** — the AI retrieves the most relevant chunks, generates a grounded answer with citations, and refuses to answer when evidence is weak.
3. **Run workflows** — the LangGraph agent classifies the user's intent, selects tools, and creates approval requests for any external action (email send, CRM update, lead change).
4. **Approve or reject** — humans review pending actions in the Approvals queue before anything is executed.
5. **Track everything** — every action writes an audit log and usage event scoped to the organization.

---

## Key Features

| Feature | Notes |
|---------|-------|
| Multi-tenant SaaS | Organizations, users, roles (Owner/Admin/Member/Viewer), plans, quotas |
| RAG knowledge base | Upload, chunk, embed, search, grounded answers, citations, weak-evidence guardrail |
| LangGraph agent | Intent routing, tool registry, multi-step reasoning |
| Email drafting | Draft generation with HubSpot/Gmail mock adapters |
| Lead management | Lead tracking, qualification, CRM mock |
| Human approval gates | All external actions require explicit approval |
| Memory | Session, conversation, and long-term memory per org |
| Audit logs | Every sensitive action is logged with actor, org, and metadata |
| Usage tracking | Per-org quota enforcement and usage event history |
| Security | JWT auth, RBAC, prompt injection detection, sensitive data redaction, rate limiting |
| Provider adapters | Every external dependency (LLM, embeddings, vector DB, CRM, email) has a mock fallback |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| AI / Agent | LangGraph, LangChain, OpenAI |
| Database | PostgreSQL, SQLAlchemy 2.x, Alembic |
| Cache | Redis |
| Vector DB | Qdrant |
| Frontend | Next.js 16, TypeScript, Tailwind CSS, TanStack Query |
| Testing | pytest (494 tests), Ruff, Vitest |
| Infra | Docker Compose |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   Next.js Frontend                   │
│   Dashboard · AI Workspace · Knowledge · Leads       │
│   Approvals · Usage · Memory · Settings              │
└──────────────────────┬───────────────────────────────┘
                       │ REST API
┌──────────────────────▼───────────────────────────────┐
│                 FastAPI Backend                       │
│  ┌─────────┐ ┌──────────┐ ┌────────────────────┐    │
│  │ Routers │→│ Services │→│ Repos / Providers  │    │
│  │ (thin)  │ │ (logic)  │ │ (SQLAlchemy/Qdrant) │   │
│  └─────────┘ └──────────┘ └────────────────────┘    │
│  ┌──────────────────┐  ┌──────────────────────┐      │
│  │  LangGraph Agent │  │   Security Layer     │      │
│  │  intent · tools  │  │  RBAC · guardrails   │      │
│  └──────────────────┘  └──────────────────────┘      │
└──────┬──────────┬──────────┬────────────────────────┘
       │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐
  │Postgres│ │ Redis  │ │ Qdrant │
  │  (DB)  │ │(cache) │ │(vector)│
  └────────┘ └────────┘ └────────┘
```

See [docs/architecture.md](docs/architecture.md) for Mermaid diagrams.

---

## Quick Start (Local Dev)

### Prerequisites

- Python 3.11+
- Node.js 20+ and [pnpm](https://pnpm.io/)
- Docker and Docker Compose
- (Optional) OpenAI API key — without one, the system uses deterministic fallback providers

### 1. Clone and configure

```bash
git clone <repo-url> onepilot-ai
cd onepilot-ai
cp .env.example .env
# Edit .env — set OPENAI_API_KEY if you want real LLM responses (optional)
```

### 2. Start infrastructure

```bash
docker compose up -d postgres redis qdrant
```

### 3. Backend setup

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn onepilot.api.main:app --reload --port 8000
```

Or use the helper script:

```bash
cd backend
python scripts/dev_setup.py
```

### 4. Frontend setup

```bash
cd frontend
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm install
pnpm dev
```

### 5. Seed demo data

```bash
# Backend must be running
cd backend
python scripts/seed_demo.py
```

This creates a demo user (`admin@novaedge.io` / `Demo1234!`), ingests 19 NovaEdge knowledge documents, and seeds leads, approvals, audit logs, and usage events.

### 6. Open the app

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

---

## Docker (Full Stack)

Run the entire stack — Postgres, Redis, Qdrant, backend, and frontend — in Docker:

```bash
# First-time: copy and configure .env
cp .env.example .env

# Build images
docker compose build

# Start full stack
docker compose up -d

# Run migrations
docker compose run --rm migrate

# Seed demo data
docker compose run --rm seed
```

Or use the Makefile:

```bash
make docker-build
make docker-up
make docker-migrate
make docker-seed
```

### Verify the stack

```bash
# Check all services are healthy
cd backend && python scripts/check_stack.py

# Or individually:
curl http://localhost:8000/health       # backend
curl http://localhost:6333/healthz      # qdrant
```

---

## Environment Variables

Copy `.env.example` to `.env` (root) and `frontend/.env.example` to `frontend/.env.local`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | `dev` | `dev` or `production` |
| `DATABASE_URL` | **Yes** | — | PostgreSQL connection string |
| `REDIS_URL` | No | — | Redis connection string (optional, in-memory fallback) |
| `QDRANT_URL` | No | — | Qdrant base URL (optional, in-memory fallback) |
| `QDRANT_API_KEY` | No | — | Qdrant API key for cloud |
| `OPENAI_API_KEY` | No | — | OpenAI key (optional, deterministic fallback without it) |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Chat completion model |
| `OPENAI_EMBEDDING_MODEL` | No | `text-embedding-3-small` | Embedding model |
| `LANGSMITH_API_KEY` | No | — | LangSmith tracing (optional) |
| `LANGSMITH_TRACING` | No | `false` | Enable LangSmith trace export |
| `SERPER_API_KEY` | No | — | Web search (optional, returns mock results without it) |
| `JWT_SECRET` | **Yes** | `change-me-...` | Secret for signing JWTs — **change in production** |
| `JWT_EXPIRE_MINUTES` | No | `60` | JWT expiry in minutes |
| `DEV_AUTH_ENABLED` | No | `true` | Bypass JWT in dev mode (disable in production) |
| `DEV_BYPASS_QUOTAS` | No | `false` | Skip quota checks in dev |
| `NEXT_PUBLIC_API_URL` | **Yes** (frontend) | `http://localhost:8000` | Backend URL (baked into frontend build) |

---

## Running Tests

### Backend (494 tests)

```bash
cd backend
pytest -v                         # all tests
pytest -v tests/test_chat.py      # single file
pytest -v --cov=onepilot          # with coverage
```

### Linting

```bash
cd backend
ruff check src tests
ruff format --check src tests
```

### Frontend

```bash
cd frontend
pnpm typecheck    # TypeScript check
pnpm lint         # ESLint
pnpm test         # Vitest
pnpm build        # production build
```

### All at once (Makefile)

```bash
make test     # backend + frontend tests
make lint     # backend + frontend linters
```

---

## Evaluation

The evaluation harness lives in `backend/src/onepilot/evaluation/`:

```bash
cd backend
# Run intent classification evaluation
python -m onepilot.evaluation.runner
```

See [docs/evaluation.md](docs/evaluation.md) for the evaluation approach, datasets, and results.

---

## Page Tour

| Page | Path | Description |
|------|------|-------------|
| Login / Register | `/login`, `/register` | Auth with JWT, dev bypass available |
| Dashboard | `/` | Usage summary, recent activity, quick actions |
| AI Workspace | `/workspace` | Chat with the LangGraph agent, citations, approvals |
| Knowledge Base | `/knowledge` | Upload documents, semantic search, grounded answers |
| Leads | `/leads` | Lead table with qualification status |
| Approvals | `/approvals` | Review and approve/reject pending agent actions |
| Memory | `/memory` | Conversation memory and long-term facts |
| Usage | `/usage` | Usage events, quota status, audit logs |
| Settings | `/settings` | Organization and user settings |

> **Screenshots:** See `docs/screenshots/` (placeholder — add your own during demo).

---

## Documentation

| Doc | Description |
|-----|-------------|
| [Architecture](docs/architecture.md) | System design, layer responsibilities, Mermaid diagrams |
| [Agent Workflow](docs/agent_workflow.md) | LangGraph flow, intents, tools, approval gates |
| [RAG System](docs/rag_system.md) | Ingestion, chunking, embeddings, retrieval, citations |
| [Security](docs/security.md) | Auth, RBAC, tenant isolation, guardrails, production gaps |
| [Evaluation](docs/evaluation.md) | Intent eval harness, test coverage, RAG evaluation approach |
| [Demo Script](docs/demo_script.md) | 5–7 minute demo walkthrough |
| [Limitations & Roadmap](docs/limitations_roadmap.md) | Honest assessment of mock components and future work |
| [Data Model](docs/data_model.md) | Database schema and entity relationships |

---

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundations & scaffold | ✅ Complete |
| 2 | Auth, tenants, plans, quotas | ✅ Complete |
| 3 | Demo data (NovaEdge Solutions) | ✅ Complete |
| 4 | RAG & knowledge base | ✅ Complete |
| 5 | LangGraph agent & tools | ✅ Complete |
| 6 | Approvals, usage tracking, memory | ✅ Complete |
| 7 | Frontend pages & integration | ✅ Complete |
| 8 | Docker, docs, finalization | ✅ Complete |

**494 backend tests passing.** Frontend typecheck, lint, build, and tests all pass.

---

## Multilingual Support

OnePilot supports multilingual **user interaction** in the AI Workspace and speech-to-text flow while keeping the knowledge base in its original language for grounded RAG.

### Supported languages

| Language | Code |
|----------|------|
| English | `en` |
| German | `de` |
| French | `fr` |
| Spanish | `es` |

### Language preference

- **Auto (default):** Detect language from the user message (or speech transcript) and reply in that language.
- **Fixed (`en` / `de` / `fr` / `es`):** Always reply in the selected language, even if the user writes in another language.

The workspace language selector controls response language only. Navigation and sidebar labels remain in English.

### RAG behavior

- Retrieval uses the **original user query** (source language).
- Optional **English query expansion** may run for non-English questions when OpenAI is configured, to improve recall against English KB documents.
- Answers are generated in the **response language**.
- **Citations keep original document titles and sections** (not translated).

### Speech-to-text

Transcription returns a detected `language` code. When preference is Auto, that hint is passed to the agent for more reliable detection.

### Current limitations

- Knowledge base documents are **not translated** at ingest time.
- UI chrome (nav, settings labels) is **English only**.
- Cross-lingual retrieval is heuristic (original query + optional English expansion), not full multilingual embeddings.

### Future work

- Translated knowledge base ingestion
- Multilingual document ingestion pipelines
- Stronger cross-lingual retrieval (multilingual embeddings, query routing)

---

## Known Limitations

1. **Mock providers** — HubSpot, Gmail, Google Calendar, Stripe, and Serper all use in-memory mocks. No real external API calls are made.
2. **JWT in localStorage** — Tokens are stored in `localStorage` for simplicity. In production, use HTTP-only cookies.
3. **No streaming** — Chat responses are synchronous (no Server-Sent Events or WebSocket yet).
4. **Rate limiting** — In-memory token bucket resets on restart. Redis-backed rate limiting is planned.
5. **No OAuth/SSO** — Username/password only.
6. **No production deployment** — This is a local and Docker Compose setup. Kubernetes/cloud deployment is not included.

See [docs/limitations_roadmap.md](docs/limitations_roadmap.md) for the full list.

---

## Contact

**Sofien Fejji**  
- GitHub: [Fejjii](https://github.com/Fejjii)
- Email: sofien.fejji93@hotmail.com

---

## License

This project is part of an AI Engineering bootcamp capstone.
