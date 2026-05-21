# Azure Deployment Guide (Short-Term Demo)

Temporary **3–5 day** Azure demo deployment for OnePilot AI. **Local Docker Compose remains the fallback** for reviewers and development (`master` branch).

Work on the **`deployment/azure`** branch only. Do not commit secrets to git — use Azure Container App secrets or Key Vault.

---

## Purpose

- Host backend and frontend on **Azure Container Apps** for a capstone/reviewer demo.
- Keep cost low and teardown simple.
- Preserve local Docker behavior unchanged when `CORS_ALLOWED_ORIGINS` is unset (defaults to localhost).

---

## Recommended Architecture

| Component | Recommendation |
|-----------|----------------|
| Backend | Azure Container App (consumption) |
| Frontend | Azure Container App (consumption) |
| Images | Azure Container Registry (Basic) |
| Postgres | Azure Database for PostgreSQL Flexible Server (Burstable, smallest SKU) **or** Postgres container for minimal cost |
| Qdrant | Qdrant Cloud free/small tier **or** Qdrant container on ACA |
| Redis | **Optional** — leave `REDIS_URL` empty (in-memory fallback) |
| Secrets | Container App secrets (Key Vault optional later) |

---

## Cost Guidance (3–5 days)

| Profile | Estimated USD (excluding OpenAI/Serper usage) |
|---------|-----------------------------------------------|
| **Minimal** (container Postgres, skip Redis) | ~$10–35 |
| **Cleaner demo** (Flexible Server + Qdrant Cloud) | ~$25–55 |

**Biggest cost risk:** leaving resources running after the demo. Use the [shutdown checklist](#shutdown-checklist) below.

---

## Deployment Phases

### Phase 1 — Backend health

1. Build and push backend image to ACR.
2. Create backend Container App with minimal env (`APP_ENV`, `JWT_SECRET`, `CORS_ALLOWED_ORIGINS` can wait until frontend exists).
3. Verify: `GET https://<backend-fqdn>/health` returns `"status": "ok"`.

### Phase 2 — Frontend

1. Build frontend image with **`NEXT_PUBLIC_API_URL=https://<backend-fqdn>`** (see [Build guidance](#build-guidance)).
2. Deploy frontend Container App.
3. Set backend `CORS_ALLOWED_ORIGINS` to include `https://<frontend-fqdn>`.
4. Verify UI loads and browser network calls hit the backend URL.

### Phase 3 — Postgres

1. Provision Azure PostgreSQL (or container Postgres).
2. Set `DATABASE_URL` (often with `?sslmode=require` for Flexible Server).
3. Run migrations: `alembic upgrade head` (see [Migration guidance](#migration-guidance)).
4. Verify `GET /providers` shows Postgres healthy.

### Phase 4 — Qdrant

1. Set `QDRANT_URL` (and `QDRANT_API_KEY` if using Qdrant Cloud).
2. Verify vector provider in `/providers`.

### Phase 5 — OpenAI and Serper

1. Add `OPENAI_API_KEY` and optional `SERPER_API_KEY` as secrets.
2. Verify `/runtime/config` and chat/search in the app.

### Phase 6 — Gmail and Calendar (optional)

1. Copy pre-generated OAuth refresh token and client credentials into secrets (see [Provider setup](#provider-setup)).
2. Verify `/health` provider fields and approval-gated flows.

### Phase 6b — LangSmith tracing (optional)

1. Create Container App secret `langsmith-api-key` from your LangSmith API key (never commit to git).
2. Set backend env (preserve existing vars):

   | Variable | Value |
   |----------|--------|
   | `LANGSMITH_TRACING` | `true` |
   | `LANGSMITH_API_KEY` | `secretref:langsmith-api-key` |
   | `LANGSMITH_PROJECT` | `onepilot-ai` |
   | `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` |

3. Restart the backend revision.
4. Verify `GET /health` → `providers.langsmith: true` and `GET /providers` → LangSmith `mode: live` (not `missing`).
5. Run a chat prompt in the workspace; confirm a run appears in the LangSmith project `onepilot-ai`.

Example (replace `<key>` locally; do not paste keys into shell history in shared environments):

```bash
az containerapp secret set -g rg-onepilot-demo -n ca-onepilot-backend \
  --secrets langsmith-api-key=<key>

az containerapp update -g rg-onepilot-demo -n ca-onepilot-backend \
  --set-env-vars \
    LANGSMITH_TRACING=true \
    LANGSMITH_API_KEY=secretref:langsmith-api-key \
    LANGSMITH_PROJECT=onepilot-ai \
    LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

### Phase 7 — Smoke tests

Use the [smoke test checklist](#smoke-test-checklist).

---

## Required Environment Variables

See **[`.env.azure.example`](../.env.azure.example)** at the repo root for a full placeholder template.

- **Never** commit `.env`, API keys, or refresh tokens.
- Backend env vars are injected at Container App runtime (except frontend build-time vars).
- **`NEXT_PUBLIC_API_URL`** is set when **building** the frontend image, not only at runtime.

---

## Build Guidance

### Backend image

From repo root or `backend/`:

```bash
# Example: build and tag for ACR
docker build -t <acr>.azurecr.io/onepilot-backend:latest ./backend
docker push <acr>.azurecr.io/onepilot-backend:latest
```

Or use `az acr build`. Container listens on **port 8000**; health path **`/health`**.

### Frontend image

**`NEXT_PUBLIC_API_URL` must be the public HTTPS URL of the backend** at build time. The browser calls the API directly (no Next.js proxy).

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://<backend-fqdn> \
  -t <acr>.azurecr.io/onepilot-frontend:latest \
  ./frontend
docker push <acr>.azurecr.io/onepilot-frontend:latest
```

**Important:** If the backend FQDN changes, you must **rebuild and redeploy** the frontend image.

The `frontend/Dockerfile` documents this build-arg. Local Docker Compose continues to use `http://localhost:8000` by default.

---

## CORS Guidance

The backend reads **`CORS_ALLOWED_ORIGINS`** (comma-separated). Example:

```bash
CORS_ALLOWED_ORIGINS=https://<frontend-fqdn>,http://localhost:3000,http://127.0.0.1:3000
```

Optional: `CORS_ALLOW_CREDENTIALS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS` (defaults: credentials true, methods/headers `*`).

Without Azure origins in this list, the browser will block API calls from the deployed frontend.

---

## Migration Guidance

Run Alembic against the Azure `DATABASE_URL`:

```bash
# One-off job container, ACA Job, or local shell with network access to Postgres
cd backend
alembic upgrade head
```

**Azure PostgreSQL Flexible Server** typically requires TLS:

```text
postgresql+psycopg://user:password@<server>.postgres.database.azure.com:5432/onepilot?sslmode=require
```

Confirm connectivity before seeding.

---

## Seed Guidance

Demo seeding uses:

1. `POST /demo/setup` — only when **`APP_ENV=dev`** (or test).
2. `POST /demo/seed` — with bearer token from setup or login.

**Recommended for Azure demo:** keep `APP_ENV=dev` for the review window so `scripts/seed_demo.py` works:

```bash
# Backend must be up and migrations applied
cd backend
python scripts/seed_demo.py --url https://<backend-fqdn>
```

**`APP_ENV=production`:** `/demo/setup` returns 403; seed via authenticated admin (`POST /demo/seed`) after creating users through normal auth — not changed in this P0 pass.

Demo login after seed: `admin@onepilot.ai` / `Demo1234!` (or dev auth if `DEV_AUTH_ENABLED=true`).

---

## Provider Setup

| Provider | Notes |
|----------|--------|
| **OpenAI** | `OPENAI_API_KEY` for live LLM, embeddings, speech |
| **Serper** | `SERPER_API_KEY` for live web search; mock without key |
| **Gmail** | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` — server-side refresh; **no OAuth UI at runtime** if token already generated locally |
| **Calendar** | Same Google OAuth env; use workspace token script for Calendar scopes — see [google_workspace_oauth_setup.md](google_workspace_oauth_setup.md) |
| **LangSmith** | `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY` (secret), `LANGSMITH_PROJECT=onepilot-ai`, `LANGSMITH_ENDPOINT=https://api.smith.langchain.com` — live tracing when key + tracing enabled; otherwise local trace steps |

For review, Gmail/Calendar can stay tested **locally**; copy the same secrets into Azure for cloud parity.

---

## Smoke Test Checklist

- [ ] `GET /health` — status ok, expected provider flags
- [ ] `GET /providers` — Postgres, Qdrant, OpenAI as configured
- [ ] Frontend loads at public URL
- [ ] Login as demo user (`admin@onepilot.ai` / `Demo1234!`) or dev auth
- [ ] RAG prompt (knowledge / workspace)
- [ ] Serper prompt (web search intent)
- [ ] Gmail approval prompt (if OAuth configured)
- [ ] Calendar availability prompt (if OAuth configured)
- [ ] LangSmith: `/providers` shows LangSmith live; workspace chat creates a trace in project `onepilot-ai`
- [ ] Approvals page loads

---

## Shutdown Checklist

- [ ] Scale Container Apps to zero or delete apps
- [ ] Stop or delete PostgreSQL server if temporary
- [ ] Remove Qdrant Cloud cluster if created for demo
- [ ] Delete ACR images if no longer needed
- [ ] Delete the **resource group** if the entire demo was isolated
- [ ] Confirm no resources still billing in Azure Portal → Cost Management

---

## Related Docs

- [deployment.md](deployment.md) — Local Docker and environment reference
- [.env.azure.example](../.env.azure.example) — Placeholder env template
- [google_workspace_oauth_setup.md](google_workspace_oauth_setup.md) — OAuth token generation
