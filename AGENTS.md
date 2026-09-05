# Agent instructions (OnePilot AI)

Read **`docs/agent/CLOUD_HANDOFF.md` first** on every Cloud or phone session. Then `docs/agent/CLOUD_WORKFLOW.md` if you need the Local ↔ Cloud loop. Report contract: `docs/agent/AGENT_REPORTS.md`.

## Canonical branch

- **`main` is canonical.** Product changes go on a feature/fix branch, then a PR into `main`.
- Do not merge unless the operator asks.

## Deployment branches (protected)

- Never modify `deployment/live-google-demo` unless the operator **explicitly** names that branch and authorizes the change.
- Never modify `deployment/public-demo` the same way (no fast-forward, force-push, or drive-by commits) unless explicitly authorized.
- Read-only `git fetch` / `git rev-parse` of those refs is allowed.

## Reporting ref (not a product branch)

- `agent/cloud-state` stores sanitized Cloud-agent **execution/result** reports only.
- Latest report path: `docs/agent/LATEST_AGENT_REPORT.md`
- Never treat it as a product or deployment branch. Never force-push it.
- Do not use a `main` PR merely to publish a runtime report.

## Local-only state (Cloud cannot see this)

- Never assume access to git stash (including `stash@{0}`), `.ai/`, `HANDOFF.md`, `CHANGELOG_SESSION.md`, iCloud copies, or local `.env`.
- Those paths are gitignored. If a fact is missing from `CLOUD_HANDOFF.md`, it is local-only or user-gated — ask; do not invent access.
- Cloud **must not** attempt to write iCloud. GitHub is the only Cloud → Mac bridge.

## Secrets

- Never print, commit, or log secrets, tokens, JWTs, connection strings, or raw env values.
- User-gated host work (Railway, Vercel, Qdrant Cloud, production env vars) is **out of scope** unless the operator explicitly authorizes that console work.
- Every committed Cloud report is public. Fail closed if secret-like material remains.

## Do not touch

- Live Qdrant data or clusters
- Railway / Vercel / application deployment
- OP-026 and any in-flight live-data task named in `CLOUD_HANDOFF.md`
- `deployment/public-demo` and `deployment/live-google-demo` without explicit authorization

## Before finishing Cloud work

Produce a sanitized final agent report (template: `docs/agent/AGENT_REPORT_TEMPLATE.md`).

### Product feature / fix

- Normal feature branch + PR rules remain unchanged.
- Update `docs/agent/CLOUD_HANDOFF.md` inside the **same** product PR when project state changed.
- Additionally publish the Cloud agent report to `agent/cloud-state` after the run when the reporting infrastructure is available:

  `python scripts/publish_cloud_agent_report.py --input report.md`

### Read-only audit / review

- No product branch or PR is required.
- Do not modify product code.
- Publish only the sanitized agent report through `agent/cloud-state`.

### Release operations

- Report exact refs, status, and test findings.
- Publish a sanitized report.
- Never expose secrets.

`CLOUD_HANDOFF.md` remains project-state context.  
`LATEST_AGENT_REPORT.md` is execution/result context. Do not conflate them.

Prefer `python scripts/sync_cloud_handoff.py` when a local `HANDOFF.md` exists; otherwise edit the Cloud file directly and keep it sanitized. The sync script does **not** commit or push — do that explicitly after reviewing the diff.

Workflow detail: `docs/agent/CLOUD_WORKFLOW.md`.
