---
generated_utc: 2026-09-06T07:16:59Z
task_name: op-034-demo-approval-hygiene
agent_mode: cloud
agent_model: Cursor Grok 4.6
repository: Fejjii/OnePilot-AI
source_branch: fix/op-034-demo-approval-hygiene
source_sha: 2e127b4ce8d5de922de72453718ca046bdd7b756
task_type: implementation
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

- Started from `origin/main` at the expected SHA `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`.
- Implemented OP-034 on `fix/op-034-demo-approval-hygiene` only. Opened PR #32 into `main`. Did not merge.
- Added automatic public-demo approval hygiene in the demo-data layer (`cleanup_stale_public_demo_approvals`) and an org-scoped internal repository helper (`delete_ids_for_org`). No public DELETE route.
- Hooked hygiene into `ensure_curated_demo_approvals()`, which already runs on `POST /demo/start` and the existing `/demo/seed` refresh path. Cleanup happens before curated rows are refreshed.
- Updated `docs/agent/CLOUD_HANDOFF.md` in the same product PR.
- Did not deploy, did not modify `deployment/public-demo` or `deployment/live-google-demo`, and did not mutate production data.

## Important findings

- Hygiene behavior: when `PUBLIC_DEMO_ENABLED=true` and the caller principal is the public demo organization from settings (`DEV_ORG_ID`), stale non-curated approvals created by `create_demo_visitor_principal()` identities (`usr_demo_<ULID>`, excluding `DEV_USER_ID`) are deleted.
- Retention window: **6 hours**. Recent active-session visitor approvals are preserved.
- Canonical curated approvals are preserved (`curated=true`, seeded reasons, canonical titles). Other organizations and non-visitor creators are untouched. Accidental invocation outside public-demo mode is a no-op.
- Sarah Chen / Brightline Analytics lead narrative remains restored in production from the prior operator-authorized cleanup. The remaining recruiter-demo issue was stale non-curated approval residue; this PR implements the permanent code fix. Existing leftover rows older than 6 hours are removed on the next public-demo `/demo/start` after this change is deployed by an operator.

## P0 blockers

- None.

## P1 issues

- None. The shared-inbox residue still exists in live production until OP-034 is merged and an operator-authorized `deployment/public-demo` fast-forward ships the hygiene path. No production mutation was performed in this implementation task.

## P2 / deferred

- Audit P2 items remain deferred (demo email display, optional self-register, shared-org Admin, citations-overclaim copy, README test counts).
- Agent-created schedule approvals can still use a generic title and omit attendees. Out of scope for OP-034.

## Tests / validation

- Targeted: `pytest -q tests/test_public_demo_approval_hygiene.py tests/test_operational_seed.py tests/test_demo_start.py tests/test_approvals.py` — **45 passed**.
- Full backend: `pytest -q` — **821 passed, 3 skipped**.
- Scripts: `python -m pytest -q scripts/tests` — **53 passed**.
- Handoff sanitizer: `python scripts/sync_cloud_handoff.py --check --no-fetch` — **ok**.
- No frontend changes, so frontend tests were not required.

## Blockers

- None for the implementation. Live residue remains until merge + operator-authorized public-demo deploy.

## Recommended next step

Review and merge PR #32 (`fix/op-034-demo-approval-hygiene`) if accepted. After merge, only an operator-authorized fast-forward of `deployment/public-demo` ships hygiene to the live shared inbox. The next `/demo/start` then removes leftover non-curated demo-visitor rows older than 6 hours. Do not touch `deployment/live-google-demo`.

## Files changed

- `backend/src/onepilot/demo_data/seed.py`
- `backend/src/onepilot/repositories/approvals.py`
- `backend/src/onepilot/api/routers/demo.py`
- `backend/tests/test_public_demo_approval_hygiene.py`
- `docs/agent/CLOUD_HANDOFF.md`

## Production verification

- `origin/main` at task start: `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`
- `origin/deployment/public-demo` at task start: `bc07c5595b6a21709be5dea2e271c8b9b4e635c6` (not modified)
- `origin/deployment/live-google-demo`: `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (untouched)
- Production database: not mutated
- Host env / Railway / Vercel / Qdrant: not touched
