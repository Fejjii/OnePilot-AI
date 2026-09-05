---
generated_utc: 2026-09-05T13:46:01Z
task_name: public-demo-mutable-data-cleanup
agent_mode: cloud
agent_model: Cursor Grok 4.6
repository: Fejjii/OnePilot-AI
source_branch: main
source_sha: bc07c5595b6a21709be5dea2e271c8b9b4e635c6
task_type: release
status: PASS_WITH_ISSUES
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

- Operator-authorized one-time production cleanup of mutable recruiter-facing CRM / approval data for the **public demo organization only**. No product-code edits. No branch. No PR. No deploy. No env/host changes. `main`, `deployment/public-demo`, and `deployment/live-google-demo` were not moved.
- Preflight fetched GitHub refs and confirmed the expected product SHAs.
- Identified the public-demo tenant from application code and the live `/demo/start` path, then confirmed with `/me` and `/organizations/current`. Did not guess an organization id.
- Inspected demo-org leads and approvals through the authenticated tenant-scoped API before mutation.
- Restored drifted canonical lead urgency values through `PATCH /leads/{id}` scoped to that tenant and matched by canonical email.
- Confirmed there were no non-canonical demo lead rows to delete.
- Attempted leftover approval cleanup through existing authenticated APIs only. Production has no approval DELETE path. This environment has no production-safe database management path. Leftover agent-created approvals were **not** rejected or rewritten to hide the residue.
- Started a fresh normal `/demo/start` session and re-validated ranking, recruiter flows, and public runtime safety.

## Important findings

- Public-demo tenant identity from application code + live session:
  - id: `org_demo_onepilot` (same as `Settings.DEV_ORG_ID` default used by `/demo/start`)
  - name: `OnePilot AI`
  - slug: `onepilot-ai-demo`
- Observed pre-cleanup drift matched the prior release report:
  - Kevin Park / NovaStack DevTools stored `urgency=high` (canonical seed: `medium`)
  - Priya Nair / Atlas Health Clinics stored `urgency=high` (canonical seed: `medium`)
  - 12/12 leads were canonical seeded rows; no extra ranking-altering lead rows
  - 8 canonical seeded approvals were already complete and recruiter-facing
  - 9 leftover agent-created approvals remained from earlier reviewer sessions
- After the org-scoped lead restore, `rank_leads()` and `GET /leads` both return Sarah Chen / Brightline Analytics as the unique top / most promising seeded lead.
- Fresh-session chat, workspace insight, and CRM email drafting now agree on Sarah Chen / Brightline Analytics.
- Shared Approvals still contain the 9 pre-existing leftover rows. Existing APIs can list and decide approvals but cannot delete them. `/demo/start` reseeds curated rows and explicitly keeps agent-created leftovers.

## P0 blockers

- None for the restored Sarah-first recruiter lead narrative or public runtime safety.

## P1 issues

- Shared public-demo approval inbox is not a clean canonical baseline. 9 leftover agent-created rows remain, including placeholder-style Gmail drafts and incomplete calendar cards with empty attendee lists. Removing them requires a production-safe org-scoped delete/reset path that does not exist in the current API, and this Cloud environment has no authorized database console access.

## P2 / deferred

- Agent-created schedule approvals can still use a generic title (`OnePilot scheduled meeting`) and omit attendees. Creation still stops at approval; no live Calendar write was observed.
- Mock “meetings this week” still renders a fixed late-August week. Availability remains semantically distinct from meetings.

## Tests / validation

- `python scripts/smoke_test_public_demo.py --base-url https://onepilot-ai-production.up.railway.app`: critical checks **PASSED** (health, providers). Authenticated optional checks skipped (no demo password used).
- Fresh `POST /demo/start` session against the production backend, then tenant-scoped API validation. No secrets printed.

Observed public runtime (no secrets):

REAL: OpenAI chat (`gpt-5-nano`), embeddings, Qdrant RAG, Redis, Serper, agent orchestration, CRM/business logic, HITL approvals.

SIMULATED / DISABLED: Gmail mock, Gmail send disabled, Calendar mock, Calendar create disabled, public-demo speech transcription disabled.

## Blockers

- Approval residue cannot be removed with the existing authenticated production API (DELETE `/approvals/{id}` returns 405). This Cloud environment has no production database credential or Railway console path. A later operator-authorized org-scoped delete/reset is required for a clean shared Approvals inbox.

## Recommended next step

READY AFTER SMALL FIXES. The Sarah Chen / Brightline Analytics recruiter narrative is restored and consistent across Leads, workspace insight, chat, and CRM email. Share the demo if leftover shared-inbox cards are acceptable. To make Approvals canonical-only, authorize a production-safe org-scoped delete of the 9 leftover agent-created rows in `org_demo_onepilot` only. Do not change Railway/Vercel/Qdrant env or enable live Gmail/Calendar. Do not touch `deployment/live-google-demo`.

## Files changed

- n/a. Product files, deployment refs, env vars, Qdrant, and host configuration were not modified.

## Production verification

### Refs verified

- `origin/main`: `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`
- `origin/deployment/public-demo`: `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`
- `origin/deployment/live-google-demo`: `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (unchanged)

### Cleanup scope (sanitized)

- Tenant: public demo org only (`org_demo_onepilot` / `onepilot-ai-demo`)
- Other organizations mutated: **none**
- Tables / systems touched: leads only, via tenant-scoped PATCH
- Not touched: Qdrant, documents, conversations (except normal validation chat), users beyond normal `/demo/start` visitor issuance, env vars, Railway/Vercel, deployment refs

### Lead cleanup

- Canonical lead rows restored: **2** (Kevin Park urgency `high` → `medium`; Priya Nair urgency `high` → `medium`)
- All other mutable recruiter-facing fields on the 12 canonical leads already matched `seed.py`
- Non-canonical demo lead rows removed: **0** (none existed)
- Resulting top lead from `GET /leads` and `rank_leads()`: **Sarah Chen / Brightline Analytics**
- Sarah consistency after a fresh session:
  - Leads API top row: Sarah Chen / Brightline Analytics
  - “Who is my most promising lead?”: Sarah Chen / Brightline Analytics
  - Workspace insight / prioritize-first: Sarah Chen / Brightline Analytics
  - Business summary top lead: Sarah Chen / Brightline Analytics
  - “Draft a follow-up email to my most promising lead”: grounded to Sarah Chen / Brightline Analytics; approval required; no real send

### Approval cleanup

- Approval rows deleted / reseeded this run: **0**
- Canonical seeded approvals retained: **8**, all with complete recruiter-facing previews
  - Email: recipient, subject, body
  - Calendar: summary, start_time, end_time, attendees
- Leftover non-canonical shared-demo approvals remaining: **9**
  - Placeholder-style Gmail drafts remain
  - Incomplete old calendar approvals with empty attendees remain
- This validation session created 2 new approvals (expected):
  - Recruiter-friendly Sarah Chen / Brightline Analytics email draft (complete preview, no placeholders)
  - Schedule approval only; no `_execution` / live Calendar write

### Critical recruiter flows

1. Start demo: PASS
2. Business summary: PASS; Sarah/Brightline first among top leads
3. Pending approvals: PASS as a working inbox; not a clean canonical-only inbox
4. RAG / knowledge question: PASS; citations present (escalation policy)
5. Most promising lead: PASS; Sarah Chen / Brightline Analytics
6. CRM-grounded follow-up email: PASS; Sarah-grounded; approval required; no real send
7. Show meetings this week: PASS; lists existing mock meetings
8. Find available slots: PASS; explicitly “open times, not existing meetings”
9. Schedule a meeting: PASS; approval only; no live Calendar create
10. Execution trace/details: PASS; recruiter-facing steps present
11. Serper / web search: PASS; citations present
12. Evaluation page/API: PASS (`GET /evaluation/summary` HTTP 200)

### Public runtime safety

- Health: PASS
- Providers: PASS
- Runtime config: PASS (`gpt-5-nano`, embeddings live)
- `/docs`: PASS (404)
- Frontend `https://one-pilot-ai.vercel.app`: HTTP 200
- Gmail: mock, send disabled
- Calendar: mock, create disabled; recruiter reason remains “Calendar is simulated for this public demo. Google Calendar is not connected.”
- Speech: `POST /speech/transcribe` HTTP 403, `error=SPEECH_DISABLED`
- No real Gmail send observed
- No real Calendar creation observed
