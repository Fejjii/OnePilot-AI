---
generated_utc: 2026-09-07T16:08:00Z
task_name: release-last-mile-demo-quality
agent_mode: cloud
agent_model: cursor-grok-4.6
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

Operator marked PR #37 ready for review and merged it into `main`. Cloud did not merge. No further product commits. Deployment branches, Railway/Vercel env, OAuth, live Qdrant, and Gmail send were not touched.

## Important findings

Last-mile recruiter-demo quality is now on canonical `main`:

- Explicit Calendar titles preserved through chat, approval payload, and approved event summary
- Explicit wrapped email recipients displayed and propagated; live Gmail draft creation is HITL-gated (`gmail_create_draft`)
- Web search answers from retrieved citation evidence; polish no longer emits rewrite-the-brief meta copy
- Public `/demo/start` still seeds NovaEdge knowledge documents with tenant-grounded RAG citations
- Public Gmail/Calendar remain mock; send remains disabled

## P0 blockers

- None in merged code.

## P1 issues

- Private-host deploy remains user-gated.

## P2 / deferred

- Remaining audit P2 items from CLOUD_HANDOFF.md (optional self-register, shared-org Admin, citations-overclaim copy).

## Tests / validation

GitHub CI on PR #37 head `16a7f84115c06719c75caea9c841e71f5f9d51b4`: all 6 checks passed (Backend tests, Frontend checks, Script tests, Vercel Preview Comments, Vercel one-pilot-ai, Vercel onepilot-private-demo).

Local suite before merge: backend 883 passed, 3 skipped; frontend 178 passed; typecheck ok; production build ok; scripts/tests 53 passed; sanitizer ok; deterministic eval 79 cases, 0 failed.

## Blockers

- None.

## Recommended next step

Operator-gated private-host deploy if the last-mile fixes should be used on the live-Google demo. Do not move `deployment/public-demo` or `deployment/live-google-demo` unless explicitly authorized. Keep `GMAIL_SEND_ENABLED=false`. Keep public `gpt-5-nano`.

## Files changed

n/a

## Production verification

- PR #37: MERGED
- Merge commit / `origin/main`: `1efdf9bfaa6344b492e882428d55a7bc682d1c0f`
- Pre-merge branch head: `16a7f84115c06719c75caea9c841e71f5f9d51b4`
- `origin/deployment/public-demo`: `87eef7d5c2565181b94aff06be97374b22bdf4f9` (untouched)
- `origin/deployment/live-google-demo`: `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (untouched)

Public production env was not changed by this merge. Private live-Google host deploy remains operator-gated.
