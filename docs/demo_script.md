# Demo Script — OnePilot AI

**Duration:** 8–10 minutes  
**Audience:** Recruiter, hiring manager, or technical reviewer  
**Entry:** Open the public landing page and click **Try the demo** (no credentials required). For local Docker, use **Try the demo** with `PUBLIC_DEMO_ENABLED=true` or sign in after running the seed script.

---

## Prerequisites

```bash
docker compose down
docker compose up -d --build
docker compose run --rm migrate
docker compose run --rm seed
cd backend && uv run python -m onepilot.evaluation.run_all_evals
```

Verify: `http://localhost:3000` and `http://localhost:8000/health`

---

## Reviewer Story (13 steps)

### 0 — Landing page (30 s)

Open the root URL (`/`).

**Show:** Product overview, human-in-the-loop safety model, architecture/tech stack, and **Try the demo** CTA. No credentials displayed.

**Say:** OnePilot is an AI operations platform for small businesses — grounded answers, workflow automation, and mandatory human approval before any external action.

---

### 1 — Dashboard (30 s)

After **Try the demo**, open Dashboard.

**Show:** SaaS overview, live vs mock provider banner, usage summary, pending approvals, recent activity.

**Say:** One operational view for knowledge, pipeline, usage, and approval backlog.

---

### 2 — AI Workspace: general routing (30 s)

**Prompt:** `What can you do for me?`

**Explain:** Routes to **general assistant** — no RAG, no web search. Capability overview only.

---

### 3 — Internal RAG (45 s)

**Prompt:** `What services does NovaEdge Solutions offer and what integrations are supported?`

**Explain:** Internal company knowledge via retrieval. Citations from uploaded NovaEdge docs. Confidence and weak-evidence guardrail when evidence is thin.

---

### 4 — Serper live web search (45 s)

**Prompt:** `Find recent SMB automation trends.`

**Explain:** External web intelligence via Serper (`external.web_search`). **External web evidence** section with URL citations — separate from internal KB.

Settings → Serper shows **live** when `SERPER_API_KEY` is set.

---

### 5 — Hybrid internal plus external (60 s)

**Prompt:** `Find recent SMB automation trends and compare them with NovaEdge Solutions services.`

**Explain:** `web_and_knowledge` intent runs **both** Serper and RAG. Answer sections: **Internal company knowledge**, **External web evidence**, **Recommendation**.

---

### 6 — Gmail workflow (90 s)

**Prompt:** `Draft and send an email to a high priority lead about NovaEdge automation services.`

**Explain:**

- Agent generates draft in-app (`email.draft`) — no Gmail call yet
- **Approval required** before any Gmail action
- After approve on Approvals page → Gmail **draft** created (live or mock)
- **Send disabled for safety** — `GMAIL_SEND_ENABLED=false` by default
- On the **public demo**, Gmail is **simulated** (mock provider)

---

### 7 — Calendar workflow (90 s)

**Prompt 1:** `Am I free Friday at 11 am?`

**Explain:** Google Calendar across selected calendars (live when OAuth configured; **mock on public demo**). Busy/free only — **no private event titles** exposed in responses or diagnostics.

**Prompt 2:** `Suggest three meeting slots next week.`

**Explain:** Slot suggestion tool — no event created, no approval.

**Prompt 3:** `Schedule a 30 minute meeting with a high priority lead next week.`

**Explain:** Creates **approval request** only. Event appears in calendar **after** admin approves.

---

### 8 — Compound workflow (60 s)

**Prompt:** `Find recent SMB automation trends, draft an email, and schedule a meeting with a high priority lead next week.`

**Explain:** Multi-tool sequential workflow:

1. `external.web_search` — research
2. `email.draft` + Gmail approval
3. `calendar.create_event_request` + Calendar approval

No external side effects until approvals are granted.

---

### 9 — Approvals page (45 s)

Open **Approvals**.

**Show:** Pending Gmail and/or Calendar requests, proposed payload, risk level.

**Action:** Approve one item → execution metadata (draft id or event id) on detail view.

**Optional:** Reject or request more info.

---

### 10 — Usage and Admin (30 s)

Open **Usage & Admin**.

**Show:** Token counts, estimated costs, quota progress, invoice preview (mock Stripe), audit log entries.

**Say:** Full observability for cost control and compliance — estimates only, no real charges.

---

### 11 — Evaluation (30 s)

Open **Evaluation**.

**Show:** Deterministic offline eval results (routing, RAG golden set, safety/HITL).

**Say:** Regression gates for demo quality — not a substitute for production RAGAS or human eval.

---

### 12 — Settings / provider diagnostics (45 s)

Open **Settings**.

**Show provider diagnostics** (no secrets):

| Provider | Expected mode (public demo) |
|----------|----------------------------|
| OpenAI | fallback (no key) or live |
| Serper | optional or live |
| Gmail | **mock** |
| Google Calendar | **mock** |
| Qdrant | in-memory fallback or live |
| Redis | live (Railway) or in-memory |
| Postgres | live (required) |
| LangSmith | local or live |

**Close:** FastAPI + LangGraph + Postgres + Qdrant + Redis. Every external integration uses provider adapters. Multi-tenant isolation, audit logs, quotas, and mandatory HITL before Gmail drafts/events. Live public demo on Vercel + Railway with simulated Gmail/Calendar.

---

## Offline / no-key demo

- Without `OPENAI_API_KEY`: deterministic LLM fallback — routing and workflows still demonstrate
- Without `SERPER_API_KEY`: mock web results with clear optional mode label
- Without Google OAuth (public demo default): Gmail and Calendar use mock providers; approval flow unchanged
- Re-run seed safely: `docker compose run --rm seed` (idempotent)

---

## Related docs

- [architecture.md](architecture.md) — system and workflow diagrams
- [manual_test_checklist.md](manual_test_checklist.md) — pre-push validation
- [google_workspace_oauth_setup.md](google_workspace_oauth_setup.md) — Gmail + Calendar OAuth
