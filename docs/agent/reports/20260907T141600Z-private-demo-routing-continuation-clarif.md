---
generated_utc: 2026-09-07T14:16:00Z
task_name: private-demo-routing-continuation-clarify
agent_mode: cloud
agent_model: cursor-grok-4.6
repository: Fejjii/OnePilot-AI
source_branch: fix/private-demo-routing-response-polish
source_sha: 9aa8f2f7238ade98f14430f8daab11b46cabc130
task_type: implementation
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

Final review fix on existing branch `fix/private-demo-routing-response-polish` and the same PR #36. Did not create a new branch or PR. Did not merge.

Fixed a release-blocking edge case: scheduling continuations such as "Just schedule the meeting." must not create a calendar proposal or ApprovalRequest when bounded same-conversation user history has no recoverable prior scheduling request.

Also narrowed the substantive-factual RAG fallback so generic world-knowledge ("What is the capital of France?") is not treated as tenant business knowledge, while preserving ORION-47 internal factual RAG.

## Important findings

Root cause: Stage 1 ran generic `looks_like_scheduling` before continuation/history handling. "Just schedule the meeting" matches `schedule` + `meeting`, so it became WORKFLOW_REQUEST even with empty history. Stage 2 then mapped it through generic calendar scheduling patterns to `CALENDAR_SCHEDULING`, and the calendar node called `calendar.create_event_request` with default date/time/title.

Exact fix:

- Evaluate continuation before generic scheduling in Stage 1 and Stage 2.
- Continuation + recoverable prior request → `CALENDAR_SCHEDULING` with recovered details, pending HITL, no provider write.
- Continuation + no recoverable prior request → `UNCLEAR` / `CLARIFICATION`, specific ask for title/date/time/duration, no create tool, no approval.
- `looks_like_scheduling` and `infer_calendar_tool` no longer treat continuation-only phrases as create.
- Calendar node still refuses to run create if a continuation arrives without recovered history (defense in depth).
- RAG fallback now requires a tenant/work cue and excludes generic geography trivia such as "capital of".

## P0 blockers

- None.

## P1 issues

- None for this code change. Private-host deploy remains user-gated.

## P2 / deferred

- Remaining audit P2 items from CLOUD_HANDOFF.md were not in scope.

## Tests / validation

Targeted routing/calendar tests: passed (240 in the first routing slice; private-demo polish tests included).

Full backend: 871 passed, 3 skipped.

Frontend vitest: 176 passed (30 files).

pnpm typecheck: ok.

pnpm build: ok.

python3 -m pytest -q scripts/tests: 53 passed.

python3 scripts/sync_cloud_handoff.py --check --no-fetch: ok.

Deterministic eval: intent 57/57 (100%), routing 57/57 (100%), combined 79 cases, 0 failed. Harness scores, not live-model quality.

## Blockers

- None. Implementation is READY FOR REVIEW. Do not merge unless asked.

## Recommended next step

Review PR #36 and merge only if accepted. Private-host deploy remains user-gated. Do not move deployment branches or change Gmail send / HITL.

## Files changed

- backend/src/onepilot/services/calendar_intent.py
- backend/src/onepilot/agents/message_classifier.py
- backend/src/onepilot/agents/intent_classifier.py
- backend/src/onepilot/agents/workflow.py
- backend/src/onepilot/services/calendar_service.py
- backend/src/onepilot/services/i18n_messages.py
- backend/src/onepilot/evaluation/datasets/intent_eval.jsonl
- backend/tests/test_private_demo_routing_polish.py
- backend/docs/TWO_STAGE_ROUTING.md
- backend/reports/evaluation/*_latest.{json,md}
- docs/agent/CLOUD_HANDOFF.md

## Production verification

Not a host deploy. Refs only:

- origin/main: be8d956ea246bab895dd68a7f366b2a1d8ffbefb
- PR head: 9aa8f2f7238ade98f14430f8daab11b46cabc130
- deployment/public-demo and deployment/live-google-demo untouched
