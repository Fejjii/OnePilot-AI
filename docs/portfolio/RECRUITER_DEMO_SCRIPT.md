# Recruiter Demo Script — ~3 minutes

Spoken first-person script for Sofien on the **public demo only**: [https://one-pilot-ai.vercel.app](https://one-pilot-ai.vercel.app)

Target: **2:45–3:30**. Pair with [RECORDING_CHECKLIST.md](RECORDING_CHECKLIST.md).  
Do not claim live Gmail sending, live Google Calendar writes, or a production accuracy score. Public runtime model: **`gpt-5-nano`**.

Type the prompts below. Workspace chips exist, but their wording is slightly different.

---

## A. Intro — ~20 sec

OnePilot is an Agentic AI operations workspace I built for small businesses. The problem is not “chat with a document.” Operators lose time across knowledge, leads, drafts, and scheduling, and a single LLM call cannot run that loop safely. So this is a control plane: retrieve company knowledge, inspect CRM context, draft the next action, then stop for a human before anything external runs.

---

## B. Business context — ~20 sec

I’ll open the live demo — no account. This is a seeded workspace. The knowledge corpus is NovaEdge Solutions: policies, services, playbooks. Around that you have CRM leads, an approvals queue, a calendar surface, and web search. Same agent, different tools, one tenant.

---

## C. CRM / agentic flow — ~45 sec

First: **Who is my most promising lead?**

That is not a hardcoded UI string. The request is classified, routed into workspace / CRM logic, and ranked with stored lead facts. The top open lead should be Sarah Chen, VP Operations at Brightline Analytics — qualified, high urgency.

Now: **Draft a follow-up email to my most promising lead.**

Same ranking resolves the recipient. The model drafts to her stored context — pain point, next action — and returns a structured draft. It also creates a human approval. I am not sending mail. On this public demo Gmail is simulated, and even after approval nothing hits a real inbox.

---

## D. RAG — ~35 sec

**What does our refund policy say?**

This path is retrieval, not CRM. The question is embedded with `text-embedding-3-small`, searched in Qdrant, and filtered to this organization. You should see a grounded answer with citations from the refund-policy document — for example the pilot window, then the declining refund schedule. If retrieval is weak, it hedges and skips the LLM instead of guessing.

---

## E. Calendar / tools — ~25 sec

**Show my meetings this week.** Then **Find available time slots.**

Those are different tools. One lists events. The other checks free/busy or open slots. Creating a meeting would generate another approval. Calendar writes are simulated here, same as Gmail. I am only showing routing and the read path.

---

## F. Trace / safety — ~25 sec

Open **Response details** — or Approvals if you want the queue.

You get a sanitized execution trace: understanding the request, reading CRM, retrieving sources, drafting, creating an approval. Prompts, tokens, and raw provider payloads stay off this UI. Approvals are Owner/Admin, tenant-scoped. External provider writes are disabled for anonymous public-demo traffic. That is HITL, not a trust-me chatbot.

---

## G. Architecture / end — ~25 sec

Under the hood: LangGraph on FastAPI, OpenAI for chat and embeddings, Qdrant for retrieval, Postgres and Redis for state and rate limits, Next.js on Vercel, API on Railway. What I want this to show is end-to-end Applied AI — product architecture, orchestration, RAG, safety, evaluation, and a deployed demo — not a notebook and not a wrapper around one prompt.
