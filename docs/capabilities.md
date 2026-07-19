# Feature & Capability Matrix

Honest matrix of what OnePilot AI can do, what the **public demo** exposes, and what remains mocked or private.

**Live demo:** [https://one-pilot-ai.vercel.app](https://one-pilot-ai.vercel.app)  
**Backend health:** [https://onepilot-ai-production.up.railway.app/health](https://onepilot-ai-production.up.railway.app/health)

| Capability | Product status | Public demo behavior | Notes |
|------------|----------------|----------------------|-------|
| Public landing + **Try the demo** | Live | One-click JWT session via `POST /demo/start` | No credentials on the public entry path |
| AI Workspace (guided prompts) | Live | Real chat against the LangGraph agent | Prompt chips submit through `POST /chat` |
| Two-stage intent routing | Live | Live | Message class → intent → tools |
| Knowledge upload + RAG answers | Live | Seeded **19** NovaEdge docs; search/answer work | Citations from internal KB only |
| Weak-evidence / confidence guards | Live | Live | Refuses or hedges when retrieval is thin |
| External web search (Serper) | Live when keyed | Live or mock canned results | Without `SERPER_API_KEY`, mock + clear optional mode |
| Hybrid web + knowledge answers | Live | Live (web may be mock) | Internal vs external evidence labeled separately |
| Email drafting (in-app) | Live | Live | Draft text generated in workspace |
| Gmail draft / send | Live when OAuth configured | **Simulated (mock provider)** | Approval-gated; send off by default (`GMAIL_SEND_ENABLED=false`) |
| Calendar availability / slots | Live when OAuth configured | **Simulated (mock provider)** | Busy/free only — no private event titles |
| Calendar event creation | Live when OAuth configured | **Simulated after approval** | Creates `ApprovalRequest` first |
| Approvals (HITL) | Live | Live with seeded + chat-created items | Owner/Admin decide; audited |
| Leads / business insights | Live | Seeded **12** leads | Dashboard + leads table |
| Usage, quotas, billing preview | Live | Live estimates | Stripe is **mock** — no real charges |
| Audit log | Live | Live | Sensitive actions and approvals |
| User / org memory CRUD | Live | Live (tenant-scoped) | Shared-demo **agent** memory disabled (ADR 007) |
| Agent memory recall / persist | Live | Disabled on shared-demo tenant | `/demo/start` clears memories for isolation |
| Mobile workspace layout | Live | Live | Bottom tabs + Chat / History / Details panels |
| Multi-tenant isolation | Live | Shared demo org for reviewers | Repository-scoped `organization_id` |
| Prompt-injection guards | Live | Live | Blocked before agent execution |
| Rate limiting | Live | Live (Redis on Railway) | In-memory fallback without Redis |
| Evaluation harness | Live | Offline reports in UI | Deterministic routing/RAG/safety suites |
| HubSpot CRM | Mock adapter | Mock | Not a live CRM integration |
| Twilio | Mock adapter | Mock | Not live telephony |
| Streaming chat (SSE/WebSocket) | Not implemented | — | Synchronous responses today |

## Public-demo safety summary

- Gmail and Google Calendar use **mock providers** on the public track.
- No credentials are shown on the landing or login demo entry.
- Shared-demo agent memory is disabled; demo start clears prior memories so reviewers do not leak facts across sessions.
- External side effects still go through the approvals queue even when providers are mocked.

## Related docs

- [architecture.md](architecture.md) — system design and Mermaid diagrams
- [safety_and_privacy.md](safety_and_privacy.md) — HITL, isolation, privacy
- [demo_script.md](demo_script.md) — guided reviewer walkthrough
- [limitations_roadmap.md](limitations_roadmap.md) — gaps and next work
