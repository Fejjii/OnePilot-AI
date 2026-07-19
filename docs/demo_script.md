# Demo Script — OnePilot AI

**Duration:** 8–10 minutes (or use the 3-minute cut in [portfolio/demo_narration_3min.md](portfolio/demo_narration_3min.md))  
**Audience:** Recruiter, hiring manager, or technical reviewer  
**Live entry:** https://one-pilot-ai.vercel.app → **Try the demo** (no credentials)

---

## Honesty preamble (say this once)

On the **public demo**, Gmail and Calendar use **mock providers**. Approvals, RAG, leads, and audit flows are real. Agent memory persistence is **disabled** on the shared demo tenant so reviewers do not leak facts across sessions.

---

## Prerequisites (local optional)

```bash
docker compose up -d --build
docker compose run --rm migrate
docker compose run --rm seed
# Optional: PUBLIC_DEMO_ENABLED=true for one-click demo locally
```

Verify: `http://localhost:3000` and `http://localhost:8000/health`

---

## Guided walkthrough

### 1 — Try the demo (30 s)

Open https://one-pilot-ai.vercel.app.

**Show:** Landing hero, safety/HITL messaging, architecture/tech stack, **Try the demo** CTA. No credentials on screen.

**Say:** OnePilot is an AI operations workspace — grounded answers, workflows, and mandatory human approval before external actions.

**Action:** Click **Try the demo** → land in the seeded workspace.

---

### 2 — Guided workspace (45 s)

Open **AI Workspace** if not already there.

**Show:**

- Guided empty state (capabilities + human-approval note)
- Provider-status badges (Demo mode, Gmail simulated, Calendar simulated, retrieval availability)
- Suggested prompt chips

**Action:** Click a chip (e.g. business summary) or ask: `What can you do for me?`

**Say:** Chips submit real `POST /chat` requests — not canned UI strings.

---

### 3 — Knowledge search (60 s)

**Prompt:** `What services does NovaEdge Solutions offer and what integrations are supported?`

**Show:** Grounded answer with **citations** from seeded NovaEdge docs.

**Say:** Internal RAG only here — citations are document titles/sections from the company knowledge base. Weak evidence is called out instead of inventing facts.

**Optional:** Open **Knowledge** and run the same question via search/answer UI.

---

### 4 — Approvals path with simulated Gmail (90 s)

**Prompt:** `Draft and send an email to a high priority lead about NovaEdge automation services.`

**Explain:**

1. Agent drafts email content in-app
2. Gmail provider action requires **approval**
3. On public demo, Gmail is **simulated** after approve
4. Send remains disabled by default (`GMAIL_SEND_ENABLED=false`)

Open **Approvals** → inspect payload/risk → **Approve** one item → note execution metadata / audit trail.

---

### 5 — Simulated Calendar (60 s)

**Prompt 1:** `Am I free Friday at 11 am?`  
**Prompt 2:** `Schedule a 30 minute meeting with a high priority lead next week.`

**Explain:** Availability/slots are mock on public demo (busy/free style — no private titles). Event creation creates an approval first; after approve, the mock calendar provider records the event.

---

### 6 — Leads / business insights (45 s)

Open **Dashboard** and **Leads**.

**Show:** Seeded pipeline (12 leads), usage snapshot, pending approvals, recent activity.

**Say:** The agent sits inside an ops surface — not a naked chat box.

---

### 7 — Memory behavior (45 s)

Open **Memory**.

**Show:** Memory UI (scopes, controls). Check status messaging for shared demo.

**Say (public demo):** Agent memory is **disabled** on the shared-demo tenant, and starting a new demo session **clears** prior memories so reviewers don’t inherit each other’s facts. Private tenants can use recall/persist in the LangGraph workflow.

---

### 8 — Mobile workspace (30 s)

Resize to a phone width or open on a phone.

**Show:** Bottom tabs (Chat / Approvals / Knowledge / Leads / More) and workspace **Chat | History | Details** segmented control with sticky composer.

**Say:** Same product flows; desktop keeps the three-column layout.

---

### 9 — Close on architecture & safety (45 s)

Open **Settings → provider diagnostics** (no secrets).

| Provider (public demo) | Expected |
|------------------------|----------|
| Gmail | **mock** |
| Google Calendar | **mock** |
| OpenAI | live or deterministic fallback |
| Serper | live or optional mock |
| Qdrant | live or in-memory fallback |
| Postgres / Redis | live on Railway |

**Close:** FastAPI + LangGraph + Postgres + Redis + Qdrant/fallback. Provider adapters. Tenant isolation. HITL before external side effects. Live on Vercel + Railway.

---

## Optional deeper prompts

| Goal | Prompt |
|------|--------|
| External web | `Find recent SMB automation trends.` |
| Hybrid | `Find recent SMB automation trends and compare them with NovaEdge Solutions services.` |
| Compound | `Find recent SMB automation trends, draft an email, and schedule a meeting with a high priority lead next week.` |

---

## Related docs

- [portfolio/demo_narration_3min.md](portfolio/demo_narration_3min.md) — timed narration
- [capabilities.md](capabilities.md) — live vs mocked matrix
- [safety_and_privacy.md](safety_and_privacy.md) — HITL and isolation
- [screenshots/README.md](screenshots/README.md) — capture list
