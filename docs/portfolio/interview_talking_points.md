# Technical Interview Talking Points

Keep each point to ~30–60 seconds. Verify against code if asked for depth.

## 1. Why this architecture

- Layered FastAPI: routers → services → repositories → providers
- Thin routers, business logic in services, tenant scoping in repositories
- Provider adapters with mock/live/fallback so demos and CI never depend on live SaaS

## 2. Agent orchestration

- LangGraph workflow with two-stage routing (message class → intent)
- Tools registered centrally; external side effects create approval requests instead of executing
- Structured responses with citations and tool traces for explainability

## 3. RAG that fails closed

- Ingest → chunk → embed → retrieve → answer with citations
- Confidence / weak-evidence path when retrieval is thin
- Internal KB citations kept separate from Serper web evidence

## 4. Human-in-the-loop safety

- `GATED_ACTION_TYPES` for email, calendar, CRM-style actions
- Owner/Admin approval only; audit on decide + execute
- Public demo: mock Gmail/Calendar + send disabled — approval UX still exercises the real path

## 5. Multi-tenant isolation

- `organization_id` on tenant models; repository filters everywhere
- Per-org vector collections
- Shared public-demo org is intentional for reviewers; agent memory disabled there (ADR 007)

## 6. Memory design (OP-012)

- Recall before generation; bounded, relevance-ranked
- Persist only explicit durable facts; reject secret-like content
- Shared-demo clears memories on `/demo/start` to prevent cross-reviewer leakage

## 7. Frontend product craft

- Landing + one-click demo entry for recruiters
- Guided workspace chips, provider badges, recoverable errors
- Mobile bottom nav + workspace panel tabs without breaking desktop three-column layout

## 8. Testing & evaluation honesty

- Backend pytest + frontend Vitest in CI on `main` and `deployment/**`
- Deterministic offline evaluation (routing / RAG / safety) — not a substitute for production RAGAS
- Prefer stating verified counts from the latest green CI run

## 9. What you’d improve next

- HTTP-only cookie auth + refresh tokens
- Streaming responses
- Object storage for uploads
- Background workers for long jobs
- Real Stripe / HubSpot when productizing beyond portfolio demo

## Questions to invite

- “How do you keep mock and live providers from forking business logic?”
- “Where does tenant isolation actually get enforced?”
- “What happens if someone tries to skip approval via prompt injection?”
