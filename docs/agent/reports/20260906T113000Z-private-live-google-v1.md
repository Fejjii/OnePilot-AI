---
generated_utc: 2026-09-06T11:30:00Z
task_name: private-live-google-v1
agent_mode: cloud
agent_model: Cursor Grok 4.6
repository: Fejjii/OnePilot-AI
source_branch: feat/private-live-google-v1
source_sha: f3980ddf294182a5177284deec22c2382a18a01c
task_type: implementation
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

- Started from latest `origin/main` at the expected SHA `1cd9abbc1eaec6022a17826e5fc4269797c40828`.
- Created exactly one branch: `feat/private-live-google-v1`.
- Audited current Gmail/Calendar/auth/HITL on `main` and compared `origin/deployment/live-google-demo`.
- Implemented the smallest safe private live-Google delta on current `main` (no provider-architecture rewrite).
- Added operator doc `docs/private_demo/LIVE_GOOGLE_SETUP.md` (variable names only).
- Updated `docs/agent/CLOUD_HANDOFF.md` in the same product PR.
- Opened PR #35 into `main`. Did not merge.
- `deployment/public-demo` and `deployment/live-google-demo` were not modified.

## Important findings

- PRIVATE LIVE GOOGLE PREP: **PASS** (code/config/tests). Host deploy is still operator-gated.
- Existing Gmail on `main`: full live `GmailProvider`, OAuth refresh-token env, approval-gated draft/send, `GMAIL_SEND_ENABLED` default false, `auto`/`mock` modes.
- Existing Calendar on `main`: full live `GoogleCalendarProvider`, same OAuth token, reads without approval, create after approval.
- `origin/deployment/live-google-demo` at `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` has **no unique commits** vs `main`. Current `main` is authoritative. Nothing was ported.
- Public demo remains mock/send-disabled; `/demo/start` cannot mint anonymous access to live Google.
- Current JWT + RBAC is sufficient for the private track if `PUBLIC_DEMO_ENABLED=false` and `DEV_AUTH_ENABLED=false`.
- New fail-closed gates: explicit `live` mode without OAuth; private track without credentials/org id; public+private both enabled; public demo always forces mock providers.

## P0 blockers

- None for this code PR.

## P1 issues

- None.

## P2 / deferred

- Operator must still create the dedicated Google account, Cloud project, OAuth consent, refresh token, and a **new** private Railway/Vercel host. Public production env must not be changed.
- Remaining audit P2 items are unchanged (demo email display, optional self-register, shared-org Admin, citations-overclaim copy).
- HTTP-only cookie auth remains a later hardening item.

## Tests / validation

- Targeted provider/HITL/demo/config tests: **119 passed**.
- Full backend: **846 passed, 3 skipped**.
- `python3 -m pytest -q scripts/tests`: **53 passed**.
- `python3 scripts/sync_cloud_handoff.py --check --no-fetch`: **ok**.
- Frontend unchanged; frontend tests not re-run.
- No Railway, Vercel, Qdrant, Google account, or deployment-branch mutations.

## Blockers

- None in code. Private deployment is blocked only on operator host/OAuth work.

## Recommended next step

Review and merge PR #35 if accepted. Then Sofien follows `docs/private_demo/LIVE_GOOGLE_SETUP.md` on a **new** private host: dedicated Google account, Gmail + Calendar APIs, OAuth consent, refresh token, `PRIVATE_LIVE_GOOGLE_ENABLED=true`, `PUBLIC_DEMO_ENABLED=false`, `PRIVATE_LIVE_GOOGLE_ORG_ID` set. Do not change public production env. Do not move deployment branches unless explicitly authorized.

## Files changed

- `backend/src/onepilot/core/config.py`
- `backend/src/onepilot/providers/__init__.py`
- `backend/src/onepilot/services/gmail_service.py`
- `backend/src/onepilot/services/calendar_service.py`
- `backend/src/onepilot/tools/email_tool.py`
- `backend/src/onepilot/api/routers/demo.py`
- `backend/src/onepilot/api/routers/health.py`
- `backend/tests/test_private_live_google.py` (new)
- `backend/tests/test_calendar_event_approval.py`
- `docs/private_demo/LIVE_GOOGLE_SETUP.md` (new)
- `docs/agent/CLOUD_HANDOFF.md`
- `.env.example`, `backend/.env.example`, README and safety/deployment/capabilities/security docs

## Production verification

- No production deploy or data mutation in this run.
- Public demo pointer remains `87eef7d5c2565181b94aff06be97374b22bdf4f9`.
- `origin/deployment/live-google-demo` remains `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332`.
