# Cloud agent handoff (sanitized)

Generated: 2026-09-03 15:24 UTC  
Generator: `scripts/sync_cloud_handoff.py` (does **not** commit or push)

This file is the **only** committed project-state brief for Cursor Cloud / phone agents.
It is intentionally smaller than any local `HANDOFF.md` and contains **no secrets**.

No local `HANDOFF.md` was available. Task sections use repo defaults and/or the previous Cloud file.


## How to read this file

| Layer | What it is | Cloud can use it? |
|-------|------------|-------------------|
| **Canonical repository** | `main` at the SHA below | Yes — default base for product work |
| **Deployed public-demo** | `deployment/public-demo` (Vercel + Railway, mock Gmail/Calendar) | Read SHAs only. Do not push/fast-forward unless explicitly authorized |
| **Private live-demo** | `deployment/live-google-demo` (live Google OAuth track) | **No** unless the operator names that branch and authorizes the change |
| **User-gated operations** | Railway / Vercel / Qdrant Cloud / production env vars | **No** — operator does this in host consoles |
| **Local-only state** | `HANDOFF.md`, `.ai/`, `CHANGELOG_SESSION.md`, git stash, iCloud, local `.env` | **Invisible** to Cloud. Never assume it exists |

## Canonical and deployment SHAs

| Ref | SHA | Notes |
|-----|-----|-------|
| `origin/main` (canonical) | `1c3dd0172250891d71f89c21a4a57e6002a5119d` | Product source of truth |
| `origin/deployment/public-demo` | `1c3dd0172250891d71f89c21a4a57e6002a5119d` | matches `main` (thin deploy pointer) |
| `origin/deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` | Private live-Google pointer; **do not modify** |

## Completed

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

- **This file** is the sanitized Cloud/mobile handoff context. Local `HANDOFF.md` (gitignored) remains authoritative for private/local state.
- Public infrastructure is essentially complete (OP-026 COMPLETE; public demo Qdrant cleaned).
- Next product phase: recruiter-facing public demo polish (audit, refinement, wording, and final checklist alignment).
- Private live-Google demo remains a later user-gated track (Cloud must not assume OAuth or live Google access).
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
- Public demo: Vercel frontend + Railway API/Postgres/Redis; Gmail/Calendar **mock**; shared-demo agent memory disabled.
- Private live-Google track exists on `deployment/live-google-demo` and is **user-gated**. Cloud must not assume OAuth or live Google access.
- Vectors: Qdrant when configured, in-memory fallback otherwise. Cloud must not target live Qdrant clusters.

## Tests / status

- Documented counts in README (2026-07-20): **703** backend tests (3 skipped), **126** frontend tests. Later merges added Qdrant/OpenAI coverage — trust current CI on `main`.
- CI (`.github/workflows/ci.yml`) runs backend pytest + frontend typecheck/tests/build on PRs to `main` and `deployment/**`.
- Public-demo smoke: `python scripts/smoke_test_public_demo.py --base-url <public-api>` (never print tokens).
- Cloud-handoff sync tests: `python -m pytest -q scripts/tests`

## Protected branches and do-not-touch

Cloud (and any agent) must **not** touch:

- `deployment/public-demo` and `deployment/live-google-demo` (no checkout-for-edit, no force-push, no fast-forward) unless the operator explicitly authorizes that exact branch
- Live **Qdrant**, **Railway**, **Vercel**, production env vars, or application deployment
- OP-026 is COMPLETE — do not re-run or modify live-Qdrant work
- git `stash` (including `stash@{0}`)
- gitignored local files: `.ai/`, `HANDOFF.md`, `CHANGELOG_SESSION.md`, `.env`, `.env.local`

`main` is canonical. All product changes go on a feature/fix branch, then a PR into `main`. Do not merge unless asked.

## Recommended next task

Recommended next Cloud-safe task: a scoped product/fix branch off `main` from the near-term list in `docs/limitations_roadmap.md`, after the operator names the task.

OP-026 is complete; do not re-run live Qdrant or modify deployment branches unless the operator explicitly authorizes that exact branch.

## Local-only reminder

Cloud cannot see the operator's Mac stash, iCloud copies, local `.ai/` notes, or private `HANDOFF.md`. If something is missing here, it is local-only or user-gated — ask; do not invent access.
