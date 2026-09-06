---
generated_utc: 2026-09-06T08:27:00Z
task_name: op-034-final-public-demo-release
agent_mode: cloud
agent_model: Cursor Grok 4.6
repository: Fejjii/OnePilot-AI
source_branch: deployment/public-demo
source_sha: 87eef7d5c2565181b94aff06be97374b22bdf4f9
task_type: release
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

- Operator-authorized FINAL public-demo release and production acceptance for OP-034.
- Fetched origin and verified the expected pre-release refs exactly.
- Confirmed `origin/deployment/public-demo` was an ancestor of `origin/main`, the update was a normal fast-forward, PR #32 / OP-034 was on `main`, and `deployment/live-google-demo` was unchanged.
- Fast-forwarded **only** `deployment/public-demo` from `bc07c5595b6a21709be5dea2e271c8b9b4e635c6` to `87eef7d5c2565181b94aff06be97374b22bdf4f9`. No force, no merge commit, no new branch, no PR, no product-code edits, `main` not modified, `deployment/live-google-demo` not touched.
- Waited for Vercel production, Railway production, and GitHub CI on `deployment/public-demo`.
- After the new backend was live, started a fresh public demo with `POST /demo/start` so the deployed OP-034 hygiene path ran. Did not perform any manual database cleanup.
- Ran a second fresh-session recruiter acceptance (API + browser) covering the 20 requested checks and provider/runtime safety.

## Important findings

- OP-034 automatic hygiene ran on the first live `POST /demo/start` after Railway success.
- Immediately after that hygiene run the shared demo inbox had:
  - **8** canonical curated approvals present
  - **0** stale non-curated demo-visitor approvals
  - **0** recent non-curated visitor approvals retained
  - **1** non-visitor leftover (see below)
- Compared with the previously documented 9 leftover agent-created rows, **8 stale visitor approvals were removed** by the automatic path.
- The remaining leftover does **not** satisfy the OP-034 stale-visitor rule:
  - title: `Gmail action: Following up on Draft a follow-up email to Northwind about the renewal quote`
  - status: approved
  - created by the deterministic demo owner (`usr_demo_admin`), not a `usr_demo_<ULID>` visitor
  - age about 94 hours
  - recipient `lead@example.com`
  - visible only if the Approvals filter is switched from default Pending to Approved / All
- Default Pending inbox is recruiter-clean: curated Brightline / Northwind cards only, plus recent cards created by this acceptance journey (Sarah follow-up email and a schedule-meeting approval). Those recent visitor rows are correctly retained by the 6-hour window.
- No other organization was targeted. Hygiene is org-scoped to the public demo tenant.

## P0 blockers

- None.

## P1 issues

- None recruiter-critical. The one owner-created approved leftover is out of OP-034 scope by design and is not in the default Pending inbox.

## P2 / deferred

- One approved owner-created historical Gmail draft remains (`lead@example.com`). OP-034 correctly left it because `created_by` is not a demo visitor. Do not reopen unless the Approved/All filter is treated as a recruiter surface that must be canonical-only.
- Agent-created schedule approvals can still use a generic title (`OnePilot scheduled meeting`). Creation still stops at approval; no live Calendar write.
- Audit P2 items remain deferred (demo email display, optional self-register, shared-org Admin, citations-overclaim copy, README test counts).
- `docs/agent/CLOUD_HANDOFF.md` on `main` still describes the pre-OP-034 project state. This release did not edit product files.

## Tests / validation

- GitHub CI on `deployment/public-demo` @ `87eef7d5c2565181b94aff06be97374b22bdf4f9` (run 34021137264): **success** (Backend tests, Frontend checks, Script tests).
- Vercel production commit status: **success**.
- Railway production commit status: **success** (`onepilot-ai-production.up.railway.app`).
- Fresh `POST /demo/start` executed deployed OP-034 hygiene. No manual DB mutation.
- Recruiter API + browser acceptance on a later fresh session. No tokens or secrets printed.

## Blockers

- None recruiter-critical.

## Recommended next step

**READY TO SHARE.**

Share `https://one-pilot-ai.vercel.app`. Keep `gpt-5-nano`. Leave Gmail mock/send-disabled and Calendar mock/create-disabled. Do not touch `deployment/live-google-demo`. Do not reopen P2 items unless the remaining approved owner-created Gmail leftover is later treated as a visible recruiter blocker.

## Files changed

- n/a. Product files were not edited. Only the `deployment/public-demo` pointer was fast-forwarded, and this sanitized report is published to `agent/cloud-state`.

## Production verification

### Refs

| Ref | Pre-release | Post-release |
|-----|-------------|--------------|
| `origin/main` | `87eef7d5c2565181b94aff06be97374b22bdf4f9` | `87eef7d5c2565181b94aff06be97374b22bdf4f9` (unchanged) |
| `origin/deployment/public-demo` | `bc07c5595b6a21709be5dea2e271c8b9b4e635c6` | `87eef7d5c2565181b94aff06be97374b22bdf4f9` |
| `origin/deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (unchanged) |

Fast-forward only. No force. Public-demo is now identical to `main` and includes PR #32 / OP-034.

### Deployment status

- Vercel production (`https://one-pilot-ai.vercel.app`): **PASS**
- Railway production (`https://onepilot-ai-production.up.railway.app`): **PASS**
- GitHub CI / checks on `deployment/public-demo`: **PASS**

### OP-034 cleanup result (sanitized counts)

Measured immediately after the first live hygiene `POST /demo/start`. A pre-hygiene live snapshot was not available because `/demo/start` returned HTTP 502 during the Railway restart; counts below use that first successful post-deploy start plus the previously documented leftover inventory.

- Stale approvals removed: **8**
- Canonical approvals present: **8**
- Recent non-curated approvals retained at hygiene time: **0**
- Owner-created leftover remaining (not a visitor row): **1**
- Other organizations affected: **none**

Later acceptance chats created 2 recent visitor approvals (Sarah email draft + schedule request). Those are inside the 6-hour window and were correctly preserved.

### Recruiter acceptance

| # | Check | Result |
|---|-------|--------|
| 1 | Landing / Try the demo | PASS |
| 2 | Business summary | PASS (workspace insights; Sarah first among top leads) |
| 3 | RAG knowledge answer with citations | PASS (NovaEdge refund policy; 5 citations) |
| 4 | Most promising lead = Sarah Chen / Brightline Analytics | PASS (Leads API, chat, and Leads UI) |
| 5 | Workspace insight agrees | PASS |
| 6 | CRM-grounded follow-up email targets Sarah | PASS (`sarah.chen@brightline.io`) |
| 7 | Email requires approval; no real Gmail send | PASS |
| 8 | Approvals inbox recruiter-clean | PASS (default Pending; no placeholder historical drafts) |
| 9 | Show meetings this week | PASS (distinct from open slots) |
| 10 | Find available slots | PASS |
| 11 | Schedule meeting -> approval only | PASS |
| 12 | No real Calendar creation | PASS |
| 13 | Execution trace recruiter-friendly | PASS (Understanding request / Reviewing workspace activity / tool labels only) |
| 14 | Serper/web search with sources | PASS |
| 15 | Evaluation summary available | PASS |
| 16 | Settings Calendar = healthy simulated mode | PASS |
| 17 | Public speech transcription = SPEECH_DISABLED | PASS (`POST /speech/transcribe` HTTP 403; no mic in public UI) |
| 18 | Runtime model = gpt-5-nano | PASS |
| 19 | `/docs` remains 404 | PASS (backend and Vercel frontend) |
| 20 | No raw IDs / debug / provider payloads / placeholders in recruiter-facing output | PASS |

Sarah lead consistency: **PASS**.

### Provider / runtime safety

REAL: OpenAI chat (`gpt-5-nano`), embeddings (`text-embedding-3-small`), Qdrant, Redis, Serper, agent orchestration, CRM/business logic, HITL approvals.

SIMULATED / DISABLED: Gmail mock, Gmail send disabled, Calendar mock, Calendar create disabled, public-demo speech transcription disabled (`SPEECH_DISABLED`). Settings still reports Whisper as a configured model; the public transcribe route rejects before any live transcription.
