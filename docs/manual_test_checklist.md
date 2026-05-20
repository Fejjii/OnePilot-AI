# Manual Test Checklist — OnePilot AI

Final validation checklist before reviewer demo or push.

**Setup:** `docker compose up -d --build` → `docker compose run --rm migrate` → `docker compose run --rm seed`  
**Login:** `admin@onepilot.ai` / `Demo1234!`

---

## Core

- [ ] Login with demo user succeeds
- [ ] Dashboard loads without error card
- [ ] Provider diagnostics loads in Settings
- [ ] Header shows honest live vs fallback provider status
- [ ] No API keys or secrets in Network tab or page source

---

## AI Workspace

- [ ] General: `What can you do for me?` → general assistant, no RAG, no web
- [ ] RAG: `What services does NovaEdge Solutions offer and what integrations are supported?` → KB citations
- [ ] Serper: `Find recent SMB automation trends.` → external.web_search + URL citations
- [ ] Hybrid: `Find recent SMB automation trends and compare them with NovaEdge Solutions services.` → both tools, separated sections
- [ ] Gmail: `Draft and send an email to a high priority lead about NovaEdge automation services.` → draft + approval, no send before approve
- [ ] Calendar availability: `Am I free Friday at 11 am?` → busy/free, no event titles leaked
- [ ] Calendar slots: `Suggest three meeting slots next week.` → suggestions only
- [ ] Calendar schedule: `Schedule a 30 minute meeting with a high priority lead next week.` → approval created, no event before approve
- [ ] Compound: `Find recent SMB automation trends, draft an email, and schedule a meeting with a high priority lead next week.` → multi-tool + multiple approvals
- [ ] Speech to text works when OpenAI configured (or graceful unavailable message)
- [ ] Multilingual German RAG: DE query → answer in German, English citation titles
- [ ] Delete conversation removes thread from sidebar and clears pane
- [ ] Only one language selector in workspace (no duplicate)

---

## Providers

- [ ] Serper live when `SERPER_API_KEY` set (optional/mock otherwise)
- [ ] Gmail live or mock per OAuth config
- [ ] Google Calendar live or mock per OAuth config
- [ ] OpenAI live or deterministic fallback
- [ ] Qdrant live or in-memory fallback
- [ ] Redis live or in-memory fallback
- [ ] Postgres connected (required)
- [ ] `GET /providers` returns 200, modes only, no tokens
- [ ] `GET /health` returns status ok, no secrets

---

## Approvals

- [ ] Gmail draft approval: approve → execution metadata with draft id
- [ ] Calendar event approval: approve → execution metadata with event id
- [ ] Reject flow: status rejected, no auto-retry
- [ ] Needs more info flow: stays pending (if exposed in UI)

---

## Safety

- [ ] No direct email send before approval
- [ ] No calendar event creation before approval
- [ ] No private calendar event titles in chat or API responses
- [ ] No secrets in frontend bundle or API responses
- [ ] No `.env` committed — only `.env.example` placeholders
- [ ] Mock providers never labeled as live in diagnostics

---

## Pages quick scan

| Page | Load | Main action |
|------|------|-------------|
| Dashboard | ☐ | Usage + provider status |
| AI Workspace | ☐ | Send prompts above |
| Knowledge Base | ☐ | 19 NovaEdge docs + search |
| Leads | ☐ | View seeded leads |
| Approvals | ☐ | Approve / reject |
| Usage & Admin | ☐ | Costs + audit log |
| Evaluation | ☐ | Metrics from latest report |
| Memory | ☐ | View conversation memory |
| Settings | ☐ | Provider diagnostics |

---

## Docker smoke

- [ ] `docker compose up -d --build` — services healthy
- [ ] `docker compose run --rm migrate` succeeds
- [ ] `docker compose run --rm seed` — 19 docs + operational data
- [ ] `Invoke-RestMethod http://localhost:8000/health` → status ok
- [ ] `Invoke-RestMethod http://localhost:8000/providers` → diagnostics 200

---

## Backend / frontend CI (pre-push)

- [ ] `cd backend && uv run python -m pytest` — all pass
- [ ] `cd backend && uv run python -m onepilot.evaluation.run_all_evals` — reports updated
- [ ] `cd frontend && pnpm typecheck && pnpm lint && pnpm build && pnpm test` — all pass

---

**Sign-off:** _______________  **Date:** _______________  **Environment:** local / Docker
