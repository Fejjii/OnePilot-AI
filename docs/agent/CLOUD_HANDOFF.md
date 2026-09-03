# Cloud agent handoff (sanitized)

Generated: 2026-09-03 21:40 UTC  
Generator: Cloud agent (manual, sanitized; no local `HANDOFF.md`)

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
| `origin/main` (canonical) | `f73668924becc7619b05e3e6723e3626ead13677` | Product source of truth (includes OP-027/OP-029) |
| `origin/deployment/public-demo` | `1c3dd0172250891d71f89c21a4a57e6002a5119d` | Thin deploy pointer; **behind `main`**; do not fast-forward unless authorized |
| `origin/deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` | Private live-Google pointer; **do not modify** |
| `polish/op-031` (this work) | see latest commit on that branch | OP-031 PR #26 into `main`; do not merge unless asked |

## Completed

- OP-031 — persist/render safe recruiter-facing agent execution traces + complete intent/tool badges (PR #26, `polish/op-031`; not merged)
- OP-028 — complete and merged (operator-confirmed)
- OP-027 / OP-029 — workspace insights focus + eval reports (merged to `main`, PR #24)
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

- **OP-031** implemented on `polish/op-031` (PR #26). Awaits review; do not merge unless asked.
- Public infrastructure is essentially complete (OP-026 COMPLETE; public demo Qdrant cleaned).
- Recruiter-facing public demo polish continues after OP-031 (wording, checklist alignment) when the operator names the next item.
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
- Assistant messages now persist a sanitized `execution_trace` (observable steps only). Internal graph details, prompts, tokens, and secrets are not shown in the recruiter UI.
- Public demo: Vercel frontend + Railway API/Postgres/Redis; Gmail/Calendar **mock**; shared-demo agent memory disabled.
- Private live-Google track exists on `deployment/live-google-demo` and is **user-gated**. Cloud must not assume OAuth or live Google access.
- Vectors: Qdrant when configured, in-memory fallback otherwise. Cloud must not target live Qdrant clusters.

## Tests / status

- OP-031 validation: backend **765 passed, 3 skipped**; frontend **155 passed**; `pnpm typecheck` and `pnpm build` passed.
- Documented counts in README (2026-07-20): **703** backend tests (3 skipped), **126** frontend tests. Later merges added coverage — trust current CI on `main`.
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

After OP-031 is reviewed/merged: remaining recruiter-facing public-demo polish (copy, checklist alignment) **or** a named item from the near-term list in `docs/limitations_roadmap.md`. Operator should name the next OP/task.

Do not re-run live Qdrant or modify deployment branches unless the operator explicitly authorizes that exact branch.

Suggested model: the same Cloud-capable coding model used for OP-031, on a scoped feature/fix branch off `main`.

## Local-only reminder

Cloud cannot see the operator's Mac stash, iCloud copies, local `.ai/` notes, or private `HANDOFF.md`. If something is missing here, it is local-only or user-gated — ask; do not invent access.
