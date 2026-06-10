# Public Demo Deployment Checklist

Use this checklist before deploying OnePilot AI for a **public LinkedIn demo**. This is a demo-capable capstone app — not a full production SaaS.

---

## Pre-deploy (repository)

- [ ] All CI checks pass (`.github/workflows/ci.yml`)
- [ ] Local smoke test passes: `python scripts/smoke_test_public_demo.py --base-url http://localhost:8000 --demo-email admin@onepilot.ai --demo-password Demo1234!`
- [ ] No `.env` files committed (only `.env.example` / `frontend/.env.local.example`)
- [ ] `DEV_AUTH_ENABLED=false` in production env
- [ ] Strong `JWT_SECRET` (≥ 32 random characters)
- [ ] `CORS_ORIGINS` lists your Vercel frontend URL (no wildcards)

---

## 1. Managed Postgres (required)

1. Create a PostgreSQL 16 instance (Railway, Render, Neon, Supabase, etc.).
2. Copy the connection string → `DATABASE_URL`.
3. Run migrations before serving traffic:
   ```bash
   cd backend && DATABASE_URL="<url>" alembic upgrade head
   ```
4. Seed demo data (optional for public demo):
   ```bash
   cd backend && python scripts/seed_demo.py
   ```
   Creates `admin@onepilot.ai` / `Demo1234!` when the org is empty.

---

## 2. Qdrant Cloud (strongly recommended)

Without Qdrant, vectors fall back to **in-memory** and are lost on restart.

1. Create a Qdrant Cloud cluster (or self-host).
2. Set `QDRANT_URL` and `QDRANT_API_KEY`.
3. Re-seed or re-upload knowledge after deploy so embeddings are indexed.

---

## 3. Managed Redis (strongly recommended)

Redis shares rate limits across backend workers. Without it, limits are per-process memory only.

1. Create a Redis instance (Railway, Render, Upstash, etc.).
2. Set `REDIS_URL=redis://...`
3. After deploy, verify `/health` shows `rate_limit_backend: redis`.

---

## 4. Backend (Railway or Render)

1. Deploy from `backend/Dockerfile` (or connect the repo with root `backend/`).
2. Set minimum production env vars:

| Variable | Value |
|----------|-------|
| `APP_ENV` | `production` |
| `DATABASE_URL` | Managed Postgres URL |
| `JWT_SECRET` | Strong random secret (≥ 32 chars) |
| `DEV_AUTH_ENABLED` | `false` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` |
| `REDIS_URL` | Managed Redis URL (strongly recommended) |
| `QDRANT_URL` | Qdrant endpoint (strongly recommended) |
| `QDRANT_API_KEY` | If using Qdrant Cloud |
| `GMAIL_PROVIDER_MODE` | `mock` |
| `GOOGLE_CALENDAR_PROVIDER_MODE` | `mock` |
| `OPENAI_API_KEY` | Optional — set usage limits in OpenAI dashboard |

3. Expose port `8000` (or platform default).
4. Confirm `GET /health` returns `status: ok`.
5. Confirm `GET /providers` returns readable diagnostics (no secrets).

**Do not** connect personal Gmail or Calendar accounts to a public demo.

---

## 5. Frontend (Vercel)

1. Import repo; set root directory to `frontend/`.
2. Copy `frontend/.env.local.example` → set in Vercel env:
   - `NEXT_PUBLIC_API_URL=https://your-backend.example.com`
3. Deploy. Redeploy after changing `NEXT_PUBLIC_API_URL` (baked at build time).
4. Add the Vercel URL to backend `CORS_ORIGINS`.

---

## 6. OpenAI usage limits (if using live OpenAI)

- Set monthly spend cap in the OpenAI dashboard.
- Demo works without OpenAI (deterministic fallback LLM/embeddings).
- Speech transcription requires OpenAI when enabled.

---

## 7. Post-deploy smoke test

```bash
python scripts/smoke_test_public_demo.py \
  --base-url https://your-backend.example.com \
  --demo-email admin@onepilot.ai \
  --demo-password Demo1234!
```

Expected critical checks:

- [ ] Health `status=ok`
- [ ] Provider diagnostics readable
- [ ] Login succeeds (if demo user seeded)
- [ ] Benign chat returns a response
- [ ] Prompt injection blocked or refused
- [ ] Knowledge search returns results
- [ ] `rate_limit_backend` is `redis` when `REDIS_URL` is set (check `/health`)

---

## 8. Rollback if smoke test fails

1. **Do not announce** the demo URL until smoke test passes.
2. Revert the backend deployment to the last known-good image/release.
3. Revert the Vercel deployment to the previous production build.
4. Verify `DEV_AUTH_ENABLED=false` and `CORS_ORIGINS` on the rolled-back backend.
5. Re-run the smoke test against the rolled-back backend URL.
6. Check backend logs for startup validation errors (JWT, CORS, DEV_AUTH).
7. If database migration caused failure, restore Postgres snapshot and redeploy previous backend tag.

---

## Local Docker smoke test (pre-deploy validation)

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose run --rm migrate
docker compose run --rm seed

# Verify stack
curl http://localhost:8000/health
curl http://localhost:3000

# Confirm Redis-backed rate limiting (after rebuild with latest code)
curl -s http://localhost:8000/health | jq '.providers.rate_limit_backend'
# Expected: "redis"

# Full smoke test
python scripts/smoke_test_public_demo.py \
  --base-url http://localhost:8000 \
  --demo-email admin@onepilot.ai \
  --demo-password Demo1234!
```

---

## Honest scope notes

| Component | Public demo status |
|-----------|-------------------|
| Auth (JWT) | Demo-ready; no refresh tokens |
| Rate limiting | Redis-backed with memory fallback |
| Gmail / Calendar | **Mock** recommended for public demo |
| HubSpot / Stripe / Twilio | **Mock** only |
| RAG / Qdrant | Live when configured; in-memory fallback without Qdrant |
| OpenAI | Optional; fallback without key |

See [deployment.md](deployment.md), [security.md](security.md), and [limitations_roadmap.md](limitations_roadmap.md).
