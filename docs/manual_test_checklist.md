# Manual Test Checklist — OnePilot AI

Use this checklist before final review, demo recording, or push. Each item should pass on a fresh local or Docker stack after `seed_demo.py`.

**Setup:** `docker compose up -d` → `docker compose run --rm migrate` → `docker compose run --rm seed`  
**Login:** `admin@onepilot.ai` / `Demo1234!`

---

## 1. Auth / Login

- [ ] Login page loads without console errors
- [ ] Demo credentials box shows `admin@onepilot.ai` / `Demo1234!`
- [ ] Valid login redirects to Dashboard
- [ ] Invalid password shows a clear error (no stack trace)
- [ ] Sign out returns to login and clears session
- [ ] Register flow works for a new org (optional smoke)

---

## 2. Provider diagnostics

- [ ] Header shows **Live providers** or **Deterministic fallback** honestly
- [ ] Settings → **AI Model Configuration** shows chat/embedding/speech models (read-only)
- [ ] Settings → **Runtime & Provider Diagnostics** lists all providers with explicit modes
- [ ] Mock SaaS providers (Gmail, HubSpot, Calendar, Twilio, Stripe) show **Mock**
- [ ] No API keys, secrets, or raw env values visible in UI or network responses
- [ ] `GET /runtime/config` returns model names only (no secrets)

---

## 3. Knowledge Base RAG

- [ ] Knowledge Base lists **19** NovaEdge documents after seed
- [ ] Search: `How much does the Growth retainer cost per month?` returns **Pricing Plans** citation
- [ ] Grounded answer: `Can NovaEdge handle refunds autonomously?` cites **AI Usage Policy**
- [ ] Out-of-scope: `What is the population of Tokyo?` shows weak-evidence / refusal behavior
- [ ] Upload + delete document flows work (optional if demo-only)

---

## 4. Multilingual RAG

- [ ] AI Workspace language selector: Auto, EN, DE, FR, ES
- [ ] French query against English KB returns answer in French with **English citation titles**
- [ ] German query behaves similarly (optional spot check)

---

## 5. AI Workspace routing

- [ ] General capability: `What can OnePilot help me with?` → capability/help routing
- [ ] RAG question: `What is our refund policy?` → knowledge search with citations
- [ ] Workflow: `Help automate support and integrate HubSpot and Gmail` → workflow + tools trace
- [ ] Email Assistant (same page): `Draft a follow-up email to our top lead about the Growth plan`
- [ ] Intent badge and tool trace panel update per message
- [ ] Approval banner appears when an external action is proposed

---

## 6. Conversation switching / New conversation

- [ ] **New conversation** clears prior messages in the main pane
- [ ] Selecting a sidebar conversation loads its history (no stale messages from previous chat)
- [ ] Sending while switched conversations does not attach to wrong thread
- [ ] Dashboard “Recent agent activity” links open the correct conversation

---

## 7. Speech to text

- [ ] Workspace mic / speech control is visible when OpenAI is configured
- [ ] With `OPENAI_API_KEY` set: short audio clip transcribes and fills the input
- [ ] Without key: clear unavailable / fallback message (no fake “live” badge)
- [ ] Detected language hint appears when using Auto language mode

---

## 8. Approvals (HITL)

- [ ] Approvals page loads; pending count badge in sidebar matches API
- [ ] After seed: at least one **pending** approval visible
- [ ] Approve changes status; audit reflects decision
- [ ] Reject changes status; no automatic retry
- [ ] Payload shows proposed action type and demo-safe mock context

---

## 9. Usage and billing

- [ ] Usage & Admin shows quota progress bars
- [ ] Usage events table populated after seed (40 sample events)
- [ ] Billing summary / invoice preview shows estimated costs (mock Stripe)
- [ ] Admin audit log section lists seeded entries
- [ ] Costs labeled as estimates, not live charges

---

## 10. Evaluation

- [ ] Evaluation page loads summary when `reports/evaluation/latest.json` exists
- [ ] Empty state shows run command: `uv run python -m onepilot.evaluation.run_all_evals`
- [ ] Routing, RAG, and safety metric cards render when report present
- [ ] HITL / safety copy states email send requires approval

---

## 11. Settings

- [ ] Organization name and plan badge correct
- [ ] AI Model Configuration section complete
- [ ] Provider legend explains live / local / missing / mock / optional
- [ ] “Seed demo data” or equivalent admin action works if exposed in Settings

---

## 12. Security / no secrets

- [ ] Browser devtools → Network: no `OPENAI_API_KEY`, JWT secret, or Stripe keys in responses
- [ ] Frontend bundle contains no hardcoded API keys
- [ ] `.env` not committed; `.env.example` has placeholders only
- [ ] Mock providers never labeled as live in Settings diagnostics

---

## 13. Docker smoke test

- [ ] `docker compose up -d` — all services healthy
- [ ] `docker compose run --rm migrate` succeeds
- [ ] `docker compose run --rm seed` — 19 docs + operational data
- [ ] `curl http://localhost:8000/health` → 200
- [ ] Frontend at `http://localhost:3000` loads Dashboard after login
- [ ] `cd backend && python scripts/check_stack.py` passes (optional)

---

## Pages quick scan

| Page | Load | Empty state | Main action |
|------|------|-------------|-------------|
| Dashboard | ☐ | ☐ | ☐ Open workspace |
| AI Workspace | ☐ | ☐ | ☐ Send message |
| Knowledge Base | ☐ | ☐ | ☐ Search / answer |
| Leads | ☐ | ☐ | ☐ View / create lead |
| Email Assistant | ☐ | ☐ | ☐ Via Workspace draft |
| Approvals | ☐ | ☐ | ☐ Approve / reject |
| Usage & Admin | ☐ | ☐ | ☐ View events |
| Evaluation | ☐ | ☐ | ☐ View metrics |
| Memory | ☐ | ☐ | ☐ View / add memory |
| Settings | ☐ | ☐ | ☐ View diagnostics |

---

**Sign-off:** _______________  **Date:** _______________  **Environment:** local / Docker / other
