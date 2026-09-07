---
generated_utc: 2026-09-07T13:45:05Z
task_name: private-demo-routing-response-polish
agent_mode: cloud
agent_model: cursor-grok-4.6
repository: Fejjii/OnePilot-AI
source_branch: fix/private-demo-routing-response-polish
source_sha: 432690d62f4a51e1e5f796cfe28ec9ff71c6b341
task_type: implementation
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

Stabilized private-demo functional routing and AI Workspace response UX on one branch, one PR into `main`. Did not merge. Did not touch `deployment/public-demo`, `deployment/live-google-demo`, Railway/Vercel env, Gmail send, HITL, OAuth, live Qdrant, or anonymous access.

Started from `main` @ `be8d956ea246bab895dd68a7f366b2a1d8ffbefb`. Branch: `fix/private-demo-routing-response-polish`. PR: https://github.com/Fejjii/OnePilot-AI/pull/36. Head SHA: `432690d62f4a51e1e5f796cfe28ec9ff71c6b341`.

Fixed four private-demo validation issues in product code:

- P0-1 calendar availability routing (Stage 1 + Stage 2 + time window parsing)
- P0-2 fully specified scheduling plus continuation recovery from bounded same-conversation user history
- P0-3 AI Workspace tenant RAG for substantive factual questions (no hardcoded codename)
- P1-4 recruiter-facing response structure and evidence-oriented confidence copy

Updated `docs/agent/CLOUD_HANDOFF.md` in the same PR. Regenerated deterministic eval snapshots from actual harness output (not live-model scores).

## Important findings

P0-1: Stage 1 `_CAPABILITY_PATTERNS` matched bare `available` (meant for “what tools are available”), so “When am I available tomorrow between 9 AM and 5 PM?” became General / `chat.general`. Stage 2 lacked `when am I available` / `what times am I free` / `do I have availability`. Time parser treated `between 9 AM and 5 PM` as a specific 9 AM slot via `_AT_TIME`.

P0-2: Conversational `\b(test|testing)\b` matched the title word “Test”. Titles were not extracted from `titled "..."`. `30-minute` hyphen duration was missed. Continuations did not read bounded `AgentState` user history. Proposal display converted already-local wall-clock times as UTC (15:00 shown as 17:00); the stored payload was local 15:00.

P0-3: Factual questions without policy/pricing/service keywords scored UNCLEAR → Clarify. Knowledge Base could return ORION-47 while AI Workspace asked for more detail and skipped `rag.answer`. Fix is a general substantive-factual fallback (length + WH/explain, excluding calendar/email/CRM/web/capability/small-talk), not a “codename” special case. A broad `what is/are the` pattern was tried and removed because it stole “What are the key points?” into RAG.

P1-4: Structured parser only treated known `##` titles as sections (unknown headings stayed raw markdown). Confidence badge always showed “Low confidence · 25%” even with citations. Email format leaked Gmail draft IDs and lacked Recipient.

Routing after this PR (production prompts):

- Availability → `calendar_availability` / `calendar.check_availability`
- Fully specified schedule → `calendar_scheduling`, next local day 15:00–15:30 Europe/Berlin, title exactly `OnePilot Live Calendar Test`, pending HITL, no Calendar write before approval
- “Just schedule the meeting.” after that request recovers the same details from last 6 user turns only
- Internal factual question → `knowledge_search` / `rag.answer` with citation, no Clarify

Public Gmail/Calendar remain mock/simulated if these changes later deploy to the public host. HITL is not bypassed.

## P0 blockers

- None.

## P1 issues

- None for this code change. Private-host deploy remains user-gated (Railway/Vercel). Do not merge unless asked.

## P2 / deferred

- Remaining audit P2 items from `CLOUD_HANDOFF.md` (demo email display, optional self-register, shared-org Admin, citations-overclaim copy) were not in scope.
- HTTP-only cookie auth, SSE streaming, object storage, background task queue, optional demo-reset remain backlog.

## Tests / validation

Targeted private-demo routing/calendar tests: passed (203 in the routing/calendar slice after the 17:00 display and “key points” fixes).

Full backend: 865 passed, 3 skipped.

Frontend vitest: 176 passed (30 files).

`pnpm typecheck`: ok.

`pnpm build`: ok.

`python3 -m pytest -q scripts/tests`: 53 passed.

`python3 scripts/sync_cloud_handoff.py --check --no-fetch`: ok.

Deterministic eval after new fixtures: intent 54/54 (100%), routing 54/54 (100%), combined suite 76 cases, 0 failed. These are harness scores, not live RAGAS or live-model quality scores. Do not fabricate either.

GitHub CI on product commit `8fcb688` (run 34128586331): success. Docs/eval snapshot commit `432690d` was pushed after that green run.

## Blockers

- None for the product PR. Merging and private-host deploy are operator-gated. This run did not change host environment variables.

## Recommended next step

Review PR #36 and merge only if the private-demo routing/UX fixes are accepted. After merge, deploying to the private host is still user-gated. Do not move `deployment/public-demo` or `deployment/live-google-demo`. Do not enable Gmail send or bypass HITL.

## Files changed

- `backend/src/onepilot/services/calendar_intent.py` (new shared availability/scheduling/continuation helpers)
- `backend/src/onepilot/agents/message_classifier.py`
- `backend/src/onepilot/agents/intent_classifier.py`
- `backend/src/onepilot/agents/workflow.py`
- `backend/src/onepilot/services/calendar_service.py`
- `backend/src/onepilot/providers/calendar/time_parser.py`
- `backend/src/onepilot/services/calendar_format.py`
- `backend/src/onepilot/services/web_synthesis.py`
- `backend/src/onepilot/evaluation/datasets/intent_eval.jsonl`
- `backend/src/onepilot/evaluation/run_intent_eval.py`
- `backend/docs/TWO_STAGE_ROUTING.md`
- `backend/tests/test_private_demo_routing_polish.py` (new)
- `backend/tests/test_calendar_intent_routing.py`
- `backend/tests/test_calendar_time_parser.py`
- `backend/tests/test_calendar_format.py`
- `frontend/src/lib/parse-structured-response.ts` (+ test)
- `frontend/src/components/domain/assistant-message-content.tsx` (+ test)
- `frontend/src/components/domain/confidence-badge.tsx` (+ test)
- `frontend/src/components/domain/chat-message.tsx`
- `frontend/src/app/(app)/knowledge/page.tsx`
- `frontend/src/app/(app)/workspace/page.tsx`
- `frontend/src/app/(app)/workspace/workspace.test.tsx`
- `backend/reports/evaluation/*_latest.{json,md}`
- `docs/agent/CLOUD_HANDOFF.md`

Deployment branches were not modified.

## Production verification

Not a host deploy. Refs only:

- `origin/main`: `be8d956ea246bab895dd68a7f366b2a1d8ffbefb`
- PR head: `432690d62f4a51e1e5f796cfe28ec9ff71c6b341`
- `origin/deployment/public-demo`: `87eef7d5c2565181b94aff06be97374b22bdf4f9` (untouched)
- `origin/deployment/live-google-demo`: `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (untouched)
