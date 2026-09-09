# Cloud agent handoff (sanitized)

Generated: 2026-09-09 08:50 UTC  
Generator: Cloud agent (manual, sanitized; docs-only recruiter README polish; no local `HANDOFF.md`)

This file is the **only** committed project-state brief for Cursor Cloud / phone agents.
It is intentionally smaller than any local `HANDOFF.md` and contains **no secrets**.

`CLOUD_HANDOFF.md` is project-state context. The latest Cloud execution/result
lives at `agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md`. Do not conflate the two.


## How to read this file

| Layer | What it is | Cloud can use it? |
|-------|-----------|-------------------|
| **Canonical repository** | `main` at the SHA below | Yes — default base for product work |
| **Deployed public-demo** | `deployment/public-demo` (Vercel + Railway, mock Gmail/Calendar) | Read SHAs only. Do not push/fast-forward unless explicitly authorized |
| **Private live-demo** | `deployment/live-google-demo` (legacy pointer) | **No** unless the operator names that branch and authorizes the change. Implementation lives on `main` via `PRIVATE_LIVE_GOOGLE_ENABLED` |
| **User-gated operations** | Railway / Vercel / Qdrant Cloud / production env vars | **No** — operator does this in host consoles |
| **Local-only state** | `HANDOFF.md`, `.ai/`, `CHANGELOG_SESSION.md`, git stash, iCloud, local `.env` | **Invisible** to Cloud. Never assume it exists |
| **Latest Cloud agent report** | `agent/cloud-state` → `docs/agent/LATEST_AGENT_REPORT.md` | Yes — last execution/result only. Not project state and not a product/deploy branch |

## Canonical and deployment SHAs

| Ref | SHA | Notes |
|-----|-----|-------|
| `origin/main` (canonical) | `72f91ac2bb75d35096379361f2dd4222114c2198` | Includes PR #41 (landing premium hero) |
| `origin/deployment/public-demo` | `72f91ac2bb75d35096379361f2dd4222114c2198` | Observed matching `main` after fetch. **Do not push/fast-forward** unless authorized |
| `origin/deployment/live-google-demo` | `72f91ac2bb75d35096379361f2dd4222114c2198` | Observed matching `main` after fetch. This agent did **not** move it. **Do not push** unless authorized |

This Cloud session did not checkout, fast-forward, or push either deployment branch. Current `main` is still canonical for product work.

## Completed

- PR #41 — landing premium hero visual merged to `main` (`72f91ac`)
- PR #40 — public web-search / WEB_AND_KNOWLEDGE generated prose honors exact requested language (fr/de/es); merged to `main` (`a26bb15`)
- PR #39 — landing hero capability architecture merged to `main` (`2445400`)
- PR #38 — final product UX / i18n / recruiter polish merged to `main` (`716c3fa`)
- PR #37 — last-mile recruiter-demo quality merged to `main` (calendar title preservation, Gmail recipient + HITL draft gating, web-search synthesis polish)
- PR #36 — private-demo routing + response UX merged to `main`
- PR #35 — private live-Google v1 track merged to `main` (`PRIVATE_LIVE_GOOGLE_ENABLED`)
- PR #34 — recruiter demo presentation package merged to `main`
- PR #33 — recruiter-facing README polish merged to `main`
- Public demo **READY TO SHARE** at `https://one-pilot-ai.vercel.app` (backend `https://onepilot-ai-production.up.railway.app`)
- OP-034 deployed and accepted (PR #32 merged)
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

- **Docs-only recruiter README polish** on `docs/final-recruiter-readme` (PR #42). Follow-up: high-level architecture / HITL diagrams now split read-only vs approval-gated external actions. Engineering remains frozen.
- Goal: transform the root README into a premium recruiter/general-public entry point, with `docs/portfolio/ARCHITECTURE_OVERVIEW.md` as the 30–60 second next scan. Deep implementation stays in `docs/architecture.md` and related engineering docs.
- Accuracy constraints unchanged: do not claim MCP; do not claim HubSpot, Salesforce, Stripe, Slack, or Twilio are live; public Gmail/Calendar remain simulated; private Google remains live/org-restricted and is not a public CTA; Gmail send stays disabled; evaluation 100% figures are demo-quality regression checks, not a universal accuracy claim.
- Private host remains user-gated (`PRIVATE_LIVE_GOOGLE_ENABLED=true`, Gmail send disabled, Calendar create and Gmail draft approval-gated). This PR does **not** change Railway/Vercel env, OAuth, or deployment branches.
- `origin/main` at branch creation: `72f91ac2bb75d35096379361f2dd4222114c2198`.
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
- Two-stage routing: Stage 1 message class, Stage 2 intent. Calendar availability vs meetings vs scheduling are distinct tool inferences. Scheduling continuations use bounded same-conversation user history only; a continuation with no recoverable prior request clarifies instead of defaulting date/time/title.
- Assistant messages persist a sanitized `execution_trace` (observable steps only). Internal graph details, prompts, tokens, and secrets are not shown in the recruiter UI.
- Email drafts resolve org-scoped CRM leads when present and must not invent customer facts. An explicitly provided email is used as Recipient when no CRM name exists. Human approval is required before Gmail draft **or** send; public Gmail stays mock/send-disabled.
- Workspace insights, CRM email drafting, and recruiter-facing lead listing share `rank_leads()`. Seeded demo data makes Sarah Chen at Brightline Analytics the most promising lead. That narrative is restored in production.
- Public demo: Vercel frontend + Railway API/Postgres/Redis; Gmail/Calendar **mock**; speech transcription disabled on the anonymous public demo (available in authenticated/private mode); shared-demo agent memory disabled. `/demo/start` seeds NovaEdge knowledge-base documents, operational data, and curated approvals. NovaEdge Solutions is the sample demo customer, not OnePilot itself.
- Forced Calendar mock is reported as healthy simulated mode. Missing OAuth in that mode is not a provider outage.
- Seeded Approvals email/calendar payloads use the same preview fields as chat-created approvals.
- Public-demo `/demo/start` refreshes canonical curated approvals and, when `PUBLIC_DEMO_ENABLED=true`, also removes stale non-curated demo-visitor residue older than 6 hours. Recent active-session approvals are preserved. No public approval DELETE route.
- Private live-Google is a **config track on `main`** (`PRIVATE_LIVE_GOOGLE_ENABLED`), not a deployment-branch codebase. The `deployment/live-google-demo` pointer is legacy and still must not be moved unless the operator explicitly authorizes that branch.
- Vectors: Qdrant when configured, in-memory fallback otherwise. Cloud must not target live Qdrant clusters.
- Recruiter entry point is the root `README.md`. Next scan is `docs/portfolio/ARCHITECTURE_OVERVIEW.md`. Deep internals remain `docs/architecture.md`, `docs/agent_workflow.md`, `docs/rag_system.md`, `docs/data_architecture.md`. Portfolio kit also includes `RECRUITER_DEMO_SCRIPT.md`, `RECORDING_CHECKLIST.md`, `INTERVIEW_CHEAT_SHEET.md`.
- Cloud execution reports are public/sanitized and live only on `agent/cloud-state`. Cloud cannot write iCloud.
- Explicit response language (fr/de/es) controls WEB_SEARCH / WEB_AND_KNOWLEDGE generated Summary/findings. Wrong-language polish triggers a localization pass, then a language-safe fallback. Original Sources (titles, URLs, snippets) stay unchanged. AUTO still follows detected input language. RAG/email/calendar explicit-language behavior is unchanged.
- Public landing hero (merged via PR #41): compact operating-layer visual (Understand, Reason, Execute, Connect). Memory is labeled as authenticated/private. Payments and Communications are marked integration-ready. MCP and live HubSpot/Salesforce/Stripe/Slack/Twilio are not claimed.

## Tests / status

- Latest `main` @ `72f91ac2bb75d35096379361f2dd4222114c2198` includes PR #41 (landing premium hero) and PR #40 (web-search response language).
- Stable presentation wording for this release: **900+** backend tests, **180** frontend tests, **53** release/script tests, **79-case deterministic evaluation suite**.
- Evaluation labeled-set results remain demo-quality regression checks (intent/routing/RAG golden/citation/weak-evidence/safety 100%, source hit 90%, 0 failures). Not a production SLO and not a claim of universal 100% accuracy.
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

Review the docs-only recruiter README PR (`docs/final-recruiter-readme`) and merge only if accepted. Do not change the public production env. Do not move `deployment/public-demo` or `deployment/live-google-demo` unless explicitly authorized. Keep public `gpt-5-nano`. Keep `GMAIL_SEND_ENABLED=false`. Remaining P2 audit items stay deferred. Engineering remains frozen unless a new product task is named.

Do not re-run live Qdrant or modify deployment branches unless the operator explicitly authorizes that exact branch.

Suggested model: a Cloud-capable coding model, on a scoped feature/fix branch off `main` for product work. Read-only audits publish only to `agent/cloud-state`.

## Local-only reminder

Cloud cannot see the operator's Mac stash, iCloud copies, local `.ai/` notes, or private `HANDOFF.md`. If something is missing here, it is local-only or user-gated — ask; do not invent access.
