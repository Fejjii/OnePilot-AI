# LinkedIn Post — OnePilot AI

**Status:** Ready to publish after attaching screenshots from `docs/screenshots/`.  
**Tone:** Technical, honest, recruiter-friendly. No capstone/student framing.

---

I built **OnePilot AI** — a production-style AI operations workspace for small businesses.

The problem: teams juggle scattered docs, inbox drafts, scheduling, and leads across tools. Generic chatbots don’t give grounded answers, safe workflows, or auditability.

**What it does**
- Grounded RAG answers over a company knowledge base (with citations)
- LangGraph agent with two-stage intent routing and tool calling
- Human-in-the-loop approvals before any external action
- Multi-tenant isolation, usage tracking, and audit logs
- Guided workspace + mobile layout for real reviewer demos

**Public demo (no account needed)**  
https://one-pilot-ai.vercel.app  
Click **Try the demo**. Gmail and Calendar are **simulated** on the public track — the approval flow is real; outbound side effects are not.

**Stack**  
FastAPI · LangGraph · PostgreSQL · Redis · Qdrant · Next.js · Vercel · Railway

Happy to walk through architecture, safety trade-offs, or the evaluation harness.

#AIEngineering #FastAPI #LangGraph #NextJS #RAG #HumanInTheLoop

---

## Optional shorter variant

Built OnePilot AI: multi-tenant AI workspace with RAG + citations, LangGraph tools, and mandatory human approval before email/calendar actions.

Live demo (no signup; Gmail/Calendar simulated): https://one-pilot-ai.vercel.app
