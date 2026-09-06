# Cloud agent handoff (sanitized)

Generated: 2026-09-06 07:20 UTC  
Generator: Cloud agent (manual, sanitized; OP-034 public-demo approval hygiene on `fix/op-034-demo-approval-hygiene`; no local `HANDOFF.md`)

This file is the **only** committed project-state brief for Cursor Cloud / phone agents.
It is intentionally smaller than any local `HANDOFF.md` and contains **no secrets**.

`CLOUD_HANDOFF.md` is project-state context. The latest Cloud execution/result
lives at `agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md`. Do not conflate the two.


## How to read this file

| Layer | What it is | Cloud can use it? |
|-------|------------|-------------------|
| **Canonical repository** | `main` at the SHA below | Yes — default base for product work |
| **Deployed public-demo** | `deployment/public-demo` (Vercel + Railway, mock Gmail/Calendar) | Read SHAs only. Do not push/fast-forward unless explicitly authorized |
| **Private live-demo** | `deployment/live-google-demo` (live Google OAuth track) | **No** unless the operator names that branch and authorizes the change |
| **User-gated operations** | Railway / Vercel / Qdrant Cloud / production env vars | **No** — operator does this in host consoles |
| **Local-only state** | `HANDOFF.md`, `.ai/`, `CHANGELOG_SESSION.md`, git stash, iCloud, local `.env` | **Invisible** to Cloud. Never assume it exists |
| **Latest Cloud agent report** | `agent/cloud-state` → `docs/agent/LATEST_AGENT_REPORT.md` | Yes — last execution/result only. Not project state and not a product/deploy branch |

## Canonical and deployment SHAs

| Ref | SHA | Notes |
|-----|-----|-------|
| `origin/main` (canonical) | `bc07c5595b6a21709be5dea2e271c8b9b4e635c6` | Task-start SHA. Includes PR #31 (OP-033) |
| `origin/deployment/public-demo` | `bc07c5595b6a21709be5dea2e271c8b9b4e635c6` | Same product SHA as `main` at task start. Do not fast-forward |
| `origin/deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` | Private live-Google pointer; **untouched** |
| `fix/op-034-demo-approval-hygiene` (this work) | see latest commit on that branch | OP-034 PR into `main`; do not merge unless asked |

## Completed

- PR #31 — OP-033 final public-demo P1 audit fixes merged to `main`
- PR #30 — Cloud Agent report bridge merged to `main` (`infra/cloud-agent-report-bridge`)
- OP-032 — final recruiter-facing public-demo polish (merged to `main`, PR #29)
- Public release of `deployment/public-demo` at `bc07c5595b6a21709be5dea2e271c8b9b4e635c6` (matches `main` at OP-034 task start)
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

- **OP-034** implemented on `fix/op-034-demo-approval-hygiene` and **not merged**. Adds automatic public-demo approval hygiene on `/demo/start` and the existing demo-refresh path.
- Remaining recruiter-demo issue after the production lead restore: the shared public-demo Approvals inbox accumulated stale non-curated demo-visitor residue from previous reviewer sessions. Canonical seeded approvals were already correct. OP-034 removes only stale, non-curated, demo-visitor-created approvals in the public demo organization when `PUBLIC_DEMO_ENABLED=true`, using a 6-hour retention window. No public DELETE endpoint. No production database mutation in this implementation task.
- `origin/main` and `origin/deployment/public-demo` at task start were `bc07c5595b6a21709be5dea2e271c8b9b4e635c6`.
- `deployment/live-google-demo` remains untouched at `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332`.
- Public infrastructure is essentially complete (OP-026 COMPLETE). Private live-Google demo remains a later user-gated track (Cloud must not assume OAuth or live Google access).
- Product work belongs on a feature/fix branch off `main`, never on a deployment branch.

## Backlog

From `docs/limitations_roadmap.md` (near-term, product — pick explicitly):
- HTTP-only cookie auth with refresh tokens
- Real OpenAI streaming (SSE)
- Object storage for uploaded files
- Background task queue
- Optional demo-reset endpoint

Audit P2 items remain deferred (demo email display, optional self-register, shared-org Admin, citations-overclaim copy, README test counts).

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
- Private live-Google track exists on `deployment/live-google-demo` and is **user-gated**. Cloud must not assume OAuth or live Google access.
- Vectors: Qdrant when configured, in-memory fallback otherwise. Cloud must not target live Qdrant clusters.
- Cloud execution reports are public/sanitized and live only on `agent/cloud-state`. Cloud cannot write iCloud.

## Tests / status

- OP-034 validation on this branch: targeted hygiene/demo-start/approvals tests **45 passed**; full backend **821 passed, 3 skipped**; `python -m pytest -q scripts/tests` — **53 passed**; handoff sanitizer `--check --no-fetch` — **ok**. No frontend changes.
- Documented counts in README (2026-07-20): **703** backend tests (3 skipped), **126** frontend tests. Later merges added Qdrant/OpenAI/CRM-email/execution-trace/OP-032/OP-033 coverage.
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

Review and merge OP-034 (`fix/op-034-demo-approval-hygiene`) if accepted. After merge, only an operator-authorized fast-forward of `deployment/public-demo` would ship automatic approval hygiene to the live public demo. Existing leftover rows older than 6 hours are then removed on the next `/demo/start`. Do not touch that branch unless explicitly authorized. Private live-Google demo remains later and user-gated. P2 audit items stay deferred.

Do not re-run live Qdrant or modify deployment branches unless the operator explicitly authorizes that exact branch.

Suggested model: a Cloud-capable coding model, on a scoped feature/fix branch off `main` for product work. Read-only audits publish only to `agent/cloud-state`.

## Local-only reminder

Cloud cannot see the operator's Mac stash, iCloud copies, local `.ai/` notes, or private `HANDOFF.md`. If something is missing here, it is local-only or user-gated — ask; do not invent access.
