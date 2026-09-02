# Public demo — enable managed AI providers (OP-022)

This is a **user-gated** host configuration step. Application code is ready; keys must be set only on the Railway backend, never on Vercel.

## Prerequisites

1. Merge OP-015 (routing), OP-016 (OpenAI client hardening), and OP-017 (abuse/spend controls) to `main`, then fast-forward `deployment/public-demo` (explicit approval).
2. Create or select an OpenAI project and set a **hard monthly spend limit** (recommend USD 10).
3. Confirm remaining Serper free-tier credits in the Serper dashboard.

## Backend env (Railway, `deployment/public-demo`)

Set **variable names only** — never commit values:

```bash
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_RETRIES=2
OPENAI_MAX_OUTPUT_TOKENS=1024
SERPER_API_KEY=<secret>
QDRANT_URL=
PUBLIC_DEMO_WARM_REINDEX=true
PUBLIC_DEMO_CHAT_PER_IP_PER_MINUTE=20
PUBLIC_DEMO_CHAT_PER_IP_PER_DAY=200
PUBLIC_DEMO_WEB_SEARCH_PER_IP_PER_MINUTE=5
PUBLIC_DEMO_WEB_SEARCH_PER_DAY=300
PUBLIC_DEMO_DAILY_TOKEN_BUDGET=250000
```

Keep `GMAIL_PROVIDER_MODE=mock`, `GOOGLE_CALENDAR_PROVIDER_MODE=mock`, `GMAIL_SEND_ENABLED=false`.

Redeploy the Railway service after saving env vars so provider singletons re-initialize.

## Verify

```bash
curl -s https://onepilot-ai-production.up.railway.app/providers
python scripts/smoke_test_public_demo.py --base-url https://onepilot-ai-production.up.railway.app
```

`/providers` should show OpenAI LLM and embeddings `live` (or `fallback` if the key is invalid), Serper `live`, Gmail/Calendar `mock`. Then click **Try the demo** and run the six workspace chips.

## Rollback

Unset `OPENAI_API_KEY` and `SERPER_API_KEY` on Railway and redeploy. Deterministic fallbacks resume immediately.
