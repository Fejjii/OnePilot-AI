---
generated_utc: 2026-09-07T17:01:18Z
task_name: public-demo-fast-forward-release
agent_mode: cloud
agent_model: cursor-grok-4.6-high
repository: Fejjii/OnePilot-AI
source_branch: main
source_sha: 1efdf9bfaa6344b492e882428d55a7bc682d1c0f
task_type: release
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

Operator-authorized deployment-ref release only. No product code change, no feature branch, no PR, no force push, no merge commit, no host-console or env change.

1. Read `AGENTS.md` and `docs/agent/CLOUD_HANDOFF.md`.
2. Fetched `origin/main`, `origin/deployment/public-demo`, and `origin/deployment/live-google-demo`.
3. Verified `origin/main` was exactly `1efdf9bfaa6344b492e882428d55a7bc682d1c0f`.
4. Verified `origin/deployment/public-demo` was `87eef7d5c2565181b94aff06be97374b22bdf4f9`, an ancestor of `main`, with no unique commits (`git log origin/main..origin/deployment/public-demo` empty).
5. Fast-forwarded `deployment/public-demo` to the exact `main` SHA:
   `git push origin 1efdf9bfaa6344b492e882428d55a7bc682d1c0f:refs/heads/deployment/public-demo`
   Remote reported `87eef7d..1efdf9b`.
6. Re-fetched and confirmed `deployment/public-demo == main`. Left `deployment/live-google-demo` at `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332`.
7. Verified public-demo safety assumptions in the released SHA (code inspection only).
8. Observed GitHub-visible CI and commit-status deploy triggers. Did not change Railway, Vercel, OAuth, secrets, databases, Redis, Qdrant, or provider configuration.

`docs/agent/CLOUD_HANDOFF.md` on `main` was not edited. This run was deployment-ref only; a later product/docs update can record the new public pointer.

## Important findings

### Refs

| Ref | Old SHA | New SHA |
|-----|---------|---------|
| `main` | `1efdf9bfaa6344b492e882428d55a7bc682d1c0f` | `1efdf9bfaa6344b492e882428d55a7bc682d1c0f` (unchanged) |
| `deployment/public-demo` | `87eef7d5c2565181b94aff06be97374b22bdf4f9` | `1efdf9bfaa6344b492e882428d55a7bc682d1c0f` |
| `deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (untouched) |

Fast-forward verification:

- Pre-push: `deployment/public-demo` was merge-base with `main` and had zero unique commits.
- Push was a non-force fast-forward (`87eef7d..1efdf9b`).
- Post-push: `origin/deployment/public-demo` == `origin/main` == `1efdf9bfaa6344b492e882428d55a7bc682d1c0f`.
- Old public SHA remains an ancestor of the new public SHA.

The public pointer now includes merged last-mile work through PR #37 (`fix/release-last-mile-demo-quality`) plus earlier `main` commits that were previously ahead of public-demo.

### Public demo safety assumptions (code at released SHA)

Confirmed in `backend/src/onepilot/core/config.py`, `backend/src/onepilot/providers/__init__.py`, `backend/src/onepilot/services/gmail_service.py`, `backend/src/onepilot/tools/email_tool.py`, and `backend/src/onepilot/services/approval_service.py`:

- `PUBLIC_DEMO_ENABLED` forces Gmail mock at provider init (`get_email_provider`) and org resolution (`resolve_email_provider_for_org`). Runtime status reports `gmail_mode=mock`, `gmail_active=False`.
- `PUBLIC_DEMO_ENABLED` forces Calendar mock at provider init (`get_calendar_provider`) and org resolution (`resolve_calendar_provider_for_org`). Runtime status reports `calendar_mode=mock`, `calendar_active=False`.
- `live_google_allowed_for_org()` returns `False` whenever `PUBLIC_DEMO_ENABLED` is true. Public and private-live flags cannot both be true. Production startup requires mock Gmail/Calendar modes and `GMAIL_SEND_ENABLED=false`.
- HITL remains enabled: `gmail_create_draft`, `gmail_send_email`, `send_email`, and calendar create/schedule actions are in `GATED_ACTION_TYPES`. Email draft tool always sets `approval_required = True`. Gmail send stays config-disabled.

No public live Google side effects from this flag combination.

## P0 blockers

- None.

## P1 issues

- None.

## P2 / deferred

- `docs/agent/CLOUD_HANDOFF.md` on `main` still lists public-demo at `87eef7d5c2565181b94aff06be97374b22bdf4f9`. Not updated here (no product edit / no PR).
- GitHub commit statuses on this SHA also showed Vercel `onepilot-private-demo` completing. That is a host-side SHA status, not a `deployment/live-google-demo` ref move. The live-google git pointer was not changed. No Vercel/Railway console work was done.

## Tests / validation

- Git ancestry / fast-forward checks: PASS.
- Post-push ref equality: PASS.
- `deployment/live-google-demo` unchanged: PASS.
- Public-demo safety code inspection at `1efdf9b`: PASS (mock Gmail, mock Calendar, no public live Google, HITL gated).
- GitHub Actions CI on `deployment/public-demo` @ `1efdf9b` (run 34145540933): **success** (Backend tests, Frontend checks, Script tests).
- No new pytest or live public-demo smoke was run (out of scope for this ref-only task).

## Blockers

- None for the git fast-forward. Host runtime/env remains user-gated; this agent did not smoke the live public URL.

## Recommended next step

Confirm the public recruiter demo in the Vercel/Railway consoles if a human walkthrough is wanted. Do not move `deployment/live-google-demo`. Optionally refresh `docs/agent/CLOUD_HANDOFF.md` in a later product/docs change so the recorded public SHA matches `1efdf9b`.

## Files changed

- None in the product working tree.
- Git ref only: `deployment/public-demo` fast-forwarded.

## Production verification

- Old public SHA: `87eef7d5c2565181b94aff06be97374b22bdf4f9`
- New public SHA: `1efdf9bfaa6344b492e882428d55a7bc682d1c0f`
- Main SHA: `1efdf9bfaa6344b492e882428d55a7bc682d1c0f`
- Fast-forward: verified (`87eef7d..1efdf9b`, no force, no unique public-demo commits)
- Deployment trigger status (GitHub-visible only; no host consoles opened):
  - GitHub CI on `deployment/public-demo`: success (run 34145540933)
  - Railway `devoted-empathy` commit status: success (`onepilot-ai-production.up.railway.app`); GitHub deployment 6313066944 success
  - Railway `confident-sparkle` commit status: success (`onepilot-ai-production-85dd.up.railway.app`)
  - Vercel `one-pilot-ai`: success (`Deployment has completed`); GitHub preview deployment 6313073831 success
  - Vercel `onepilot-private-demo`: success (`Deployment has completed`) — SHA-level host status; live-google git ref untouched
- Combined GitHub commit status for `1efdf9b`: success
- No Railway/Vercel/OAuth/secret/database/Redis/Qdrant/provider config was changed by this agent
