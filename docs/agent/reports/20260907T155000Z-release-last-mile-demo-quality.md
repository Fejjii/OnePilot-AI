---
generated_utc: 2026-09-07T15:50:00Z
task_name: release-last-mile-demo-quality
agent_mode: cloud
agent_model: cursor-grok-4.6
repository: Fejjii/OnePilot-AI
source_branch: fix/release-last-mile-demo-quality
source_sha: 16a7f84115c06719c75caea9c841e71f5f9d51b4
task_type: implementation
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

Last-mile recruiter-demo stabilization on one branch `fix/release-last-mile-demo-quality` and one PR into `main` (PR #37). Started from `origin/main` `611bcbdf7e480aa10b5d8a8295af770dc21b717b` (PR #36 already merged). Did not merge. Did not touch `deployment/public-demo`, `deployment/live-google-demo`, Railway/Vercel env, OAuth, live Qdrant, or Gmail send.

Fixed the three remaining live-validation issues plus a public NovaEdge RAG regression.

## Important findings

### P0-1 Calendar title

Root cause: `extract_meeting_title` required a matching pair of quotes after titled/called/named. Live/mobile input with curly quotes, no quotes, or an unmatched opening quote fell through to the default summary `OnePilot scheduled meeting`. Helper tests used a perfectly closed quoted string, so they passed while the live path did not.

Exact fix: accept quoted, curly-quoted, unquoted, and unmatched opening-quote titles; clip unquoted remainder so date/time clauses are not consumed. The title is stored on the approval payload, shown in the recruiter-facing proposal, and used as the Google event summary after approval.

### P0-2 Email recipient + Gmail HITL

Root causes:

1. Recruiter-facing `_format_email` preferred name/placeholder and `email.draft` did not emit `recipient_email`, so an explicit address displayed as `Recipient: Not specified`.
2. Wrapped addresses (`[email]`, `<email>`, `(email)`) were not treated as a first-class explicit recipient when no CRM row existed.
3. Live `draft_only` called `create_draft_direct` and skipped approval, creating a real Gmail draft before HITL.

Exact fix: unwrap explicit emails; return them immediately when no CRM match (never guess); display the address as Recipient; always create a pending `gmail_create_draft` ApprovalRequest. Existing approval execution creates the draft after Owner/Admin approval. `GMAIL_SEND_ENABLED=false` still means nothing is sent. Public demo stays mock.

### P1-3 Web search quality

Root cause: deterministic summary was meta (“based on external web search…”) and `maybe_llm_polish` instructed the model to “Rewrite the research brief…”, so live output talked about rewriting a brief. Polish headings also did not match web-only Top findings / Sources.

Exact fix: Summary and numbered Top findings are derived from retrieved citation evidence; source cards are preserved; instruction-like snippets are ignored for findings; dated sources are preferred when metadata exists; requested result count is honored; polish that is meta-copy or invents URLs is discarded.

### Public NovaEdge RAG

`/demo/start` still seeds 19 NovaEdge knowledge documents. A public demo session can obtain a tenant-grounded RAG answer with citations. Public Gmail/Calendar remain mock.

## P0 blockers

- None for this code change. Private-host deploy remains user-gated.

## P1 issues

- None for this code change.

## P2 / deferred

- Remaining audit P2 items from CLOUD_HANDOFF.md were not in scope (optional self-register, shared-org Admin, citations-overclaim copy).

## Tests / validation

Targeted last-mile e2e (exact live prompts + NovaEdge RAG + public Google isolation): **9 passed**.

Full backend: **883 passed, 3 skipped**.

Frontend vitest: **178 passed** (30 files).

pnpm typecheck: ok.

pnpm build: ok.

python3 -m pytest -q scripts/tests: **53 passed**.

python3 scripts/sync_cloud_handoff.py --check --no-fetch: ok.

Deterministic eval: intent 57/57 (100%), routing 57/57 (100%), combined 79 cases, 0 failed. Harness scores, not live-model quality.

## Blockers

- None. Implementation is READY FOR REVIEW. Do not merge unless asked. Private-host deploy remains user-gated.

## Recommended next step

Review PR #37 and merge only if accepted. Then operator-gated private-host deploy. Do not move deployment branches or enable Gmail send.

## Files changed

- `backend/src/onepilot/services/calendar_intent.py`
- `backend/src/onepilot/services/lead_service.py`
- `backend/src/onepilot/services/crm_email_grounding.py`
- `backend/src/onepilot/services/email_service.py`
- `backend/src/onepilot/services/gmail_service.py`
- `backend/src/onepilot/services/web_synthesis.py`
- `backend/src/onepilot/tools/email_tool.py`
- `backend/src/onepilot/agents/workflow.py`
- `backend/tests/test_release_last_mile_demo_quality.py`
- `backend/tests/test_web_synthesis.py`
- `backend/tests/test_gmail_provider.py`
- `backend/tests/test_leads.py`
- `backend/tests/test_crm_email_grounding.py`
- `frontend/src/lib/parse-structured-response.test.ts`
- `frontend/src/components/domain/assistant-message-content.test.tsx`
- `docs/private_demo/LIVE_GOOGLE_SETUP.md`
- `docs/agent/CLOUD_HANDOFF.md`

## Production verification

- `origin/main`: `611bcbdf7e480aa10b5d8a8295af770dc21b717b`
- `origin/deployment/public-demo`: `87eef7d5c2565181b94aff06be97374b22bdf4f9` (untouched)
- `origin/deployment/live-google-demo`: `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (untouched)
- PR: https://github.com/Fejjii/OnePilot-AI/pull/37
- Head SHA: `16a7f84115c06719c75caea9c841e71f5f9d51b4`
- No Railway/Vercel/OAuth/env changes. Gmail send remains disabled.
