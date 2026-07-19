# Public Demo Deployment Steps

Ordered guide for deploying OnePilot AI as a **public portfolio demo**. Uses placeholder URLs only — no real secrets.

**Canonical branch:** `main`  
**Public deployment branch:** `deployment/public-demo` (fast-forwarded to match `main`; no code divergence)  
**Live stack:** frontend on **Vercel**, backend on **Railway** (Postgres + Redis attached)

**Do not deploy until:** managed services are provisioned, env vars are set in hosting UIs, migrations run, and the post-deploy smoke test passes.

Related docs:

- [deployment_checklist.md](deployment_checklist.md) — pre/post deploy checklist
- [public_demo_env_template.md](public_demo_env_template.md) — env var template with placeholders
- [deployment.md](deployment.md) — full deployment reference

---

## Architecture overview

| Layer | Host | Purpose |
|-------|------|---------|
| Frontend | **Vercel** | Next.js app (landing page, authenticated workspace) |
| Backend | **Railway** | FastAPI container (`backend/Dockerfile`) |
| Postgres | Railway (attached) | Primary database |
| Redis | Railway (attached) | Shared rate limiting |
| Qdrant | Qdrant Cloud (optional) | Persistent vector search; in-memory fallback if unset |
| OpenAI | OpenAI dashboard (optional) | Optional; set spend cap if used |

**Public demo behavior:** Gmail and Calendar stay in **mock mode**. Reviewers use **Try the demo** on the landing page — no credentials required. `POST /demo/start` seeds the demo org and issues a short-lived session token (rate limited).

---

## Phase 0: Prerequisites

- [ ] `main` CI is green (backend tests + frontend checks)
- [ ] `deployment/public-demo` is fast-forwarded to the same commit as `main`
- [ ] Local smoke test passed against Docker stack (optional but recommended)
- [ ] OpenAI spend cap configured if using `OPENAI_API_KEY`

---

## Phase 1: Managed Postgres (required)

1. Create PostgreSQL 16 on Railway (recommended for public demo), Render, Neon, or Supabase.
2. Copy connection string → `DATABASE_URL` (backend env).
3. Run migrations **before** serving traffic:

   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://<USER>:<PASSWORD>@<HOST>:5432/<DB>" \
     alembic upgrade head
   ```

4. **One-click demo (recommended):** set `PUBLIC_DEMO_ENABLED=true` on the backend. The first **Try the demo** click calls `POST /demo/start`, which idempotently seeds the demo org and issues a short-lived token — no credentials shown or required.

5. **Manual seed (optional, local or admin):** run `python scripts/seed_demo.py` when you need a persistent demo user for password-based sign-in testing. The script prints the demo email to the terminal.

---

## Phase 2: Qdrant Cloud (optional)

Without Qdrant, embeddings fall back to in-memory storage and are lost on restart. The public demo currently runs with deterministic/in-memory fallbacks when Qdrant is unset.

1. Create a cluster at [Qdrant Cloud](https://cloud.qdrant.io).
2. Set backend env:
   - `QDRANT_URL=https://<CLUSTER>.cloud.qdrant.io`
   - `QDRANT_API_KEY=<API_KEY>`
3. After deploy, re-seed or re-upload knowledge so vectors are indexed.

---

## Phase 3: Managed Redis (strongly recommended)

Redis shares rate limits across backend workers. Without it, limits are per-process only.

1. Create Redis on Railway (recommended), Render, or Upstash.
2. Set `REDIS_URL=redis://<USER>:<PASSWORD>@<HOST>:6379/0`
3. After deploy, confirm `/health` reports `rate_limit_backend: redis`.

---

## Phase 4: Backend (Railway)

### Railway setup

1. New project → Deploy from GitHub repo `Fejjii/OnePilot-AI`.
2. Set deploy branch to **`deployment/public-demo`**.
3. Set root directory / Dockerfile path to `backend/Dockerfile`.
4. Add env vars from [public_demo_env_template.md](public_demo_env_template.md).
5. Attach managed Postgres and Redis (or paste external URLs).
6. Expose port `8000`.
7. Deploy and verify:

   ```bash
   curl https://<YOUR_BACKEND>.up.railway.app/health
   ```

### Render (alternative)

1. New Web Service → connect repo, branch **`deployment/public-demo`**.
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
| `GMAIL_SEND_ENABLED` | `false` |
| `PUBLIC_DEMO_ENABLED` | `true` (enables one-click demo) |

---

## Phase 5: Frontend (Vercel)

1. Import GitHub repo → set **Root Directory** to `frontend/`.
2. Framework preset: Next.js.
3. Set environment variable:
   - `NEXT_PUBLIC_API_URL=https://<YOUR_BACKEND_HOST>`
4. Deploy. Note the Vercel URL (e.g. `https://your-app.vercel.app`).
5. Add that URL to backend `CORS_ORIGINS` and redeploy backend if needed.
6. Redeploy Vercel whenever `NEXT_PUBLIC_API_URL` changes (build-time variable).

The root URL (`/`) serves the public landing page with **Try the demo**, product capabilities, safety model, and architecture overview.

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
# Critical checks (health, providers) — no login required
python scripts/smoke_test_public_demo.py --base-url https://<YOUR_BACKEND_HOST>
```

Then verify the live experience manually:

- [ ] Landing page loads; **Try the demo** is visible
- [ ] One-click demo opens a seeded workspace (documents, leads, approvals)
- [ ] Gmail and Calendar show mock/simulated behavior
- [ ] No credentials are displayed on the landing or login page

Optional authenticated smoke (after local seed only):

```bash
python scripts/smoke_test_public_demo.py \
  --base-url https://<YOUR_BACKEND_HOST> \
  --demo-email <EMAIL_FROM_SEED_SCRIPT> \
  --demo-password <PASSWORD_FROM_SEED_SCRIPT>
```

Expected critical checks:

- Health `status=ok`
- Provider diagnostics readable (no secrets leaked)
- Gmail/Calendar in mock mode

Optional: confirm `rate_limit_backend` is `redis` when Redis is configured:

```bash
curl -s https://<YOUR_BACKEND_HOST>/health | jq '.providers.rate_limit_backend'
```

---

## Phase 8: Announce only after green smoke test

- [ ] Smoke test passed
- [ ] One-click demo verified on the live landing page
- [ ] `DEV_AUTH_ENABLED=false` confirmed on backend
- [ ] CORS allows Vercel origin only
- [ ] Gmail/Calendar in mock mode
- [ ] OpenAI spend cap set (if using live OpenAI)

Do **not** share the public URL until all checks pass.

---

## Rollback

If smoke test fails:

1. Revert backend to last known-good release/image (or fast-forward `deployment/public-demo` to previous commit).
2. Revert Vercel to previous production deployment.
3. Re-run smoke test against rolled-back backend URL.
4. Check backend logs for startup validation errors (JWT, CORS, `DEV_AUTH_ENABLED`, mock provider modes).

See [deployment_checklist.md](deployment_checklist.md) § Rollback.

---

## What this deployment is (and is not)

| In scope | Out of scope |
|----------|--------------|
| Public demo for portfolio / recruiter review | Full production SaaS |
| One-click demo via **Try the demo** | Refresh tokens / SSO |
| JWT auth with shared demo tenant | Per-visitor isolated orgs |
| Redis rate limiting | WAF / DDoS protection |
| Mock Gmail/Calendar on public demo | Live personal Google accounts |
| Qdrant-backed RAG when configured | Multi-region HA |

See [limitations_roadmap.md](limitations_roadmap.md) for known gaps.
