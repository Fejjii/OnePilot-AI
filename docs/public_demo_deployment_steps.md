# Public Demo Deployment Steps

Ordered guide for deploying OnePilot AI as a **public LinkedIn demo**. Uses placeholder URLs only — no real secrets.

**Branch:** `deployment/public_demo` (cut from green `master` CI checkpoint)

**Do not deploy until:** managed services are provisioned, env vars are set in hosting UIs, migrations run, and the post-deploy smoke test passes.

Related docs:

- [deployment_checklist.md](deployment_checklist.md) — pre/post deploy checklist
- [public_demo_env_template.md](public_demo_env_template.md) — env var template with placeholders
- [deployment.md](deployment.md) — full deployment reference

---

## Architecture overview

| Layer | Recommended host | Purpose |
|-------|------------------|---------|
| Frontend | **Vercel** | Next.js static/SSR app |
| Backend | **Railway** or **Render** | FastAPI container (`backend/Dockerfile`) |
| Postgres | Railway / Render / Neon / Supabase | Primary database |
| Redis | Railway / Render / Upstash | Shared rate limiting |
| Qdrant | **Qdrant Cloud** | Persistent vector search |
| OpenAI | OpenAI dashboard | Optional; set spend cap if used |

Gmail and Calendar stay in **mock mode** for public demo. Do not connect personal Google accounts.

---

## Phase 0: Prerequisites

- [ ] `master` CI is green (backend tests + frontend checks)
- [ ] You are deploying from `deployment/public_demo` or latest `master`
- [ ] Local smoke test passed against Docker stack (optional but recommended)
- [ ] OpenAI spend cap configured if using `OPENAI_API_KEY`

---

## Phase 1: Managed Postgres (required)

1. Create PostgreSQL 16 on Railway, Render, Neon, or Supabase.
2. Copy connection string → `DATABASE_URL` (backend env).
3. Run migrations **before** serving traffic:

   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://<USER>:<PASSWORD>@<HOST>:5432/<DB>" \
     alembic upgrade head
   ```

4. Seed demo user (optional but recommended for login demo):

   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://..." python scripts/seed_demo.py
   ```

   Creates `admin@onepilot.ai` / `Demo1234!` when the org is empty.

   With `PUBLIC_DEMO_ENABLED=true` this manual step is optional: the first
   click on **Try the demo** calls `POST /demo/start`, which idempotently
   seeds the same demo org and issues a short-lived session token — no
   credentials shown or required.

---

## Phase 2: Qdrant Cloud (strongly recommended)

Without Qdrant, embeddings fall back to in-memory storage and are lost on restart.

1. Create a cluster at [Qdrant Cloud](https://cloud.qdrant.io).
2. Set backend env:
   - `QDRANT_URL=https://<CLUSTER>.cloud.qdrant.io`
   - `QDRANT_API_KEY=<API_KEY>`
3. After deploy, re-seed or re-upload knowledge so vectors are indexed.

---

## Phase 3: Managed Redis (strongly recommended)

Redis shares rate limits across backend workers. Without it, limits are per-process only.

1. Create Redis on Railway, Render, or Upstash.
2. Set `REDIS_URL=redis://<USER>:<PASSWORD>@<HOST>:6379/0`
3. After deploy, confirm `/health` reports `rate_limit_backend: redis`.

---

## Phase 4: Backend (Railway or Render)

### Railway

1. New project → Deploy from GitHub repo `Fejjii/OnePilot-AI`.
2. Set root directory / Dockerfile path to `backend/Dockerfile`.
3. Add env vars from [public_demo_env_template.md](public_demo_env_template.md).
4. Attach managed Postgres and Redis (or paste external URLs).
5. Expose port `8000`.
6. Deploy and verify:

   ```bash
   curl https://<YOUR_BACKEND>.up.railway.app/health
   ```

### Render

1. New Web Service → connect repo, branch `deployment/public_demo`.
2. Root directory: `backend/`
3. Docker or native Python build from `backend/Dockerfile`.
4. Set env vars (same template as above).
5. Expose port `8000`, enable health check path `/health`.

### Required production env (minimum)

| Variable | Value |
|----------|-------|
| `APP_ENV` | `production` |
| `DATABASE_URL` | Managed Postgres URL |
| `JWT_SECRET` | ≥ 32 char random secret |
| `DEV_AUTH_ENABLED` | `false` |
| `CORS_ORIGINS` | `https://<YOUR_VERCEL_APP>.vercel.app` |
| `GMAIL_PROVIDER_MODE` | `mock` |
| `GOOGLE_CALENDAR_PROVIDER_MODE` | `mock` |

---

## Phase 5: Frontend (Vercel)

1. Import GitHub repo → set **Root Directory** to `frontend/`.
2. Framework preset: Next.js.
3. Set environment variable:
   - `NEXT_PUBLIC_API_URL=https://<YOUR_BACKEND_HOST>`
4. Deploy. Note the Vercel URL (e.g. `https://onepilot-demo.vercel.app`).
5. Add that URL to backend `CORS_ORIGINS` and redeploy backend if needed.
6. Redeploy Vercel whenever `NEXT_PUBLIC_API_URL` changes (build-time variable).

---

## Phase 6: OpenAI usage limits (optional)

If you set `OPENAI_API_KEY`:

1. Open [OpenAI usage limits](https://platform.openai.com/settings/organization/limits).
2. Set a monthly spend cap appropriate for demo traffic.
3. Monitor usage during the demo window.

The app runs without OpenAI using deterministic fallback LLM/embeddings. Speech transcription requires OpenAI when enabled.

---

## Phase 7: Post-deploy smoke test

Run from your machine (no secrets printed):

```bash
python scripts/smoke_test_public_demo.py \
  --base-url https://<YOUR_BACKEND_HOST> \
  --demo-email admin@onepilot.ai \
  --demo-password Demo1234!
```

Expected critical checks:

- Health `status=ok`
- Provider diagnostics readable (no secrets leaked)
- Login succeeds (if demo user seeded)
- Benign chat returns a response
- Prompt injection blocked or refused
- Knowledge search returns results

Optional: confirm `rate_limit_backend` is `redis` when Redis is configured:

```bash
curl -s https://<YOUR_BACKEND_HOST>/health | jq '.providers.rate_limit_backend'
```

---

## Phase 8: Announce only after green smoke test

- [ ] Smoke test passed
- [ ] `DEV_AUTH_ENABLED=false` confirmed on backend
- [ ] CORS allows Vercel origin only
- [ ] Gmail/Calendar in mock mode
- [ ] OpenAI spend cap set (if using live OpenAI)

Do **not** share the public URL until all checks pass.

---

## Rollback

If smoke test fails:

1. Revert backend to last known-good release/image.
2. Revert Vercel to previous production deployment.
3. Re-run smoke test against rolled-back backend URL.
4. Check backend logs for startup validation errors (JWT, CORS, `DEV_AUTH_ENABLED`).

See [deployment_checklist.md](deployment_checklist.md) § Rollback.

---

## What this deployment is (and is not)

| In scope | Out of scope |
|----------|--------------|
| Public demo for LinkedIn / portfolio | Full production SaaS |
| JWT auth with demo user | Refresh tokens / SSO |
| Redis rate limiting | WAF / DDoS protection |
| Mock Gmail/Calendar | Live personal Google accounts |
| Qdrant-backed RAG when configured | Multi-region HA |

See [limitations_roadmap.md](limitations_roadmap.md) for known gaps.
