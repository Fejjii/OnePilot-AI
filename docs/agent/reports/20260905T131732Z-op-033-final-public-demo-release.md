---
generated_utc: 2026-09-05T13:17:32Z
task_name: OP-033-final-public-demo-release
agent_mode: cloud
agent_model: Cursor Grok 4.6
repository: Fejjii/OnePilot-AI
source_branch: deployment/public-demo
source_sha: bc07c5595b6a21709be5dea2e271c8b9b4e635c6
task_type: release
status: PASS_WITH_ISSUES
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

- Operator-authorized final public-demo release. No product-code edits. No PR. `main` and `deployment/live-google-demo` were not modified.
- Pre-release refs matched the expected SHAs. `deployment/public-demo` was an ancestor of `main`. The update was a normal fast-forward.
- Confirmed `origin/main` includes PR #30 (Cloud Agent report bridge) and PR #31 (OP-033 final P1 fixes).
- Fast-forwarded only `deployment/public-demo` from `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8` to `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`. No force push. No merge commit.
- Waited for automatic Vercel and Railway deployments associated with that push. Host configuration was not changed.
- Ran baseline production checks, the repository public-demo smoke test, OP-033 production acceptance, and critical recruiter-flow checks.

## Important findings

- Public-demo pointer now matches `main` at `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`.
- Private live-Google pointer remains `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332`.
- OP-033 P1-1 Calendar mock diagnostics: **PASS** in production.
- OP-033 P1-2 public-demo speech disable: **PASS** in production.
- OP-033 P1-3 seeded approval preview fields: **PASS** in production. Seeded email/calendar rows use the new recruiter-facing keys. This is not a seed-key migration miss.
- OP-033 P1-4 lead ranking consistency: **FAIL** in production. The ranking code is live and internally consistent, but stored lead attributes have drifted from the curated seed. Kevin Park and Priya Nair are stored as `urgency=high` (seed expects `medium`). With three high/qualified leads, alphabetical order puts Kevin Park first, then Priya Nair, then Sarah Chen. Chat, CRM email drafting, and workspace insights agree with that drifted ranking.
- Leftover agent-created approvals from earlier reviewer sessions remain in the shared demo inbox. Seeded rows were refreshed by the normal `/demo/start` path. Agent leftovers were not deleted.

## P0 blockers

- None.

## P1 issues

- Production lead-attribute drift: Kevin Park (NovaStack DevTools) and Priya Nair (Atlas Health Clinics) are stored as high urgency. The curated seed keeps those two at medium and Sarah Chen / Brightline Analytics as the top high+qualified lead. Recruiter-facing surfaces therefore currently promote Kevin Park first. This is a production-data issue, not a missing `rank_leads()` deploy. Do not treat it as a host-config or code-hotfix requirement unless an operator later authorizes a data refresh.

## P2 / deferred

- Shared-demo inbox still contains leftover agent-created approvals, including one placeholder-style Gmail draft subject (`[Company]` / `[specific goal]`) and two calendar approvals with empty attendee lists. Seeded cards are complete; these leftovers are previous-session residue.
- Agent-created schedule approvals can use a generic title (`OnePilot scheduled meeting`) and omit attendees. Creation still stops at approval; no live Calendar write was observed.
- Mock “meetings this week” still renders a fixed late-August week. Availability remains semantically distinct from meetings.

## Tests / validation

- `python scripts/smoke_test_public_demo.py --base-url https://onepilot-ai-production.up.railway.app`: critical checks **PASSED** (health, providers). Authenticated optional checks skipped (no demo password used).
- GitHub commit statuses on `bc07c55`: Vercel **success**; Railway **success**.
- GitHub checks on the public-demo push: Backend tests, Frontend checks, Script tests, Vercel Preview Comments — all **success**.
- Frontend `https://one-pilot-ai.vercel.app` HTTP 200. Landing includes “Try the demo”.
- `GET /health` HTTP 200, `status=ok`.
- `GET /providers` HTTP 200.
- `GET /runtime/config` HTTP 200. Chat model `gpt-5-nano`. Embeddings live. Provider mode live.
- `GET /docs` HTTP 404 as intended.
- Public-demo smoke + authenticated acceptance against the production backend.

Observed public runtime (no secrets):

REAL: OpenAI chat (`gpt-5-nano`), embeddings, Qdrant RAG, Redis, Serper, agent orchestration, CRM/business logic, HITL approvals.

SIMULATED / DISABLED: Gmail mock, Gmail send disabled, Calendar mock, Calendar create disabled, public-demo speech transcription disabled.

## Blockers

- None that prevent the new code from running in production.
- Recruiter-facing “most promising lead” story is currently Kevin-first because stored urgency values drifted. A later operator-authorized demo-data refresh would restore Sarah Chen as the top seeded lead. This run did not reset production data.

## Recommended next step

READY AFTER SMALL FIXES. Share the demo if the Kevin-first ranking is acceptable for now. If the intended recruiter narrative must be Sarah Chen / Brightline Analytics first, authorize a production demo-data refresh of lead attributes (and optionally leftover agent approvals). Do not change Railway/Vercel/Qdrant env or enable live Gmail/Calendar. Do not touch `deployment/live-google-demo`.

## Files changed

- n/a for this release. Product files were already on `main` via PR #30 and PR #31. This run only moved the `deployment/public-demo` pointer and published this report.

## Production verification

### Pre-release refs

- `origin/main`: `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`
- `origin/deployment/public-demo`: `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8`
- `origin/deployment/live-google-demo`: `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332`
- Ancestor / fast-forward checks: PASS
- PR #30 and PR #31 present on `main`: PASS

### Post-release refs

- `origin/main`: `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`
- `origin/deployment/public-demo`: `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`
- `origin/deployment/live-google-demo`: `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (unchanged)

### Deployment status

- Vercel production (`https://one-pilot-ai.vercel.app`): success / HTTP 200
- Railway production (`https://onepilot-ai-production.up.railway.app`): success / healthy

### Baseline provider/runtime

- Health: PASS
- Providers: PASS
- Runtime config: PASS (`gpt-5-nano`, embeddings live)
- `/docs`: PASS (404)
- Gmail: mock, send disabled
- Calendar: mock, create disabled
- Speech provider remains configured, but public-demo transcribe is rejected (see P1-2)
- Qdrant, Redis, Serper: live

### OP-033 production checks

- **P1-1 Calendar diagnostics: PASS.** Mode `mock`. Healthy simulated mode. Recruiter-facing reason: “Calendar is simulated for this public demo. Google Calendar is not connected.” No `missing_google_client_id` / provider-outage wording. Real Calendar remains disabled.
- **P1-2 Speech safety: PASS.** Normal `/demo/start` session. `POST /speech/transcribe` with a harmless multipart body returned HTTP 403, `error=SPEECH_DISABLED`, message “Speech transcription is disabled in the public demo.” Rejection happened before any live transcription. Production workspace JS gates the microphone control with `isDemo` (`!isDemo && MicrophoneInput`). Anonymous public-demo workspace does not render an active microphone control. Config was not changed to test this.
- **P1-3 Approval previews: PASS** for seeded rows. After the normal demo-start refresh, curated email approvals have recipient (`to`), subject, and body. Curated calendar approvals have summary, start time, end time, and attendees. No old seeded payload keys (`body_preview` / `attendee` / `purpose`) remain on curated rows. Leftover **agent-created** approvals are a separate production-inbox residue issue, not a seeded-key migration miss.
- **P1-4 Lead ranking consistency: FAIL** due to production data drift. Leads API top row is Kevin Park / NovaStack DevTools. “Who is my most promising lead?” and workspace insight agree. CRM-grounded follow-up email also drafted to Kevin and required approval. Sarah Chen / Brightline Analytics is present and still high/qualified, but third after the drifted high-urgency Kevin and Priya rows. Production data was not mutated or reseeded to force a pass.

### Critical recruiter flows

1. Start demo: PASS
2. Business summary: PASS (workspace insights; mentions Sarah/Brightline among top leads)
3. Pending approvals: PASS
4. RAG / knowledge question: PASS, citations present (escalation policy)
5. Most promising lead: FAIL vs intended Sarah-first narrative; agrees with drifted stored ranking
6. CRM-grounded follow-up email: PASS as approval-gated draft; targets Kevin because of drifted ranking
7. Show meetings this week: PASS; lists existing mock meetings
8. Find available slots: PASS; explicitly “open times, not existing meetings”
9. Schedule a meeting: PASS; approval only; no live Calendar create
10. Execution trace/details: PASS; recruiter-facing steps present
11. Serper / web search: PASS; citations present
12. Evaluation page/API: PASS (`GET /evaluation/summary` HTTP 200)

Safety checks across these flows:

- No real Gmail send observed
- No real Calendar creation observed
- No raw IDs / debug / provider payloads in recruiter-facing chat text
- No placeholder content in this session’s new CRM email draft
- Knowledge and web-search answers included citations
- Meetings and availability remained semantically distinct
