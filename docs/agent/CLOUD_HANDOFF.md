# Cloud agent handoff (sanitized)

Generated: 2026-09-05 11:20 UTC  
Generator: Cloud agent (manual, sanitized; reporting bridge on `infra/cloud-agent-report-bridge`; no local `HANDOFF.md`)

This file is the **only** committed project-state brief for Cursor Cloud / phone agents.
It is intentionally smaller than any local `HANDOFF.md` and contains **no secrets**.

`CLOUD_HANDOFF.md` is project-state context. The latest Cloud execution/result
lives at `agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md` after that ref is
bootstrapped. Do not conflate the two.


## How to read this file

| Layer | What it is | Cloud can use it? |
|-------|------------|-------------------|
| **Canonical repository** | `main` at the SHA below | Yes — default base for product work |
| **Deployed public-demo** | `deployment/public-demo` (Vercel + Railway, mock Gmail/Calendar) | Read SHAs only. Do not push/fast-forward unless explicitly authorized |
| **Private live-demo** | `deployment/live-google-demo` (live Google OAuth track) | **No** unless the operator names that branch and authorizes the change |
| **User-gated operations** | Railway / Vercel / Qdrant Cloud / production env vars | **No** — operator does this in host consoles |
| **Local-only state** | `HANDOFF.md`, `.ai/`, `CHANGELOG_SESSION.md`, git stash, iCloud, local `.env` | **Invisible** to Cloud. Never assume it exists |
| **Latest Cloud agent report** | `agent/cloud-state` → `docs/agent/LATEST_AGENT_REPORT.md` | Yes — last execution/result only. Not project state and not a product/deploy branch. Ref is not bootstrapped until after this infra PR merges |

## Canonical and deployment SHAs

| Ref | SHA | Notes |
|-----|-----|-------|
| `origin/main` (canonical) | `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8` | Includes PR #29 (OP-032). Public release source |
| `origin/deployment/public-demo` | `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8` | Matches `main` (thin deploy pointer). Public release succeeded |
| `origin/deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` | Private live-Google pointer; **untouched** |
| `infra/cloud-agent-report-bridge` (this work) | see latest commit on that branch | Reporting infrastructure PR into `main`; do not merge unless asked |

## Completed

- OP-032 — final recruiter-facing public-demo polish (merged to `main`, PR #29)
- Public release of `deployment/public-demo` fast-forwarded to `main` at `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8` (succeeded)
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

- **Cloud agent report bridge** implemented on `infra/cloud-agent-report-bridge` and **not yet merged**. Adds sanitized Cloud → GitHub (`agent/cloud-state`) → Mac/iCloud import. `agent/cloud-state` is not bootstrapped in this PR.
- OP-032 is merged to `main` (PR #29). `origin/main` and `origin/deployment/public-demo` are both `b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8`. Public release succeeded.
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

Do **not** treat host-console work (Railway / Vercel / Qdrant Cloud env) as Cloud-agent work.

## Architecture state

- Multi-tenant FastAPI + Next.js workspace: LangGraph agent, RAG + citations, HITL approvals, usage/quotas, memory.
- Assistant messages persist a sanitized `execution_trace` (observable steps only). Internal graph details, prompts, tokens, and secrets are not shown in the recruiter UI.
- Email drafts resolve org-scoped CRM leads when present and must not invent customer facts. Human approval is still required; public Gmail stays mock/send-disabled.
- Workspace insights and CRM email drafting share the same lead-ranking rule. Seeded demo data makes Sarah Chen at Brightline Analytics the most promising lead.
- Public demo: Vercel frontend + Railway API/Postgres/Redis; Gmail/Calendar **mock**; shared-demo agent memory disabled.
- Private live-Google track exists on `deployment/live-google-demo` and is **user-gated**. Cloud must not assume OAuth or live Google access.
- Vectors: Qdrant when configured, in-memory fallback otherwise. Cloud must not target live Qdrant clusters.
- Cloud execution reports (when the reporting ref exists) are public/sanitized and live only on `agent/cloud-state`. Cloud cannot write iCloud.

## Tests / status

- Reporting-bridge validation on this branch: `python -m pytest -q scripts/tests` — **53 passed**.
- Documented counts in README (2026-07-20): **703** backend tests (3 skipped), **126** frontend tests. Later merges added Qdrant/OpenAI/CRM-email/execution-trace/OP-032 coverage.
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

After `infra/cloud-agent-report-bridge` is reviewed/merged: bootstrap `agent/cloud-state` once with `python scripts/publish_cloud_agent_report.py --bootstrap --input <sanitized-report.md>`. Do not create that ref during the infrastructure PR. Do not touch deployment branches unless explicitly authorized. Private live-Google demo remains later and user-gated.

Do not re-run live Qdrant or modify deployment branches unless the operator explicitly authorizes that exact branch.

Suggested model: a Cloud-capable coding model, on a scoped feature/fix branch off `main` for product work. Read-only audits publish only to `agent/cloud-state`.

## Local-only reminder

Cloud cannot see the operator's Mac stash, iCloud copies, local `.ai/` notes, or private `HANDOFF.md`. If something is missing here, it is local-only or user-gated — ask; do not invent access.
