# Recording Checklist — Recruiter Demo (~3 minutes)

Operational shot list for [RECRUITER_DEMO_SCRIPT.md](RECRUITER_DEMO_SCRIPT.md).  
Production URL only: **https://one-pilot-ai.vercel.app**  
Public runtime model: **`gpt-5-nano`**. Gmail and Calendar writes are simulated.

Stay in recruiter-facing views. Do not open raw API payloads, env vars, Settings secrets, or the private live-Google track.

---

## PRE-RECORDING CHECKLIST

- [ ] Fresh demo session: hard refresh, then **Try the live demo** (hero) or **Try the demo** (footer). Do not reuse a stale tab.
- [ ] Browser zoom 100% (or 110% if text is small on your display). One window, one profile.
- [ ] No personal tabs, bookmarks bar clutter, or other accounts visible.
- [ ] Notifications off (OS + browser). Do not share Slack/Mail badges.
- [ ] Stable internet. If a chat hangs, stop and restart the session — do not improvise a second product story.
- [ ] **Approvals:** after `/demo/start`, pending items should be the curated seed plus only what you create in this take. If the inbox looks dirty, start a new demo session and wait a beat.
- [ ] **Leads:** Sarah Chen / Brightline Analytics is the top promising lead (`qualified`, `high`). If another name wins, stop — the ranking story is broken for this take.
- [ ] Confirm the URL is `https://one-pilot-ai.vercel.app` (not localhost).
- [ ] Test the five prompts once off-camera. Keep the on-camera take clean.
- [ ] No `/docs`, `/health` JSON, Railway, Vercel, Qdrant console, or `.env` visible.

---

## RECORDING RULES

- Do not open raw API or provider payloads.
- Do not show credentials, tokens, or env vars.
- Do not expose private live-Google setup.
- Recruiter-facing views only: Landing, Workspace, Response details, Approvals, optional Leads.
- **Do not approve** a Gmail or Calendar action. Approving a mock write can look like a live send.
- Say once, clearly: **Gmail and Calendar writes are simulated in the public demo.**
- Prefer typing the exact prompts below. Chips are fine only if you immediately say the full prompt.

Target total: **~3 minutes**. Minimal navigation: Landing → Workspace (stay there) → Details → Approvals → back to Workspace for the close.

---

## Segment list

### 00:00 — Landing

| | |
|---|---|
| **Page** | `https://one-pilot-ai.vercel.app/` |
| **Click** | None at first. Hold the hero: headline, “What is real / simulated,” **Try the live demo**. |
| **Should appear** | Product story. No credentials. Copy that Gmail/Calendar side effects are simulated. |
| **Say** | Intro (script A): what OnePilot is, why it exists, operations workspace not a chatbot. |
| **Next** | Click **Try the live demo**. |

### 00:15 — Workspace

| | |
|---|---|
| **Page** | `/workspace` after demo start |
| **Click** | Wait for the guided empty state. Optional: glance at provider badges (Gmail simulated, Calendar simulated). |
| **Should appear** | Seeded workspace, composer, suggested prompts, Demo-mode badges. Sidebar org name is **OnePilot AI**; knowledge corpus is **NovaEdge**. |
| **Say** | Business context (script B): one workspace — knowledge, CRM, approvals, calendar, web search. |
| **Next** | Focus the composer. Do not click around. |

### 00:30 — Most promising lead

| | |
|---|---|
| **Page** | `/workspace` |
| **Prompt** | `Who is my most promising lead?` |
| **Should appear** | Sarah Chen, Brightline Analytics. Supporting facts (qualified / high urgency, support-automation pain). Trace may show CRM / insights, not a canned chip string. |
| **Say** | Script C first half: routing + `rank_leads` + grounded stored facts. |
| **Next** | Keep the thread. Type the next prompt immediately. |

### 00:55 — Email draft + approval

| | |
|---|---|
| **Page** | `/workspace` |
| **Prompt** | `Draft a follow-up email to my most promising lead.` |
| **Should appear** | Draft aimed at Sarah Chen / `sarah.chen@brightline.io`. Approval-gated banner. **Do not click Approve.** |
| **Say** | Script C second half: lead resolution, LLM draft, structured result, human approval, no autonomous send. Say Gmail is simulated. |
| **Next** | Stay in the same composer for RAG. |

### 01:25 — RAG + citations

| | |
|---|---|
| **Page** | `/workspace` (Knowledge page is optional; skip it if time is tight) |
| **Prompt** | `What does our refund policy say?` |
| **Should appear** | Grounded policy answer + citations (refund policy / Pilot section). Open **Response details** only enough to show Citations. |
| **Say** | Script D: retrieval, citations, Qdrant, embeddings, tenant filter. Answers come from company documents. |
| **Next** | Calendar prompts in the same thread. |

### 01:55 — Meetings / availability

| | |
|---|---|
| **Page** | `/workspace` |
| **Prompt 1** | `Show my meetings this week.` |
| **Prompt 2** | `Find available time slots.` |
| **Should appear** | First: a meeting list (busy/free style, not a private live calendar). Second: open slots — not the same tool as “show meetings.” No create-event approval unless you ask to schedule (do not). |
| **Say** | Script E: semantic split, tool routing, meeting create would need approval, Calendar writes are simulated. |
| **Next** | Open Details or Approvals — one hop. |

### 02:15 — Execution trace / approvals

| | |
|---|---|
| **Page** | Workspace **Response details** (“What the assistant did”), then `/approvals` if the banner is visible |
| **Click** | Details panel on the latest email or RAG turn. Then **Approvals** in the nav. Do **not** approve or reject. |
| **Should appear** | Sanitized steps (`Understanding request`, `Reading CRM context`, `Drafting email`, `Creating approval`, or `Finding cited sources`). Approvals queue with the new email draft plus curated seed items. |
| **Say** | Script F: HITL, sanitized traces, RBAC / tenant scope, public-demo writes disabled. |
| **Next** | Return to Workspace or stay on Approvals for the close. Do not open Settings JSON. |

### 02:35 — Architecture

| | |
|---|---|
| **Page** | Workspace or Landing `#whats-real` if you still have the tab. Prefer staying put and speaking. |
| **Click** | None required. |
| **Should appear** | Whatever is already on screen. Do not flip through six docs. |
| **Say** | Script G stack: LangGraph, OpenAI, FastAPI, Qdrant, Postgres, Redis, Next.js, Railway / Vercel. |
| **Next** | Last sentence. |

### 02:55 — Conclusion

| | |
|---|---|
| **Page** | Same frame |
| **Click** | Stop recording after the last line. |
| **Should appear** | Clean workspace or approvals — no error toasts. |
| **Say** | This is end-to-end Applied AI / AI Engineering: architecture, orchestration, RAG, safety, evaluation, and a deployed demo. |
| **Next** | End. |

---

## Timing budget

| Clock | Segment | Spoken target |
|-------|---------|----------------|
| 00:00 | Landing | ~15s |
| 00:15 | Workspace context | ~15s |
| 00:30 | Lead ranking | ~25s |
| 00:55 | Email + approval | ~30s |
| 01:25 | RAG + citations | ~30s |
| 01:55 | Meetings / slots | ~20s |
| 02:15 | Trace / Approvals | ~20s |
| 02:35 | Architecture | ~20s |
| 02:55 | Close | ~10s |

If a generation is slow, hold the frame and keep talking. Do not fill with a sixth prompt.

---

## Abort / retake

| Problem | Action |
|---------|--------|
| Lead is not Sarah Chen | Stop. New demo session. Do not narrate a different winner. |
| Empty or weak RAG, no citations | Retake the refund prompt once. If it fails again, stop. |
| Approval auto-executes or looks “sent” | Say simulated, do not approve, retake if the UI implies a live send. |
| Error toast / quota | Stop. Do not debug on camera. |
| Wrong URL or localhost | Discard the take. |

Related: [demo_script.md](../demo_script.md) (longer reviewer walkthrough) · [capabilities.md](../capabilities.md)
