---
generated_utc: 2026-09-05T11:44:00Z
task_name: final-public-demo-release-audit
agent_mode: cloud
agent_model: Cursor Grok 4.6
repository: Fejjii/OnePilot-AI
source_branch: main
source_sha: b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8
task_type: audit
status: PASS_WITH_ISSUES
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

- Read-only final release audit of OnePilot AI on `main` at `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8`.
- GitHub refs were treated as authoritative. `origin/main` and `origin/deployment/public-demo` were identical at that SHA. `origin/deployment/live-google-demo` remained `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332`.
- Reviewed security, tenant/demo isolation, Gmail/Calendar side-effect safety, AI routing, recruiter journey, mobile layout, tests, and public capability claims.
- Live public diagnostics were read-only (`/health`, `/runtime/config`, `/providers`, CORS preflight, frontend HTTP 200, `/docs` 404). No host consoles were changed.
- No product files, branches, or PRs were created during the audit. This publish only records that existing result on `agent/cloud-state`.

## Important findings

- FINAL AUDIT: PASS WITH ISSUES
- Final recommendation: READY AFTER SMALL FIXES
- No P0 blockers. Public-demo Gmail/Calendar writes stay mock. Cross-tenant isolation holds. Chat is per-visitor.
- Live public runtime at audit time: chat model `gpt-5-nano` live; embeddings/Qdrant/Redis/Serper live; Gmail mock; send disabled; Calendar mock; calendar create disabled; `/docs` disabled; CORS allowlists the public Vercel origin.
- `docs/agent/CLOUD_HANDOFF.md` was stale during the audit (still described public-demo as behind `main` and OP-032 as unmerged). GitHub refs and live diagnostics were the release record.

### Security verdict

Safe to share as a public mock-Gmail/Calendar demo. Tenant isolation is real (`organization_id` on repositories; Qdrant collection `documents_{org}` plus payload filter). Demo visitors get distinct users; conversations are user-scoped and tested. Gmail send and live Calendar create cannot run on a correctly configured public-demo host (startup validation plus live diagnostics). CORS is allowlisted. Secrets are not returned from public diagnostic endpoints. Execution traces strip prompts, tokens, and raw IDs.

Accepted documented tradeoff: reviewers share one org. Approvals, uploads, leads, and audit rows are visible to other demo visitors. Chat and agent memory are the isolated surfaces. That is not a cross-tenant break.

Residual abuse: speech spend (P1), optional self-register, shared-org Admin.

### AI architecture verdict

Credible and consistent with claims. Two-stage classify → route → tools → HITL is implemented. RAG cites internal docs; weak evidence is guarded. CRM email grounding and workspace insights share `rank_leads()`; seeded data makes Sarah Chen / Brightline Analytics the unique top lead (high + qualified). Email text can generate without approval; Gmail/Calendar writes require approval. Public providers stay mock. Execution traces persist recruiter labels only.

The product does not claim live Gmail/Calendar on the public track. Evaluation UI discloses that RAG scores are deterministic keyword checks, not live RAGAS.

### Recruiter-demo verdict

A technical recruiter can understand the product in 2–4 minutes from landing → Try the demo → chips: what it is, RAG + routing + HITL, what is real vs simulated, and that this is a built multi-tenant workspace rather than a chat wrapper.

Landing copy is honest. Guided chips match the intended journey. No placeholder/lorem issues in the recruiter path. Remaining recruiter-credibility issues are Calendar Settings copy (P1), empty seeded approval previews (P1), and Leads table sort vs agent ranking (P1).

### Mobile verdict

No P1 mobile issues in implementation. Workspace uses overflow containment, wrapping chips, bottom tabs, Chat/History/Details panels, 44px targets, and tables that scroll inside the page. Not browser-verified on a physical phone in the read-only pass; code matches the OP-032 polish intent.

### Test-coverage verdict

Recruiter-critical backend paths are well covered: `/demo/start` gating, conversation isolation, tenant isolation vs a real org, production mock/send startup rules, CRM grounding, execution-trace sanitization, public-demo chat/search/token caps, starter-prompt routing.

Highest-risk gaps: Calendar mock diagnostics must not report unhealthy / “provider issue”; speech has no abuse test; no test that a second visitor cannot see another visitor’s approval payload (today they can, by shared-org design); no test that lead ranking survives a second visitor creating a competing high/qualified lead; seeded approval payload fields are not asserted against the Approvals UI.

### Truthfulness of public capability claims

Accurate, with the Settings Calendar contradiction (P1) and the Knowledge/Settings “citations with every response” overclaim (P2).

| Claim | Evidence |
|---|---|
| Gmail/Calendar simulated; send off | Live health + startup guard + mock providers |
| OpenAI, embeddings, Qdrant RAG, Serper, traces, HITL real | Live providers + runtime config (`gpt-5-nano`) |
| No credentials on Try the demo | `/demo/start` issues a short-lived session |
| Shared demo, agent memory disabled | Seed + shared-demo principal check |
| `gpt-5-nano` is the public runtime model | Live chat model (repo default remains `gpt-4o-mini`; host env wins) |

## P0 blockers

- None.

## P1 issues

- Calendar mock diagnostics look broken on Settings.
  Path: `backend/src/onepilot/api/routers/health.py` (`_build_calendar_diagnostic`); reason sourced from `backend/src/onepilot/core/config.py` `calendar_runtime_status()`.
  Behavior: Live `/providers` reports Calendar `mode=mock` but unhealthy, reason “Calendar provider issue: missing_google_client_id”. Workspace header/badges correctly say Simulated. Settings (`frontend/src/app/(app)/settings/page.tsx`) shows Mock + unhealthy + “provider issue”. Gmail mock uses healthy “OAuth not configured; using mock…” copy.
  Why it matters: The longer demo script closes on Settings. A technical recruiter will read this as an outage, not a safe mock.
  Smallest fix: When Calendar is forced to mock, set healthy and use the same “mock for safe demos” reason as Gmail. Do not prefix mock/missing OAuth with “provider issue”.

- Speech transcription has no public-demo spend cap.
  Path: `backend/src/onepilot/api/routers/speech.py`; workspace mic in `frontend/src/app/(app)/workspace/page.tsx`; limits in `backend/src/onepilot/security/rate_limit.py` and `backend/src/onepilot/services/quota_service.py`.
  Behavior: Chat, web search, and the daily token budget are capped. `POST /speech/transcribe` is authenticated-only, 25MB max, then calls live speech with no IP/day/audio budget. A demo session is easy to mint. The token budget applies only to the demo org and only to token usage, not audio minutes.
  Why it matters: The public link plus a short-lived session is enough to burn managed-AI spend outside the documented abuse controls. Host project caps cannot be verified from the repo.
  Smallest fix: Rate-limit speech per IP (and/or disable the mic when public demo is enabled), and count audio seconds against a small daily budget.

- Seeded Approvals previews are empty.
  Path: curated payloads in `backend/src/onepilot/demo_data/seed.py`; UI in `frontend/src/app/(app)/approvals/page.tsx` (`EmailApprovalSummary`, `CalendarApprovalSummary`).
  Behavior: Seeded email payloads use `body_preview`; the UI reads `body`. Seeded calendar payloads use `attendee` / `duration_minutes` / `purpose`; the UI requires `summary` plus `start_time` / `end_time`. Opening Approvals before a chat-created item shows To/Subject with no body, and no calendar preview. Chat-created approvals match the UI.
  Why it matters: Approvals is on the recruiter path. Empty previews look unfinished.
  Smallest fix: Align seeded payload keys with the UI (`body`, `summary`, `start_time`, `end_time`, `attendees`), or teach the UI to also read the seeded field names.

- Leads table order fights the agent ranking.
  Path: `backend/src/onepilot/repositories/leads.py` (`list_for_org` orders by `created_at DESC`); ranking in `backend/src/onepilot/services/crm_email_grounding.py` `rank_leads()`; table in `frontend/src/app/(app)/leads/page.tsx`.
  Behavior: Seed inserts Sarah Chen first and Kevin Park last, so the table can show Kevin Park on top while chat names Sarah Chen / Brightline Analytics as most promising.
  Why it matters: Opening Leads after the “most promising lead” chip creates an apparent contradiction.
  Smallest fix: Sort the Leads list with the same urgency/stage/name rule as `rank_leads()`, or label the table as recency and show the ranked “most promising” lead separately.

## P2 / deferred

- User menu / Settings show a generated demo email (`usr_demo_…@demo.onepilot.local`) in `frontend/src/app/(app)/layout.tsx` and `frontend/src/app/(app)/settings/page.tsx`; issued by `backend/src/onepilot/demo_data/seed.py` `create_demo_visitor_principal`.
- Landing and login still offer Create a workspace / register (`frontend/src/app/page.tsx`, `frontend/src/app/(public)/login/page.tsx`, `backend/src/onepilot/api/routers/auth.py`). New orgs skip the demo token budget and get an empty workspace.
- Shared-demo visitors are Admin and can create leads or delete docs; lead seed is skip-if-present, so ranking can be skewed until an operator resets.
- Settings copy claims citations on every response (`frontend/src/app/(app)/settings/page.tsx`); Knowledge page has the same overclaim (`frontend/src/app/(app)/knowledge/page.tsx`). False for calendar/general chat.
- README test counts (703/126, dated 2026-07-20) are behind later merges.
- `docs/agent/CLOUD_HANDOFF.md` was stale at audit time.
- JWT in browser localStorage remains a documented XSS-class risk, not a new finding.
- Prompt-injection checks are regex-only (`backend/src/onepilot/security/prompt_injection.py`); safety depends on tool/approval architecture, which holds.
- Try the demo navigates to `/dashboard` (`frontend/src/lib/auth.tsx`) rather than AI Workspace; one extra click before chips.
- Demo visitors as Admin can approve their own and others’ mock actions; required for the HITL demo; side effects stay mock.
- Shared daily token budget is org-wide by design (one visitor can exhaust it for others).
- Repo default chat model remains `gpt-4o-mini` in docs/templates; production host uses `gpt-5-nano`.

## Tests / validation

- Read-only audit. No product tests were re-run as part of this publish.
- Existing automated coverage reviewed: `/demo/start` gating and conversation isolation (`backend/tests/test_demo_start.py`); tenant isolation; production mock/send startup rules; CRM email grounding; execution-trace sanitization; public-demo chat/search/token caps; starter-prompt routing.
- Live read-only checks at audit time: health/providers/runtime-config; CORS allowlist vs rejected other origin; public frontend 200; `/docs` 404; evaluation summary available with honest disclaimer.
- Publisher `--check` should be run on this report before push.

## Blockers

- None blocking publish of this existing audit.
- Product share recommendation remains READY AFTER SMALL FIXES (the four P1 items above).

## Recommended next step

Fix the four P1 items (Calendar mock copy/health, speech rate/budget or disable on public demo, seeded approval field names, Leads sort aligned with `rank_leads()`), then share the public demo with recruiters.

## Files changed

- n/a for the audit itself (read-only).
- This publish writes only `agent/cloud-state` (`docs/agent/LATEST_AGENT_REPORT.md` and archive). No product files on `main` or deployment branches.

## Production verification

- Audited product SHA: `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8` on both `origin/main` and `origin/deployment/public-demo` at audit time.
- Private live-Google pointer unchanged: `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332`.
- Live public backend reported production env, mock Gmail/Calendar, send disabled, calendar create disabled, `gpt-5-nano` live, Qdrant/Redis/Serper live.
- No Railway / Vercel / Qdrant / env changes were made.
