---
generated_utc: 2026-09-08T16:27:25Z
task_name: final-public-recruiter-demo-release
agent_mode: cloud
agent_model: cursor-grok-4.6-high
repository: Fejjii/OnePilot-AI
source_branch: main
source_sha: 72f91ac2bb75d35096379361f2dd4222114c2198
task_type: release
status: PASS
---

# Cloud Agent Report

Ref: `agent/cloud-state`  
Path: `docs/agent/LATEST_AGENT_REPORT.md`

This file is public/sanitized execution context. It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).

## Work performed

- Fetched latest `main`, `deployment/public-demo`, and `deployment/live-google-demo`.
- Verified `origin/main` exactly equals `72f91ac2bb75d35096379361f2dd4222114c2198` (PR #41 merge).
- Verified `origin/deployment/public-demo` was `2445400db7489830fcba205fabcaac22644e4d72`, an ancestor of `main`, and fast-forward-safe (0 unique commits on the pointer).
- Re-verified public-demo safety on that SHA (code review + tests). Safety-relevant files were unchanged between `2445400` and `72f91ac`.
- Fast-forwarded `deployment/public-demo` to exact `main` with a non-force push (`2445400..72f91ac`). No merge commit.
- Did not move `deployment/live-google-demo` (`04e9df2e`).
- Did not alter Railway/Vercel env, OAuth, credentials, Postgres, Redis, Qdrant, Serper, or OpenAI configuration.
- No product code changes, no feature branch, no PR.

## Important findings

- Old public-demo ref: `2445400db7489830fcba205fabcaac22644e4d72`
- New public-demo ref: `72f91ac2bb75d35096379361f2dd4222114c2198`
- `origin/main` == `origin/deployment/public-demo` == `72f91ac2`
- Commits newly on the public pointer: PR #40 (web-search exact target language) and PR #41 (premium landing hero).
- Public safety verdict: **READY FOR FINAL PUBLIC SMOKE TEST.**
- `PUBLIC_DEMO_ENABLED` still forces Gmail mock and Calendar mock at factory, org resolver, and production startup validation. Production also requires `GMAIL_SEND_ENABLED=false`. Public + private live-Google cannot combine.
- HITL remains required for Gmail draft/send and calendar create. Live Google side effects are not reachable on the public track.
- Public RAG, web research, and CRM/lead logic remain enabled. Speech transcription remains disabled (`SPEECH_DISABLED`) and the microphone is hidden in demo mode.
- Public rate/token protections unchanged (`PUBLIC_DEMO_CHAT_PER_IP_PER_MINUTE=20`, chat/day 200, web/IP 5, web/day 300, daily token budget 250000).
- Live public runtime (read-only `/health` + `/runtime/config`, env not changed): `chat_model=gpt-5-nano`, `gmail_mode=mock`, `calendar_mode=mock`, `gmail_send_enabled=false`, `public_demo_enabled=true`, `private_live_google_enabled=false`, Serper/Qdrant/Redis live.
- `docs/agent/CLOUD_HANDOFF.md` on `main` still describes pre-release SHAs and open PR #41. Not updated here (no product commit/PR). Next Mac sync should refresh it.

## P0 blockers

- None.

## P1 issues

- None.

## P2 / deferred

- Refresh committed `CLOUD_HANDOFF.md` on a later product commit so canonical/public SHAs match this release.
- Remaining audit P2 items stay deferred (demo email display, optional self-register, shared-org Admin, citations-overclaim copy).

## Tests / validation

- GitHub CI on `main` @ `72f91ac`: success (run `34249667432`).
- Local public-safety pytest: **147 passed** (`test_private_live_google`, `test_public_demo_limits`, `test_speech_transcription`, `test_demo_start`, `test_public_demo_approval_hygiene`, `test_provider_diagnostics`, `test_calendar_diagnostics`, `test_release_last_mile_demo_quality`, `test_crm_email_grounding`, `test_agent_memory`, `test_tools_registry`, `test_gmail_provider`).
- GitHub CI on `deployment/public-demo` @ `72f91ac`: triggered (run `34251093141`; queued/in progress at report time). Same SHA already green on `main`.
- Host auto-deploys triggered by the branch fast-forward (no console/env changes): Railway statuses pending/success; Vercel `one-pilot-ai` deploying. A second Vercel project named `onepilot-private-demo` also showed a pending deploy from this same git hook; no env/OAuth/secrets were changed.

## Blockers

- None.

## Recommended next step

Run the final public recruiter smoke test on `https://one-pilot-ai.vercel.app` after the Vercel/Railway deploys for `72f91ac` complete. Do not move `deployment/live-google-demo`. Do not change host env.

## Files changed

- n/a product. Git pointer only: `deployment/public-demo` fast-forwarded `2445400` → `72f91ac`.

## Production verification

| Item | Status |
|------|--------|
| `origin/main` | `72f91ac2bb75d35096379361f2dd4222114c2198` |
| `origin/deployment/public-demo` old | `2445400db7489830fcba205fabcaac22644e4d72` |
| `origin/deployment/public-demo` new | `72f91ac2bb75d35096379361f2dd4222114c2198` |
| Fast-forward | yes (`2445400..72f91ac`, no force, no merge commit) |
| `origin/deployment/live-google-demo` | `04e9df2e05f56d0733c7f7d76b32c4ab1a7e3332` (untouched) |
| Safety verdict | READY FOR FINAL PUBLIC SMOKE TEST |
| Deployment trigger | GitHub CI + Railway + Vercel auto-deploys started from the pointer update |
| Host env / OAuth / data stores | not modified |

Operator smoke test should wait until Vercel `one-pilot-ai` and the Railway backend deploy finish, then run `python scripts/smoke_test_public_demo.py --base-url https://onepilot-ai-production.up.railway.app` (never print tokens) plus the landing **Try the demo** path.
