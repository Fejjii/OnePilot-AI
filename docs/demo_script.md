# Demo Script — OnePilot AI

**Duration:** 5–7 minutes  
**Format:** SCR (Situation · Complication · Resolution)

---

## Narrative Frame

**Situation**  
Small businesses use many disconnected AI tools and lose time managing scattered knowledge, customer messages, leads, approvals, and operations.

**Complication**  
Generic chatbots are not enough. Business AI needs company knowledge, safe workflows, usage controls, auditability, and human approval before taking action.

**Resolution**  
OnePilot AI centralizes business knowledge, AI agents, RAG, approvals, memory, usage tracking, and workflow automation in one SaaS workspace — with every action audited and every external action gated behind human approval.

---

## Prerequisites

- Docker stack running: `docker compose up -d && docker compose run --rm migrate`
- Demo data seeded: `docker compose run --rm seed`  
  (or locally: `cd backend && python scripts/seed_demo.py`)
- Evaluation report (optional): `cd backend && uv run python -m onepilot.evaluation.run_all_evals`
- Login: **`admin@onepilot.ai`** / **`Demo1234!`**

Verify:
```bash
cd backend && python scripts/check_stack.py
```

---

## Demo Flow (10 steps)

### 1 — Dashboard (30 s)

1. Open [http://localhost:3000/login](http://localhost:3000/login) and sign in
2. Land on **Dashboard** — point to conversations, documents (19), leads (12), pending approvals
3. Note header: **Live providers** vs **Deterministic fallback** (honest about env)

> **Talking point:** Single operational view — usage, knowledge, pipeline, and approval backlog.

---

### 2 — Provider & model diagnostics (45 s)

1. Open **Settings**
2. Show **AI Model Configuration** — `OPENAI_MODEL`, embeddings, speech (read-only, env-driven)
3. Scroll to **Runtime & Provider Diagnostics** — live vs mock vs missing
4. Emphasize: keys in environment only; Gmail/HubSpot/Stripe are **mock** for safe demos

> **Talking point:** Reviewers can verify configuration without exposing secrets.

---

### 3 — Knowledge Base golden query (60 s)

1. Navigate to **Knowledge Base** — confirm **19 NovaEdge** documents
2. Search: `How much does the Growth retainer cost per month?`
3. Show citation from **pricing_plans.md**
4. Grounded answer: `Can NovaEdge handle refunds autonomously?` → **AI Usage Policy**
5. Optional weak-evidence: `What is the population of Tokyo?`

> **Talking point:** Answers grounded in company docs, not the open internet.

---

### 4 — AI Workspace: general capability (30 s)

1. Open **AI Workspace**
2. Ask: `What can OnePilot help our team with?`
3. Show intent routing and helpful capability overview

> **Talking point:** Intent classification routes to the right behavior before tools run.

---

### 5 — AI Workspace: RAG question (45 s)

1. Ask: `What is our escalation policy for P1 support tickets?`
2. Show citations from **escalation_policy.md**
3. Optional: switch language to **French** and ask the same — answer in FR, citations in English

> **Talking point:** Multilingual replies with original-language citations.

---

### 6 — Speech to text (30 s)

1. Use microphone control in Workspace (requires `OPENAI_API_KEY`)
2. Record a short phrase; show transcript + detected language
3. If no key: explain graceful unavailability in Settings diagnostics

> **Talking point:** Voice input feeds the same agent pipeline as typed chat.

---

### 7 — Email Assistant & Approvals / HITL (90 s)

1. In Workspace, ask: `Draft a follow-up email to Olivia Grant at FinPulse about our Growth plan`
2. Show **email_drafting** intent and draft output
3. Or trigger workflow: `Automate HubSpot lead update and send a welcome email`
4. Open **Approvals** — show pending item, payload, risk level
5. **Approve** or **Reject** and show status change

> **Talking point:** AI can draft and propose — it cannot send email or update CRM without human approval.

---

### 8 — Usage & Billing (30 s)

1. Open **Usage & Admin**
2. Show usage events, token counts, estimated cost
3. Show invoice preview (mock Stripe — no real charges)
4. Glance at audit log entries

> **Talking point:** Full observability for cost control and compliance.

---

### 9 — Evaluation page (30 s)

1. Open **Evaluation**
2. Show routing / RAG / safety metrics from latest report
3. If empty: show run command on screen

```bash
cd backend && uv run python -m onepilot.evaluation.run_all_evals
```

> **Talking point:** Deterministic offline quality gates for capstone review.

---

### 10 — Architecture & safety close (45 s)

> "FastAPI backend, LangGraph agent, Postgres for tenancy and audit, Qdrant for vectors, Redis for cache. Every external integration uses a provider adapter — live when configured, mock or fallback otherwise. Multi-tenant isolation on every query. Prompt injection checks, audit logs, quotas, and mandatory HITL before send_email, schedule_meeting, or update_crm. This is demo-ready locally and in Docker — production deployment and live Stripe/Gmail are roadmap items."

Optional: show [docs/architecture.md](architecture.md) diagram.

---

## Email Assistant note

There is no separate Email Assistant page — email drafting lives in **AI Workspace** (intent: `email_drafting`). Dashboard **Quick actions** includes an Email Assistant shortcut to Workspace.

---

## Offline / no-OpenAI demo

- Without `OPENAI_API_KEY`: deterministic LLM fallback — workflows still demonstrate
- Without `QDRANT_URL`: in-memory vectors (same process)
- Mock CRM/email/calendar never call real APIs
- Re-run seed safely: `python scripts/seed_demo.py` (idempotent)

---

## CLI alternative

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/demo/setup -H 'Content-Type: application/json' -d '{}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://localhost:8000/demo/seed -H "Authorization: Bearer $TOKEN" | python -m json.tool

curl -s -X POST http://localhost:8000/knowledge/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query":"How much does the Growth retainer cost per month?"}' | python -m json.tool
```
