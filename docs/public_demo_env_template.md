# Public Demo Environment Template

Placeholder values only. **Do not commit real secrets.** Copy into your hosting provider's secret manager or env UI — never into git.

For step-by-step setup, see [public_demo_deployment_steps.md](public_demo_deployment_steps.md).

---

## Backend (Railway / Render / Azure Container Apps)

Set these on the backend service. Replace `<PLACEHOLDER>` values before deploy.

```bash
# ── Required ─────────────────────────────────────────────
APP_ENV=production
APP_NAME=OnePilot AI

DATABASE_URL=postgresql+psycopg://<USER>:<PASSWORD>@<HOST>:5432/<DB_NAME>

JWT_SECRET=<GENERATE_32_PLUS_CHAR_RANDOM_SECRET>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

DEV_AUTH_ENABLED=false

CORS_ORIGINS=https://<YOUR_VERCEL_APP>.vercel.app

# ── Strongly recommended (public demo) ─────────────────
REDIS_URL=redis://<USER>:<PASSWORD>@<REDIS_HOST>:6379/0

QDRANT_URL=https://<YOUR_CLUSTER>.cloud.qdrant.io
QDRANT_API_KEY=<QDRANT_CLOUD_API_KEY>

# ── Public demo: keep integrations in mock mode ──────────
GMAIL_PROVIDER_MODE=mock
GOOGLE_CALENDAR_PROVIDER_MODE=mock
GMAIL_SEND_ENABLED=false

# ── One-click demo access (OP-006) ───────────────────────
# Enables POST /demo/start: reviewers enter a seeded demo workspace
# without credentials. In production this REQUIRES the mock provider
# modes above — the backend refuses to start otherwise.
PUBLIC_DEMO_ENABLED=true
PUBLIC_DEMO_SESSION_MINUTES=60

# Leave Google OAuth empty for public demo (mock providers)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=

# ── Optional ─────────────────────────────────────────────
OPENAI_API_KEY=<OPENAI_API_KEY_OPTIONAL>
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

SERPER_API_KEY=
LANGSMITH_API_KEY=
LANGSMITH_TRACING=false
```

### Notes

| Variable | Public demo guidance |
|----------|---------------------|
| `JWT_SECRET` | Generate with `openssl rand -hex 32` or your password manager. Must be ≥ 32 characters. Never use `change-me-in-production`. |
| `CORS_ORIGINS` | Exact Vercel URL, no wildcards. Add preview URLs only if you need preview deployments. |
| `DEV_AUTH_ENABLED` | Must be `false`. Backend startup fails if `true` when `APP_ENV=production`. |
| `PUBLIC_DEMO_ENABLED` | Enables one-click demo entry (`POST /demo/start`, rate limited 10/hour/IP). With `APP_ENV=production`, startup fails unless `GMAIL_PROVIDER_MODE=mock`, `GOOGLE_CALENDAR_PROVIDER_MODE=mock`, and `GMAIL_SEND_ENABLED=false`. |
| `PUBLIC_DEMO_SESSION_MINUTES` | Lifetime of tokens issued by `/demo/start` (default 60). Expired demo sessions return 401 and the UI falls back to the login page. |
| `GMAIL_PROVIDER_MODE` | Use `mock` — do not connect personal Gmail. |
| `GOOGLE_CALENDAR_PROVIDER_MODE` | Use `mock` — do not connect personal Calendar. |
| `OPENAI_API_KEY` | Optional. App uses deterministic fallback without it. Set spend limits in OpenAI dashboard if enabled. |
| `REDIS_URL` | Strongly recommended so rate limits are shared across workers. Verify `/health` shows `rate_limit_backend: redis`. |
| `QDRANT_URL` | Strongly recommended for durable RAG. Without it, vectors are in-memory and lost on restart. |

---

## Frontend (Vercel)

Set in Vercel project → Settings → Environment Variables. `NEXT_PUBLIC_API_URL` is baked in at **build time** — redeploy after changing it.

```bash
NEXT_PUBLIC_API_URL=https://<YOUR_BACKEND_HOST>.up.railway.app
```

Example placeholder URLs (replace with your actual hosts):

| Service | Example placeholder |
|---------|---------------------|
| Vercel frontend | `https://onepilot-demo.vercel.app` |
| Railway backend | `https://onepilot-api.up.railway.app` |
| Render backend | `https://onepilot-api.onrender.com` |

---

## CORS pairing

Backend `CORS_ORIGINS` must include the exact frontend origin:

```bash
# If Vercel URL is https://onepilot-demo.vercel.app
CORS_ORIGINS=https://onepilot-demo.vercel.app
```

---

## Post-deploy verification

```bash
curl -s https://<YOUR_BACKEND_HOST>/health
curl -s https://<YOUR_BACKEND_HOST>/providers

# Critical checks (no login required)
python scripts/smoke_test_public_demo.py --base-url https://<YOUR_BACKEND_HOST>
```

Verify the live landing page: open your Vercel URL, click **Try the demo**, and confirm the workspace loads with seeded documents, leads, and approvals. No credentials should be displayed.

See [deployment_checklist.md](deployment_checklist.md) for the full checklist.
