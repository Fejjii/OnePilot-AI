# Cloud agent handoff (sanitized)

Generated: 2026-09-05 12:35 UTC  
Generator: Cloud agent (manual, sanitized; OP-033 P1 fixes on `fix/op-033-final-audit-p1`; no local `HANDOFF.md`)

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
| `origin/main` (canonical) | `c6edf7c4df1b7689a5ba92249da20c5d18f9262b` | Task-start SHA. Includes PR #29 (OP-032) and PR #30 (Cloud Agent report bridge) |
| `origin/deployment/public-demo` | `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8` | Previous product release (OP-032). **Behind `main` by the reporting-bridge merge.** Do not fast-forward |
| `origin/deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` | Private live-Google pointer; **untouched** |
| `fix/op-033-final-audit-p1` (this work) | see latest commit on that branch | OP-033 P1 PR into `main`; do not merge unless asked |

## Completed

- PR #30 — Cloud Agent report bridge merged to `main` (`infra/cloud-agent-report-bridge`)
- OP-032 — final recruiter-facing public-demo polish (merged to `main`, PR #29)
- Public release of `deployment/public-demo` at `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8` (previous product release; still the live public pointer)
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

- **OP-033** implemented on `fix/op-033-final-audit-p1` and **not merged**. Fixes the four P1 items from the final public-demo audit (Calendar mock diagnostics, public-demo speech disable, seeded approval preview fields, Leads listing aligned with `rank_leads()`).
- PR #30 / Cloud Agent report bridge is merged. `origin/main` at task start was `c6edf7c4df1b7689a5ba92249da20c5d18f9262b`.
- Public deployment still corresponds to the previous product release (`origin/deployment/public-demo` = `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8`). It was not updated in this work.
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
- Workspace insights, CRM email drafting, and recruiter-facing lead listing share `rank_leads()`. Seeded demo data makes Sarah Chen at Brightline Analytics the most promising lead.
- Public demo: Vercel frontend + Railway API/Postgres/Redis; Gmail/Calendar **mock**; speech transcription disabled; shared-demo agent memory disabled.
- Forced Calendar mock is reported as healthy simulated mode. Missing OAuth in that mode is not a provider outage.
- Seeded Approvals email/calendar payloads use the same preview fields as chat-created approvals.
- Private live-Google track exists on `deployment/live-google-demo` and is **user-gated**. Cloud must not assume OAuth or live Google access.
- Vectors: Qdrant when configured, in-memory fallback otherwise. Cloud must not target live Qdrant clusters.
- Cloud execution reports are public/sanitized and live only on `agent/cloud-state`. Cloud cannot write iCloud.

## Tests / status

- OP-033 validation on this branch: backend **806 passed, 3 skipped**; frontend **171 passed**; `pnpm typecheck` and `pnpm build` passed; `python -m pytest -q scripts/tests` — **53 passed**.
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

Review and merge OP-033 (`fix/op-033-final-audit-p1`, PR #31) if accepted. After merge, only an operator-authorized fast-forward of `deployment/public-demo` would ship these P1s to the live public demo. Do not touch that branch unless explicitly authorized. Private live-Google demo remains later and user-gated. P2 audit items stay deferred.

Do not re-run live Qdrant or modify deployment branches unless the operator explicitly authorizes that exact branch.

Suggested model: a Cloud-capable coding model, on a scoped feature/fix branch off `main` for product work. Read-only audits publish only to `agent/cloud-state`.

## Local-only reminder

Cloud cannot see the operator's Mac stash, iCloud copies, local `.ai/` notes, or private `HANDOFF.md`. If something is missing here, it is local-only or user-gated — ask; do not invent access.
