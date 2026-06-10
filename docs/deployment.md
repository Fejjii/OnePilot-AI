# Deployment Guide

This document describes how to run OnePilot AI locally, in Docker, and considerations for production deployment.

---

## Docker Setup

OnePilot AI uses **Docker Compose** to orchestrate all services:
- PostgreSQL 16
- Redis 7
- Qdrant (vector DB)
- Backend (FastAPI)
- Frontend (Next.js)

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### Quick Start (Full Stack)

```bash
# 1. Clone the repository
git clone https://github.com/Fejjii/OnePilot-AI.git
cd OnePilot-AI

# 2. Copy environment file
cp .env.example .env
# Edit .env — set OPENAI_API_KEY if you want real LLM responses (optional)

# 3. Build images
docker compose build

# 4. Start all services
docker compose up -d

# 5. Run migrations
docker compose run --rm migrate

# 6. Seed demo data
docker compose run --rm seed

# 7. Verify services
docker compose ps
docker compose logs -f backend
```

### Multilingual workspace (optional)

No extra deployment steps are required. Users set **Response language** in the AI Workspace (`auto`, `en`, `de`, `fr`, `es`). The backend reads `language_preference` on `POST /chat` requests. Speech transcription may pass a detected language hint when preference is `auto`.

### Access the Application

- **Frontend:** http://localhost:3000
- **Backend API docs:** http://localhost:8000/docs
- **Backend health:** http://localhost:8000/health
- **Qdrant dashboard:** http://localhost:6333/dashboard

### Demo Login

After seeding, use:
- **Email:** `admin@onepilot.ai`
- **Password:** `Demo1234!`

Or use dev auth mode when `DEV_AUTH_ENABLED=true` in `.env` — access the app without credentials. **Never enable dev auth in public deployments.**

Full pre-deploy checklist: [deployment_checklist.md](deployment_checklist.md)

### Post-deploy smoke test

After deploying the backend, run:

```bash
python scripts/smoke_test_public_demo.py --base-url https://your-api.example.com \
  --demo-email admin@onepilot.ai --demo-password Demo1234!
```

This checks health, provider diagnostics, login, chat, prompt-injection blocking, and knowledge search without requiring live OpenAI, Gmail, or Calendar.

---

## Public Demo Deployment (Vercel + Railway / Render / Azure)

This stack is designed for a **LinkedIn demo**: frontend on Vercel, backend on a container host, managed Postgres, and Qdrant Cloud (or self-hosted Qdrant). Not every component is production-hardened — see honest gaps below.

### Minimum production environment variables

| Variable | Required | Notes |
|----------|----------|-------|
| `APP_ENV` | **Yes** | Set to `production` |
| `DATABASE_URL` | **Yes** | Managed PostgreSQL connection string |
| `JWT_SECRET` | **Yes** | Strong random secret, **≥ 32 characters** — never use placeholder values |
| `DEV_AUTH_ENABLED` | **Yes** | Must be `false` — startup fails if `true` in production |
| `CORS_ORIGINS` | **Yes** | Comma-separated frontend URLs, e.g. `https://onepilot-demo.vercel.app` — no wildcards |
| `QDRANT_URL` | **Recommended** | Qdrant Cloud or self-hosted URL; without it, vectors fall back to in-memory (not durable across restarts) |
| `QDRANT_API_KEY` | If using Qdrant Cloud | API key for hosted Qdrant |
| `OPENAI_API_KEY` | No | Optional; deterministic LLM/embeddings fallback without it |
| `REDIS_URL` | No (strongly recommended) | When set and reachable, rate limits use Redis (shared across workers). Falls back to in-memory per process if unset or unavailable. |
| `GMAIL_PROVIDER_MODE` | Recommended for public demo | Set to `mock` unless using a dedicated demo Google account |
| `GOOGLE_CALENDAR_PROVIDER_MODE` | Recommended for public demo | Set to `mock` unless using a dedicated demo Google account |

Do **not** connect personal Gmail or Calendar accounts to a public demo. Use mock providers or an isolated demo Google Workspace account.

### Vercel (frontend)

1. Import the GitHub repository and set the root directory to `frontend/`.
2. Copy `frontend/.env.local.example` → set `NEXT_PUBLIC_API_URL` to your deployed backend URL (e.g. `https://onepilot-api.up.railway.app`).
3. Deploy. `NEXT_PUBLIC_API_URL` is baked in at build time — redeploy after changing it.
4. Add the Vercel URL to backend `CORS_ORIGINS`.

### Railway / Render / Azure Container Apps (backend)

1. Build from `backend/Dockerfile` (or use Docker Compose locally for validation).
2. Set the minimum production env vars above.
3. Run migrations before serving traffic: `alembic upgrade head` (or `docker compose run --rm migrate` locally).
4. Seed demo data if needed: `python scripts/seed_demo.py` (creates `admin@onepilot.ai` / `Demo1234!`).
5. Expose port `8000` and verify `GET /health` returns `status: ok`.
6. Run `scripts/smoke_test_public_demo.py` against the public URL.

**Postgres** is required. **Qdrant** is strongly recommended for persistent RAG; without it the app runs in demo mode with in-memory vectors. **Redis** is strongly recommended for public demos and multi-instance backends so rate limits are shared across workers; the app still runs without it using per-process memory fallback.

---

## Local Backend Run (Without Docker)

### Prerequisites
- Python 3.11+
- PostgreSQL 16 (running locally or via Docker)
- Redis 7 (optional, falls back to in-memory)
- Qdrant (optional, falls back to in-memory)

### Setup

```bash
# 1. Start infrastructure only
docker compose up -d postgres redis qdrant

# Or use the Makefile
make infra

# 2. Install backend dependencies
cd backend
pip install -e ".[dev]"

# 3. Run migrations
alembic upgrade head

# Or use the Makefile
make backend-migrate

# 4. Start backend dev server
uvicorn onepilot.api.main:app --reload --port 8000

# Or use the Makefile
make backend-dev

# 5. In a separate terminal, seed demo data
cd backend
python scripts/seed_demo.py

# Or use the Makefile
make backend-seed
```

### Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

**Required:**
- `DATABASE_URL` — PostgreSQL connection string
- `JWT_SECRET` — Secret key for signing JWTs (change in production!)

**Optional (with fallbacks):**
- `OPENAI_API_KEY` — for real LLM/embeddings (uses deterministic fallback without it)
- `REDIS_URL` — Redis for shared rate-limit counters (in-memory fallback when unset)
- `QDRANT_URL` — for vector search (in-memory fallback)
- `SERPER_API_KEY` — for web search (mock results without it)
- `LANGSMITH_API_KEY` — for LangSmith tracing (disabled by default)

See [.env.example](.env.example) for full list.

---

## Local Frontend Run (Without Docker)

### Prerequisites
- Node.js 20+
- pnpm 8+ (install via `npm install -g pnpm`)

### Setup

```bash
# 1. Install dependencies
cd frontend
pnpm install

# Or use the Makefile
make frontend-install

# 2. Copy frontend environment file
cp .env.example .env.local

# Edit .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# 3. Start dev server
pnpm dev

# Or use the Makefile
make frontend-dev
```

### Access the Application
- **Frontend:** http://localhost:3000
- **Hot reload:** Enabled by default in dev mode

---

## Environment Variables Reference

### Backend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | `dev` | Environment: `dev` or `production` |
| `APP_NAME` | No | `OnePilot AI` | Application name |
| `DATABASE_URL` | **Yes** | — | PostgreSQL connection string |
| `REDIS_URL` | No | — | Redis connection string (optional) |
| `QDRANT_URL` | No | — | Qdrant base URL (optional) |
| `QDRANT_API_KEY` | No | — | Qdrant API key for cloud instances |
| `OPENAI_API_KEY` | No | — | OpenAI API key (optional, uses fallback) |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Chat completion model |
| `OPENAI_EMBEDDING_MODEL` | No | `text-embedding-3-small` | Embedding model |
| `LANGSMITH_API_KEY` | No | — | LangSmith tracing API key (optional) |
| `LANGSMITH_TRACING` | No | `false` | Enable LangSmith trace export |
| `SERPER_API_KEY` | No | — | Serper web search API key (optional) |
| `JWT_SECRET` | **Yes** | `change-me-...` | Secret for signing JWTs — **≥ 32 chars in production** |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | No | `60` | JWT expiry in minutes |
| `CORS_ORIGINS` | **Yes** (production) | — | Comma-separated frontend URLs (no wildcards) |
| `DEV_AUTH_ENABLED` | No | `false` | Set `true` in local `.env` only; **must be false in production** |
| `DEV_ORG_ID` | No | `org_demo_onepilot` | Default org ID for dev auth |
| `DEV_USER_ID` | No | `usr_demo_admin` | Default user ID for dev auth |
| `DEV_BYPASS_QUOTAS` | No | `false` | Skip quota checks in dev mode |

### Frontend Environment Variables

Copy `frontend/.env.local.example` to `frontend/.env.local` for local dev.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | **Yes** | `http://localhost:8000` | Backend API base URL (baked into build; no secrets) |

---

## Deployment Readiness

### What Works
✅ **Docker Compose orchestration** — all services start together  
✅ **Health checks** — backend, Postgres, Redis, Qdrant  
✅ **Multi-stage Docker builds** — optimized for production  
✅ **Non-root containers** — security best practice  
✅ **Persistent volumes** — Postgres, Redis, Qdrant data is retained  
✅ **Migrations** — Alembic migrations run via `docker compose run --rm migrate`  
✅ **Seed data** — Demo data seeding via `docker compose run --rm seed`  

### Production Gaps

**Not production-ready** (Docker Compose is for local/dev only):

❌ **No horizontal scaling** — single instance of each service  
❌ **No load balancer** — no reverse proxy (add nginx/Traefik)  
❌ **No HTTPS** — HTTP only (terminate TLS at reverse proxy)  
❌ **No secret management** — `.env` file with plaintext secrets (use AWS Secrets Manager, Vault, etc.)  
❌ **No CI/CD** — manual build and deploy  
❌ **No monitoring** — no Prometheus, Grafana, Sentry  
❌ **No log aggregation** — logs are written to stdout only (add ELK, Datadog, etc.)  
❌ **No backup automation** — Postgres/Redis backups are manual  

---

## Runtime Modes

### Development Mode (`APP_ENV=dev`)
- **Dev auth:** Set `DEV_AUTH_ENABLED=true` in `.env` to bypass JWT when no header is sent
- **CORS:** `http://localhost:3000` and `http://127.0.0.1:3000` always allowed; optional extra origins via `CORS_ORIGINS`
- **Hot reload:** Backend and frontend auto-reload on code changes
- **Mock providers:** Fallback providers are acceptable

### Production Mode (`APP_ENV=production`)
- **Startup validation:** Fails fast if `DEV_AUTH_ENABLED=true`, weak `JWT_SECRET`, or missing `CORS_ORIGINS`
- **JWT required:** All API requests must include `Authorization: Bearer <token>`
- **CORS:** Only origins listed in `CORS_ORIGINS` (no wildcards, no implicit localhost)
- **Rate limiting:** Login, register, chat, and upload use **Redis fixed-window counters** when `REDIS_URL` is reachable; otherwise **in-memory** per process. Check `rate_limit_backend` on `/health`.
- **Gmail / Calendar:** Use `mock` provider mode or a dedicated demo Google account — not personal accounts

---

## Known Deployment Limitations

1. **No Kubernetes manifests** — Docker Compose only
2. **No cloud-native deployment** — no AWS ECS, GCP Cloud Run, Azure Container Instances examples
3. **No autoscaling** — fixed resource limits
4. **No multi-region** — single-region deployment
5. **No CDN** — frontend static assets served directly by Next.js
6. **No object storage** — uploaded files are not persisted (chunks are stored in Postgres)
7. **No message queue** — no async job processing (add Celery/RabbitMQ/Redis)
8. **Rate limiting without Redis** — falls back to per-process memory counters (not shared across workers or restarts)

See [limitations_roadmap.md](limitations_roadmap.md) for the full list.

---

## Recommended Production Architecture

```mermaid
flowchart TB
    subgraph Internet
        Users["Users"]
    end
    
    subgraph Edge
        CDN["CDN<br/>(CloudFlare, Cloudfront)"]
        WAF["WAF<br/>(Web Application Firewall)"]
    end
    
    subgraph Load_Balancer
        LB["Load Balancer<br/>(nginx, Traefik, ALB)"]
    end
    
    subgraph App_Tier
        Frontend1["Frontend 1<br/>(Next.js)"]
        Frontend2["Frontend 2<br/>(Next.js)"]
        Backend1["Backend 1<br/>(FastAPI)"]
        Backend2["Backend 2<br/>(FastAPI)"]
    end
    
    subgraph Data_Tier
        Postgres["Postgres<br/>(Primary + Replicas)"]
        Redis["Redis<br/>(Cluster)"]
        Qdrant["Qdrant<br/>(Sharded)"]
        S3["Object Storage<br/>(S3, R2)"]
    end
    
    subgraph Observability
        Logs["Log Aggregation<br/>(ELK, Datadog)"]
        Metrics["Metrics<br/>(Prometheus, Grafana)"]
        Traces["Tracing<br/>(LangSmith, Jaeger)"]
    end
    
    Users --> CDN
    CDN --> WAF
    WAF --> LB
    LB --> Frontend1
    LB --> Frontend2
    LB --> Backend1
    LB --> Backend2
    
    Frontend1 --> Backend1
    Frontend2 --> Backend2
    
    Backend1 --> Postgres
    Backend1 --> Redis
    Backend1 --> Qdrant
    Backend1 --> S3
    Backend2 --> Postgres
    Backend2 --> Redis
    Backend2 --> Qdrant
    Backend2 --> S3
    
    Backend1 --> Logs
    Backend1 --> Metrics
    Backend1 --> Traces
    Backend2 --> Logs
    Backend2 --> Metrics
    Backend2 --> Traces
```

---

## Makefile Targets

The `Makefile` provides convenience commands for local development:

### Infrastructure
```bash
make infra           # Start Postgres, Redis, Qdrant
make infra-down      # Stop infrastructure containers
```

### Backend
```bash
make backend-install # Install backend dependencies
make backend-migrate # Run Alembic migrations
make backend-seed    # Seed demo data
make backend-dev     # Start backend dev server
make backend-test    # Run pytest suite
make backend-lint    # Run Ruff linter
```

### Frontend
```bash
make frontend-install # Install frontend dependencies
make frontend-dev     # Start Next.js dev server
make frontend-build   # Production build
make frontend-test    # Run Vitest tests
make frontend-lint    # Run ESLint + tsc typecheck
```

### Docker
```bash
make docker-build    # Build all Docker images
make docker-up       # Start full stack
make docker-down     # Stop and remove containers
make docker-logs     # Follow logs
make docker-migrate  # Run migrations in Docker
make docker-seed     # Seed data in Docker
```

### Quality
```bash
make test            # Run all tests (backend + frontend)
make lint            # Run all linters (backend + frontend)
make check-stack     # Verify all services are healthy
```

### First-Time Setup
```bash
make setup           # Full setup: infra + install + migrate + seed
```

---

## Troubleshooting

### Backend won't start
**Symptom:** `uvicorn` exits immediately

**Fixes:**
1. Check `DATABASE_URL` is correct
2. Ensure Postgres is running and reachable
3. Check logs: `docker compose logs backend`

### Frontend can't reach backend
**Symptom:** API requests return network errors

**Fixes:**
1. Verify `NEXT_PUBLIC_API_URL` is set in `frontend/.env.local` (see `frontend/.env.local.example`)
2. Ensure backend is running on port 8000
3. Check `CORS_ORIGINS` on the backend includes your frontend URL in production

### Migrations fail
**Symptom:** `alembic upgrade head` exits with error

**Fixes:**
1. Check Postgres connection: `psql $DATABASE_URL`
2. Verify `alembic/versions/` contains migration files
3. Reset database (destructive): `docker compose down -v && docker compose up -d postgres`

### Seed script fails
**Symptom:** `python scripts/seed_demo.py` exits with error

**Fixes:**
1. Ensure backend is running and healthy: `curl http://localhost:8000/health`
2. Verify migrations are applied: `alembic current`
3. Check backend logs for errors

### Docker build fails
**Symptom:** `docker compose build` exits with error

**Fixes:**
1. Check Docker has enough disk space: `docker system df`
2. Prune old images: `docker system prune -a`
3. Verify Dockerfile syntax

---

## Summary

OnePilot AI is **deployment-ready for local development and testing** via Docker Compose.

For **production deployment**, additional infrastructure is required:
- Kubernetes or cloud-native orchestrator
- Load balancer with TLS termination
- Secret management (Vault, AWS Secrets Manager)
- Log aggregation and monitoring
- Backup automation
- Autoscaling policies

See **Recommended Production Architecture** above for a scalable setup.
