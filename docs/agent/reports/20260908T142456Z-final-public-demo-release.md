---
generated_utc: 2026-09-08T14:24:56Z
task_name: final-public-demo-release
agent_mode: cloud
agent_model: cursor-grok-4.6-high
repository: Fejjii/OnePilot-AI
source_branch: main
source_sha: 2445400db7489830fcba205fabcaac22644e4d72
task_type: release
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

- Fetched `origin/main`, `origin/deployment/public-demo`, and `origin/deployment/live-google-demo`.
- Verified `origin/main` was exactly `2445400db7489830fcba205fabcaac22644e4d72` (merge of PR #39).
- Verified `origin/deployment/public-demo` started at `1efdf9bfaa6344b492e882428d55a7bc682d1c0f`, was an ancestor of `main`, and was fast-forward-safe (`0` unique commits on public-demo, `7` commits on `main`).
- Inspected public-demo safety on that exact `main` SHA. Provider/config guards were unchanged vs the previous public-demo pointer. Fast-forwarded `deployment/public-demo` to exact `main` (no `--force`).
- Did not modify product code, create a branch, open a PR, or move `deployment/live-google-demo`.
- Did not change Railway/Vercel env, OAuth, secrets, DB, Redis, Qdrant, or credentials.

## Important findings

- Final refs:
  - `origin/main` = `2445400db7489830fcba205fabcaac22644e4d72`
  - `origin/deployment/public-demo` = `2445400db7489830fcba205fabcaac22644e4d72`
  - `origin/deployment/live-google-demo` = `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (untouched)
- Divergence after release: `origin/deployment/public-demo...origin/main` = `0 0`.
- Tip message: `Merge pull request #39 from Fejjii/fix/landing-capability-architecture`.
- Fast-forward range (previous public-demo → new tip): PRs #38 and #39 plus follow-up landing/i18n commits. Safety-critical files (`config.py`, `providers/__init__.py`, Gmail/Calendar HITL tools) were unchanged except i18n plumbing on email draft generation.

## P0 blockers

- None.

## P1 issues

- None.

## P2 / deferred

- Host cutover on Vercel/Railway remains operator-gated. This run only moved the Git pointer.
- `docs/agent/CLOUD_HANDOFF.md` on `main` still describes the previous public-demo SHA. Not updated here (no product commit/PR authorized).
- Remaining P2 audit items and private live-Google host work stay deferred.

## Tests / validation

- Ref checks:
  - `git merge-base --is-ancestor origin/deployment/public-demo origin/main` — true before FF.
  - `git rev-list --left-right --count` before FF: `0 7`; after FF: `0 0`.
  - Push output: `1efdf9b..2445400` → `deployment/public-demo` (fast-forward, not force).
- Safety inspection on `2445400`:
  - `PUBLIC_DEMO_ENABLED` still short-circuits Gmail and Calendar factories to mock providers, including when OAuth/env would otherwise select live.
  - Org resolvers still return isolated mocks for public demo; `live_google_allowed_for_org` is false.
  - Production startup still requires `GMAIL_PROVIDER_MODE=mock`, `GOOGLE_CALENDAR_PROVIDER_MODE=mock`, and `GMAIL_SEND_ENABLED=false`. Combined public+private live-Google still fails closed.
  - Gmail send remains config-blocked (`send_disabled`). Email draft tool still sets `approval_required = True`. Calendar create still creates an approval and never writes the event directly.
- No product tests were added or re-run. No live host smoke. No secrets printed.

## Blockers

- None.

## Recommended next step

Operator: confirm Vercel/Railway picked up `deployment/public-demo` @ `2445400db7489830fcba205fabcaac22644e4d72` if a host cutover is desired. Do not move `deployment/live-google-demo`. Keep public `PUBLIC_DEMO_ENABLED=true`, mock Gmail/Calendar, and `GMAIL_SEND_ENABLED=false`. Optionally refresh `docs/agent/CLOUD_HANDOFF.md` SHAs in a later docs commit.

## Files changed

- Git ref only: `deployment/public-demo` fast-forwarded `1efdf9bfaa6344b492e882428d55a7bc682d1c0f` → `2445400db7489830fcba205fabcaac22644e4d72`.
- Product working tree: unchanged.

## Production verification

- Release verdict: **PASS**. Public-demo Git pointer now matches latest `main`.
- `deployment/live-google-demo` not modified.
- Railway/Vercel/env/OAuth/secrets/DB/Redis/Qdrant not modified. Host deploy, if auto-triggered by the branch pointer, is outside this Cloud run.
