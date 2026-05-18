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
- Both backend (`:8000`) and frontend (`:3000`) healthy

Verify:
```bash
cd backend && python scripts/check_stack.py
```

---

## Demo Flow

### Step 1 — Login (30 seconds)

1. Open [http://localhost:3000](http://localhost:3000)
2. Click **Login** — use `admin@novaedge.io` / `Demo1234!`

> **Talking point:** Multi-tenant SaaS. Every org is isolated. No data leaks across tenants.

---

### Step 2 — Dashboard (30 seconds)

1. Land on the **Dashboard** page
2. Point to the usage summary cards: chat messages, RAG queries, document uploads
3. Point to recent activity feed

> **Talking point:** Operators see real-time usage and quota status. Quotas prevent runaway AI costs.

---

### Step 3 — Knowledge Base (60 seconds)

1. Navigate to **Knowledge Base**
2. Show the list of **19 NovaEdge documents** (pricing plans, sales playbook, AI usage policy, support guides, etc.)
3. Click **Search** and enter: `How much does the Growth retainer cost per month?`
4. Show the results: top citation is `Pricing Plans`, with section, score, and chunk preview

> **Talking point:** RAG retrieval with citations. The AI retrieves the most relevant chunk from your company's documents — not the internet. Every answer is grounded in your own knowledge base.

5. Run a **grounded answer** query: `Can NovaEdge handle refunds autonomously?`
6. Show the answer that references the AI Usage Policy forbidding autonomous refunds
7. Run an **out-of-scope** query: `What is the population of Tokyo?`
8. Show the `weak_evidence: true` response — the AI refuses to answer from its training data

> **Talking point:** Weak-evidence guardrail. The AI does not hallucinate. It says "I don't know" when the company knowledge base doesn't support an answer.

---

### Step 4 — AI Workspace (90 seconds)

1. Navigate to **AI Workspace**
2. Type: `Can you help us automate customer support and integrate with HubSpot and Gmail?`
3. Show the **intent classification** banner: `workflow_action`
4. Show the **tool trace** panel: tools selected (`lead_lookup`, `crm_update`, `email_draft`)
5. Show the **response** with the proposed action draft
6. Show the **approval banner**: "This action requires human approval before execution"

> **Talking point:** The agent classifies intent, selects the right tools, and creates a draft — but it never executes external actions without approval. This is the most important safety property of the system.

---

### Step 5 — Approvals (60 seconds)

1. Navigate to **Approvals**
2. Show the **pending approval** created by the previous chat
3. Show the **action payload**: what the agent proposes to do, which tool, which data
4. Click **Approve** — show the status change to `approved`

OR

4. Click **Reject** — show the status change to `rejected` and that no action was taken

> **Talking point:** Human-in-the-loop is not optional here. Approvals are mandatory. Rejected actions are never retried automatically.

---

### Step 6 — Leads (30 seconds)

1. Navigate to **Leads**
2. Show the lead table with seeded NovaEdge leads (name, email, status, score)
3. Click on a lead to show its detail: activity history, qualification score

> **Talking point:** Lead management is integrated with the AI agent. When you ask the agent to qualify a lead, it looks up the record here.

---

### Step 7 — Usage / Admin (30 seconds)

1. Navigate to **Usage**
2. Show the usage events table: each AI action is recorded with tokens, latency, and provider
3. Show the audit log: `document.uploaded`, `approval.created`, `chat.message` entries

> **Talking point:** Every action is audited with actor, timestamp, and metadata. You can trace exactly what the AI did, when, and why.

---

### Step 8 — Architecture Summary (30 seconds)

Close with a brief architecture explanation:

> "The backend is FastAPI with a LangGraph agent, Postgres for structured data, Qdrant for vector search, and Redis for rate limiting. Every external provider — OpenAI, HubSpot, Gmail — has a mock fallback so the system works without any third-party keys for demos. The multi-tenant model isolates all data by organization. And the approval gate ensures no autonomous external action ever fires without a human saying yes."

---

## Offline Demo Notes

- Without an OpenAI API key, the system uses a **deterministic fallback LLM** — responses are canned but the entire workflow still demonstrates correctly.
- Without Qdrant, the system uses an **in-memory vector store** — retrieval works within the same process.
- The `fallback_used: true` flag appears in API responses when providers are in mock mode.
- The demo seed data is **deterministic** (seeded with `seed=42`) and idempotent — safe to re-run.

---

## CLI Demo Alternative

If the frontend is unavailable, the same demo can be driven via curl:

```bash
# Register and get token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@novaedge.io","password":"Demo1234!","full_name":"Demo","organization_name":"NovaEdge"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Seed knowledge base
curl -s -X POST http://localhost:8000/demo/seed \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Ask a grounded question
curl -s -X POST http://localhost:8000/knowledge/answer \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query":"Can NovaEdge handle refunds autonomously?"}' | python3 -m json.tool

# Chat with the agent
curl -s -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Draft an email to our top lead about our Growth plan","conversation_id":"demo-001"}' \
  | python3 -m json.tool

# Check pending approvals
curl -s http://localhost:8000/approvals?status=pending \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Check usage
curl -s http://localhost:8000/usage/summary \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
