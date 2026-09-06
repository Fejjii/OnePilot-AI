# Cloud agent handoff (sanitized)

Generated: 2026-09-06 11:20 UTC  
Generator: Cloud agent (manual, sanitized; private live-Google v1 on `feat/private-live-google-v1`; no local `HANDOFF.md`)

This file is the **only** committed project-state brief for Cursor Cloud / phone agents.
It is intentionally smaller than any local `HANDOFF.md` and contains **no secrets**.

`CLOUD_HANDOFF.md` is project-state context. The latest Cloud execution/result
lives at `agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md`. Do not conflate the two.


## How to read this file

| Layer | What it is | Cloud can use it? |
|-------|------------|-------------------|
| **Canonical repository** | `main` at the SHA below | Yes — default base for product work |
| **Deployed public-demo** | `deployment/public-demo` (Vercel + Railway, mock Gmail/Calendar) | Read SHAs only. Do not push/fast-forward unless explicitly authorized |
| **Private live-demo** | `deployment/live-google-demo` (legacy pointer) | **No** unless the operator names that branch and authorizes the change. Implementation now lives on `main` via `PRIVATE_LIVE_GOOGLE_ENABLED` |
| **User-gated operations** | Railway / Vercel / Qdrant Cloud / production env vars | **No** — operator does this in host consoles |
| **Local-only state** | `HANDOFF.md`, `.ai/`, `CHANGELOG_SESSION.md`, git stash, iCloud, local `.env` | **Invisible** to Cloud. Never assume it exists |
| **Latest Cloud agent report** | `agent/cloud-state` → `docs/agent/LATEST_AGENT_REPORT.md` | Yes — last execution/result only. Not project state and not a product/deploy branch |

## Canonical and deployment SHAs

| Ref | SHA | Notes |
|-----|-----|-------|
| `origin/main` (canonical) | `1cd9abbc1eaec6022a17826e5fc4269797c40828` | Task-start SHA. Includes PR #34 (recruiter demo package) |
| `origin/deployment/public-demo` | `87eef7d5c2565181b94aff06be97374b22bdf4f9` | Product SHA behind `main` by docs-only commits. **READY TO SHARE**. Do not fast-forward |
| `origin/deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` | Legacy private pointer; **untouched**. No unique commits vs `main` |
| `feat/private-live-google-v1` (this work) | see latest commit on that branch | Private live-Google prep PR into `main`; do not merge unless asked |

`deployment/live-google-demo` is a stale ancestor of `main` (no unique code). Current `main` is authoritative. Do **not** move that pointer.

## Completed

- PR #34 — recruiter demo presentation package merged to `main`
- PR #33 — recruiter-facing README polish merged to `main`
- Public demo **READY TO SHARE** at `https://one-pilot-ai.vercel.app` (backend `https://onepilot-ai-production.up.railway.app`)
- OP-034 deployed and accepted (PR #32 merged; public-demo pointer remains `87eef7d5c2565181b94aff06be97374b22bdf4f9`)
- PR #31 — OP-033 final public-demo P1 audit fixes merged to `main`
- PR #30 — Cloud Agent report bridge merged to `main` (`infra/cloud-agent-report-bridge`)
- OP-032 — final recruiter-facing public-demo polish (merged to `main`, PR #29)
- Operator-authorized public-demo mutable-data cleanup restored the Sarah Chen / Brightline Analytics lead narrative in production (Kevin Park and Priya Nair urgency returned to canonical `medium`)
- OP-030 — recruiter-demo meetings vs availability polish (merged to `main`, PR #28)
- OP-031 — persist/render safe recruiter-facing agent execution traces + complete intent/tool badges (merged to `main`, PR #26)
- OP-028 — CRM-grounded email drafting + recruiter-facing approval copy (merged to `main`, PR #25)
- OP-027 / OP-029 — workspace insights focus + evaluation report polish (merged to `main`, PR #24)
- Cloud/mobile handoff infrastructure (merged to `main`, PR #23)
- OP-025 — deterministic UUID5 Qdrant point IDs for idempotent upsert (merged to `main`, PR #22)
- OP-026 — local/live Qdrant cleanup complete (public demo Qdrant cleaned: UUID4 duplicates removed; UUID5 deterministic vectors retained)
- OP-024 — `organization_id` payload index for strict-mode filtered Qdrant search (PR #21)
- OP-023 — empty `gpt-5-nano` completion handling for RAG and email drafts (PR #20)
- OP-022 — public-demo managed-provider enablement checklist (docs only; host env is user-gated)
- OP-015–OP-021 — shared-demo isolation, spend/abuse caps, workspace-insight routing
- OP-016 / OP-019 — OpenAI client timeouts/retries and secret redaction
- Public demo live on Vercel + Railway with **mock** Gmail/Calendar
- Canonical branch consolidation: `main` + thin `deployment/public-demo`

## Current task / in progress

- **Private live-Google v1** implemented on `feat/private-live-google-v1` and **not merged**. Smallest safe delta on current `main`:
  - `PRIVATE_LIVE_GOOGLE_ENABLED` + `PRIVATE_LIVE_GOOGLE_ORG_ID` select a private authenticated track
  - Explicit `GMAIL_PROVIDER_MODE=live` / `GOOGLE_CALENDAR_PROVIDER_MODE=live` fail closed without OAuth
  - `PUBLIC_DEMO_ENABLED` forces mock Gmail/Calendar even if OAuth env is present
  - Live Google is org-restricted on the private track; other orgs get isolated mocks
  - `/demo/start` stays off when the private track is enabled
  - Operator doc: `docs/private_demo/LIVE_GOOGLE_SETUP.md` (variable names only)
- Public demo behavior is unchanged: mock Gmail/send-disabled, mock Calendar, speech disabled, `gpt-5-nano` on the live public host. Do not change public production env.
- `origin/main` at task start: `1cd9abbc1eaec6022a17826e5fc4269797c40828`.
- `deployment/live-google-demo` remains untouched at `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332`. Audit found **no unique commits** vs `main`; nothing was ported from that pointer.
- Existing main already had real `GmailProvider` / `GoogleCalendarProvider`, shared OAuth refresh-token env, and HITL gates. This PR does not duplicate that architecture.
- Host configuration (Railway/Vercel/Google Cloud OAuth) remains **user-gated**. Cloud must not assume OAuth or live Google access.
- Product work belongs on a feature/fix branch off `main`, never on a deployment branch.

## Backlog

From `docs/limitations_roadmap.md` (near-term, product — pick explicitly):
- HTTP-only cookie auth with refresh tokens
- Real OpenAI streaming (SSE)
- Object storage for uploaded files
- Background task queue
- Optional demo-reset endpoint

Remaining audit P2 items (demo email display, optional self-register, shared-org Admin, citations-overclaim copy).

Do **not** treat host-console work (Railway / Vercel / Qdrant Cloud env) as Cloud-agent work.

## Architecture state

- Multi-tenant FastAPI + Next.js workspace: LangGraph agent, RAG + citations, HITL approvals, usage/quotas, memory.
- Assistant messages persist a sanitized `execution_trace` (observable steps only). Internal graph details, prompts, tokens, and secrets are not shown in the recruiter UI.
- Email drafts resolve org-scoped CRM leads when present and must not invent customer facts. Human approval is still required; public Gmail stays mock/send-disabled.
- Workspace insights, CRM email drafting, and recruiter-facing lead listing share `rank_leads()`. Seeded demo data makes Sarah Chen at Brightline Analytics the most promising lead. That narrative is restored in production.
- Public demo: Vercel frontend + Railway API/Postgres/Redis; Gmail/Calendar **mock**; speech transcription disabled; shared-demo agent memory disabled.
- Forced Calendar mock is reported as healthy simulated mode. Missing OAuth in that mode is not a provider outage.
- Seeded Approvals email/calendar payloads use the same preview fields as chat-created approvals.
- Public-demo `/demo/start` refreshes canonical curated approvals and, when `PUBLIC_DEMO_ENABLED=true`, also removes stale non-curated demo-visitor residue older than 6 hours. Recent active-session approvals are preserved. No public approval DELETE route.
- Private live-Google is now a **config track on `main`** (`PRIVATE_LIVE_GOOGLE_ENABLED`), not a deployment-branch codebase. The `deployment/live-google-demo` pointer is legacy and still must not be moved unless the operator explicitly authorizes that branch.
- Vectors: Qdrant when configured, in-memory fallback otherwise. Cloud must not target live Qdrant clusters.
- Recruiter presentation package lives under `docs/portfolio/` (`ARCHITECTURE_OVERVIEW.md`, `RECRUITER_DEMO_SCRIPT.md`, `RECORDING_CHECKLIST.md`, `INTERVIEW_CHEAT_SHEET.md`).
- Cloud execution reports are public/sanitized and live only on `agent/cloud-state`. Cloud cannot write iCloud.

## Tests / status

- Latest green CI on `main` @ `87eef7d5c2565181b94aff06be97374b22bdf4f9` (run 34020499895): backend **821 passed, 3 skipped**; frontend **171 passed** (30 files); scripts **53 passed**. README uses durable wording (**800+** / **170+**).
- This branch adds `backend/tests/test_private_live_google.py` plus fail-closed provider/startup coverage. Validation counts are recorded after the test run.
- CI (`.github/workflows/ci.yml`) runs backend pytest + frontend typecheck/tests/build on PRs to `main` and `deployment/**`, plus `scripts/tests`.
- Public-demo smoke: `python scripts/smoke_test_public_demo.py --base-url <public-api>` (never print tokens).
- Cloud-handoff / report-bridge tests: `python -m pytest -q scripts/tests`

## Protected branches and do-not-touch

Cloud (and any agent) must **not** touch:

- `deployment/public-demo` and `deployment/live-google-demo` (no checkout-for-edit, no force-push, no fast-forward) unless the operator explicitly authorizes that exact branch
- Live **Qdrant**, **Railway**, **Vercel**, production env vars, or application deployment
- OP-026 is COMPLETE — do not re-run or modify live-Qdrant work
- git `stash` (including `stash@{0}`)
- gitignored local files: `.ai/`, `HANDOFF.md`, `CHANGELOG_SESSION.md`, `.env`, `.env.local`

`main` is canonical. All product changes go on a feature/fix branch, then a PR into `main`. Do not merge unless asked.

`agent/cloud-state` is a reporting ref, not a product branch. Publish reports with `scripts/publish_cloud_agent_report.py` only. Never force-push.

## Recommended next task

Review and merge `feat/private-live-google-v1` if the private-track gates are accepted. After merge, **Sofien** still must create a dedicated Google demo account, enable Gmail + Calendar APIs, generate a refresh token on an operator machine, and set env names from `docs/private_demo/LIVE_GOOGLE_SETUP.md` on a **new** private Railway/Vercel host. Do not change the public production env. Do not move `deployment/public-demo` or `deployment/live-google-demo` unless explicitly authorized. Keep public `gpt-5-nano`. Remaining P2 audit items stay deferred.

Do not re-run live Qdrant or modify deployment branches unless the operator explicitly authorizes that exact branch.

Suggested model: a Cloud-capable coding model, on a scoped feature/fix branch off `main` for product work. Read-only audits publish only to `agent/cloud-state`.

## Local-only reminder

Cloud cannot see the operator's Mac stash, iCloud copies, local `.ai/` notes, or private `HANDOFF.md`. If something is missing here, it is local-only or user-gated — ask; do not invent access.
