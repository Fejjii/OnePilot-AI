# Interview Cheat Sheet — OnePilot AI

Short spoken answers. Verify against the [README](../../README.md) and this repo if asked for depth.  
Public demo: [https://one-pilot-ai.vercel.app](https://one-pilot-ai.vercel.app). Runtime model: **`gpt-5-nano`**.

Do not claim live Gmail, live Calendar writes, enterprise certification, or a published accuracy SLO.

---

### What problem does OnePilot solve?

Small businesses split work across docs, inbox drafts, calendars, and leads. A chatbot answers text; it does not retrieve company knowledge, rank CRM context, and stop for a human before an external action. OnePilot is that operations loop.

### Why Agentic AI rather than a single LLM call?

One call cannot safely choose tools, ground a draft in CRM facts, search a tenant KB, and create an approval. I needed routing, a tool registry, and a hard stop before provider execution. That is a graph, not a prompt.

### Why LangGraph?

I wanted an explicit state machine: safety → classify → route → tools → synthesize → approve. LangGraph keeps those nodes inspectable and testable. I am not hiding a pile of if/else inside one completion.

### How does routing work?

Two stages. Stage 1 buckets the message — knowledge, workflow, chat, out of scope. Stage 2 picks the intent and tools. Calendar then splits again: list meetings vs availability vs create event. Meta questions should not accidentally fire Gmail.

### How does the RAG pipeline work?

Upload or seed → section-aware chunk → embed with `text-embedding-3-small` → store in Postgres + Qdrant → embed the query → tenant-filtered retrieve → generate only if evidence is strong → cite title/section.

### How do you reduce hallucinations?

Citations are required for knowledge answers. Weak retrieval (score below 0.30) skips the LLM. Email drafts resolve org-scoped leads and must not invent customer facts. Internal KB and Serper evidence stay labeled separately. I still do not claim zero hallucination.

### How do approvals work?

Gated actions write an `ApprovalRequest` in Postgres. Owner/Admin decide. Rejected items are not retried. After approve, the adapter runs. On the public demo that adapter is mock Gmail/Calendar. Drafting text is allowed; sending is not autonomous.

### How is multi-tenancy enforced?

`organization_id` on tenant models. Repositories filter every read/write. `ensure_same_org()` at the service layer. Qdrant uses `documents_{organization_id}` plus a payload filter. The JWT principal carries the org. The public demo is one shared org — that is a product choice, not a leak between private tenants.

### Why Qdrant?

I needed a real vector store with per-tenant collections, payload filters, and deterministic point IDs for idempotent upserts. In-memory fallback exists for tests and local demos. Public demo retrieval is Qdrant.

### Why Redis?

Shared rate limits and light cache across Railway workers. Without Redis, limits fall back to in-process memory and reset on restart. Auth itself is still JWT, not Redis sessions.

### How do you evaluate the system?

Offline suites: two-stage routing labels, RAG golden cases, safety/HITL policy. Reports land on the Evaluation page. Small labeled set, keyword RAG checks in CI — not RAGAS, not a production quality gate. Backend/frontend tests run on every `main` PR.

### How do you control LLM cost?

Public demo uses `gpt-5-nano`. Weak-evidence RAG does not call the chat model. Quotas and a daily token budget wrap the shared demo. Usage events record tokens. Fallbacks exist so CI does not need paid keys.

### What happens when a provider fails?

Adapters have live / mock / deterministic fallback. OpenAI timeouts retry, then fall back and set `fallback_used`. Forced Calendar mock is reported as healthy simulated mode, not an outage. A failed approval create does not execute the side effect.

### What is real vs mocked?

Real on the public URL: `gpt-5-nano`, embeddings, Qdrant, Postgres, Redis, Serper, routing, CRM ranking, citations, traces, HITL records. Simulated: Gmail, Calendar writes, Stripe/HubSpot/Twilio. Disabled: speech, shared-demo agent memory persist.

### What are the current limitations?

JWT in `localStorage`. No streaming. No object storage for original uploads. No background workers. Public Google is mock. Not Kubernetes, not SSO, not a billed multi-tenant SaaS. Evaluation sets are small.

### What would you change for enterprise production?

HTTP-only cookies and refresh tokens. Streaming. Object storage. A real job queue. Private-tenant live Google behind OAuth, still approval-gated. Stronger eval (RAGAS / human review). Tighter shared-demo isolation or single-tenant preview orgs. That is hardening, not a rewrite of the loop.

### What part did you personally engineer?

This is end-to-end work I designed and implemented: architecture, LangGraph orchestration, RAG, FastAPI services, Postgres/Redis/Qdrant, Next.js workspace, HITL, offline evaluation, tenant/RBAC/redaction controls, Vercel/Railway deploy, and CI. It is a portfolio-grade product, not a company production deployment with a team behind it.
