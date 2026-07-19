# Public Demo Deployment Checklist

Use this checklist before deploying or updating OnePilot AI for a **public portfolio demo**. This is a demo-capable platform — not a full production SaaS.

**Branches:** canonical `main`; live public track `deployment/public-demo` (should match `main` exactly).

---

## Pre-deploy (repository)

- [ ] All CI checks pass (`.github/workflows/ci.yml` on `main`)
- [ ] `deployment/public-demo` is fast-forwarded to `main` (empty diff)
- [ ] Local smoke test passes: `python scripts/smoke_test_public_demo.py --base-url http://localhost:8000`
- [ ] No `.env` files committed (only `.env.example` / `frontend/.env.local.example`)
- [ ] `DEV_AUTH_ENABLED=false` in production env
- [ ] Strong `JWT_SECRET` (≥ 32 random characters)
- [ ] `CORS_ORIGINS` lists your Vercel frontend URL (no wildcards)
- [ ] `PUBLIC_DEMO_ENABLED=true` for one-click demo entry
- [ ] `GMAIL_PROVIDER_MODE=mock` and `GOOGLE_CALENDAR_PROVIDER_MODE=mock`

---

## 1. Managed Postgres (required)

1. Create a PostgreSQL 16 instance (Railway recommended, or Render, Neon, Supabase).
2. Copy the connection string → `DATABASE_URL`.
3. Run migrations before serving traffic:
   ```bash
   cd backend && DATABASE_URL="<url>" alembic upgrade head
   ```
4. **One-click demo:** with `PUBLIC_DEMO_ENABLED=true`, seeding happens automatically on first **Try the demo** click via `POST /demo/start`.
5. **Manual seed (optional):** `python scripts/seed_demo.py` — prints demo email to terminal for local password sign-in testing.

---

## 2. Qdrant Cloud (optional)

Without Qdrant, vectors fall back to **in-memory** and are lost on restart. The public demo can run on deterministic/in-memory fallbacks.

1. Create a Qdrant Cloud cluster (or self-host).
2. Set `QDRANT_URL` and `QDRANT_API_KEY`.
3. Re-seed or re-upload knowledge after deploy so embeddings are indexed.

---

## 3. Managed Redis (strongly recommended)

Redis shares rate limits across backend workers. Without it, limits are per-process memory only.

1. Create a Redis instance (Railway recommended, or Render, Upstash).
2. Set `REDIS_URL=redis://...`
3. After deploy, verify `/health` shows `rate_limit_backend: redis`.

---

## 4. Backend (Railway)

1. Deploy from `backend/Dockerfile`; set source branch to **`deployment/public-demo`**.
2. Set minimum production env vars:

| Variable | Value |
|----------|-------|
| `APP_ENV` | `production` |
| `DATABASE_URL` | Managed Postgres URL |
| `JWT_SECRET` | Strong random secret (≥ 32 chars) |
| `DEV_AUTH_ENABLED` | `false` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` |
| `REDIS_URL` | Managed Redis URL (strongly recommended) |
| `QDRANT_URL` | Qdrant endpoint (optional) |
| `QDRANT_API_KEY` | If using Qdrant Cloud |
| `GMAIL_PROVIDER_MODE` | `mock` |
| `GOOGLE_CALENDAR_PROVIDER_MODE` | `mock` |
| `GMAIL_SEND_ENABLED` | `false` |
| `PUBLIC_DEMO_ENABLED` | `true` |
| `OPENAI_API_KEY` | Optional — set usage limits in OpenAI dashboard |

3. Expose port `8000` (or platform default).
4. Confirm `GET /health` returns `status: ok`.
5. Confirm `GET /providers` returns readable diagnostics (no secrets).

**Do not** connect personal Gmail or Calendar accounts to a public demo.

---

## 5. Frontend (Vercel)

1. Import repo; set root directory to `frontend/`.
2. Set in Vercel env:
   - `NEXT_PUBLIC_API_URL=https://your-backend.example.com`
3. Deploy. Redeploy after changing `NEXT_PUBLIC_API_URL` (baked at build time).
4. Add the Vercel URL to backend `CORS_ORIGINS`.
5. Confirm landing page (`/`) shows **Try the demo** and product overview.

---

## 6. OpenAI usage limits (if using live OpenAI)

- Set monthly spend cap in the OpenAI dashboard.
- Demo works without OpenAI (deterministic fallback LLM/embeddings).
- Speech transcription requires OpenAI when enabled.

---

## 7. Post-deploy smoke test

```bash
python scripts/smoke_test_public_demo.py --base-url https://your-backend.example.com
```

Then verify live one-click demo:

- [ ] Landing page loads
- [ ] **Try the demo** opens seeded workspace
- [ ] No credentials displayed on landing or login page

Expected critical checks:

- [ ] Health `status=ok`
- [ ] Provider diagnostics readable
- [ ] Gmail/Calendar in mock mode
- [ ] `rate_limit_backend` is `redis` when `REDIS_URL` is set (check `/health`)

---

## 8. Rollback if smoke test fails

1. **Do not announce** the demo URL until smoke test passes.
2. Revert the backend deployment to the last known-good image/release (or reset `deployment/public-demo` to previous commit).
3. Revert the Vercel deployment to the previous production build.
4. Verify `DEV_AUTH_ENABLED=false`, mock provider modes, and `CORS_ORIGINS` on the rolled-back backend.
5. Re-run the smoke test against the rolled-back backend URL.
6. Check backend logs for startup validation errors (JWT, CORS, DEV_AUTH, mock modes).
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

# Critical smoke test (no login required)
python scripts/smoke_test_public_demo.py --base-url http://localhost:8000
```

---

## Honest scope notes

| Component | Public demo status |
|-----------|-------------------|
| Auth (JWT) | Demo-ready; one-click demo + optional manual sign-in |
| Rate limiting | Redis-backed with memory fallback |
| Gmail / Calendar | **Mock** on public demo |
| HubSpot / Stripe / Twilio | **Mock** only |
| RAG / Qdrant | Live when configured; in-memory fallback without Qdrant |
| OpenAI | Optional; fallback without key |
| Landing page | Live with **Try the demo** CTA |

See [deployment.md](deployment.md), [security.md](security.md), and [limitations_roadmap.md](limitations_roadmap.md).
