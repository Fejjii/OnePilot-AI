# Limitations & Roadmap

This document is an honest, professional assessment of the current state of OnePilot AI after all 8 capstone phases.

---

## What Is Mocked (Not Real)

| Component | Status | Notes |
|-----------|--------|-------|
| OpenAI LLM | Mock fallback available | Real provider activated by `OPENAI_API_KEY`. Fallback returns deterministic canned responses. |
| OpenAI Embeddings | Mock fallback available | Fallback uses token-hash embeddings — adequate for demos, not for production semantic quality. |
| Qdrant Vector DB | Mock fallback available | In-memory vector store used when `QDRANT_URL` is not set. Not persistent across restarts. |
| HubSpot CRM | Mocked | In-memory, deterministic. No real HubSpot API calls. |
| Gmail / Email send | Mocked | Email drafts stored in-memory. No actual emails sent. |
| Google Calendar | Mocked | In-memory event store. No real calendar integration. |
| Stripe Billing | Mocked | `MockStripeProvider` + billing-ready APIs; estimated usage costs; no real payment processing. |
| Serper Web Search | Mocked | Returns canned search results. No real HTTP calls. |

---

## Current Known Limitations

### Authentication & Session Management
1. **JWT stored in localStorage** — XSS vulnerability. Production should use HTTP-only cookies.
2. **No refresh tokens** — users must re-login after `JWT_EXPIRE_MINUTES` (default 60 min).
3. **No OAuth/SSO** — username/password only.
4. **DEV_AUTH_ENABLED** — must be explicitly set to `false` in production to avoid bypassing auth.

### AI & RAG Quality
5. **Fallback embeddings are low quality** — token-hash embeddings produce correct retrieval only for exact-ish keyword matches. Set `OPENAI_API_KEY` for real semantic similarity.
6. **No streaming** — chat responses are synchronous; long responses may feel slow.
7. **No real-time web search** — web search tool uses mock results without `SERPER_API_KEY`.
8. **Single-language** — English only. No multilingual support.

### Infrastructure
9. **In-memory rate limiting** — resets on backend restart. Not suitable for horizontally scaled deployments.
10. **No Redis session management** — sessions are stateless JWT only.
11. **No file persistence** — uploaded files are processed in-memory and then discarded. Chunks are stored in Postgres. The original files are not persisted to object storage.
12. **No background workers** — all processing is synchronous in the request/response cycle.
13. **No production deployment** — Docker Compose only. No Kubernetes, no cloud-native deployment.

### Billing & Plans
14. **No real billing** — usage cost estimation, invoice preview, and mock Stripe are implemented; live Stripe checkout/webhooks are not.
15. **Estimated prices** — token rates in `pricing_config.py` must be verified against provider list prices before production.
16. **Quota reset** — quotas reset on a calendar-month basis but require a cron job or background worker that is not currently implemented.

---

## What Is Production-Ready (Within Scope)

Despite the limitations above, the following components are designed and implemented to production-grade standards:

- **Multi-tenant data isolation** — every entity is scoped by `organization_id` and enforced at both repository and service layer
- **JWT authentication with RBAC** — proper role hierarchy, bcrypt passwords, configurable expiry
- **Prompt injection detection** — regex + keyword pattern matching with audit logging
- **Audit logging** — append-only audit trail for all sensitive actions
- **Usage event tracking** — per-org quota enforcement with real token counting
- **Provider adapter pattern** — every external dependency can be swapped without code changes
- **Approval gates** — no autonomous external actions without human approval
- **221 passing tests** — covering auth, tenancy, RAG, agent workflow, approvals, memory, and security
- **Ruff + mypy compliance** — clean linting and type checking

---

## Roadmap (Post-Capstone)

### Near-Term (1–3 months)
- [ ] HTTP-only cookie auth with refresh tokens
- [ ] Redis-backed rate limiting and session management
- [ ] Real OpenAI streaming (Server-Sent Events)
- [ ] Object storage for uploaded files (S3 / Cloudflare R2)
- [ ] Background task queue (Celery + Redis or ARQ)

### Medium-Term (3–6 months)
- [ ] OAuth 2.0 / SAML SSO integration
- [ ] Real Stripe billing with webhooks
- [ ] Real email delivery (SendGrid or Gmail API)
- [ ] Real HubSpot CRM integration
- [ ] Real Google Calendar integration
- [ ] IP-based rate limiting at the reverse proxy layer
- [ ] Content safety classification on LLM outputs (Moderation API)

### Long-Term
- [ ] WebSocket / SSE streaming chat
- [ ] Kubernetes deployment manifests
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Multi-language support
- [ ] Advanced analytics dashboards (token cost, latency heatmaps)
- [ ] RAGAS-style automated RAG evaluation
- [ ] Fine-tuned intent classifier replacing the LLM classifier
- [ ] Twilio voice integration
- [ ] Enterprise audit log export (SIEM integration)
