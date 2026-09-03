# Agent instructions (OnePilot AI)

Read **`docs/agent/CLOUD_HANDOFF.md` first** on every Cloud or phone session. Then `docs/agent/CLOUD_WORKFLOW.md` if you need the Local ↔ Cloud loop.

## Canonical branch

- **`main` is canonical.** Product changes go on a feature/fix branch, then a PR into `main`.
- Do not merge unless the operator asks.

## Deployment branches (protected)

- Never modify `deployment/live-google-demo` unless the operator **explicitly** names that branch and authorizes the change.
- Never modify `deployment/public-demo` the same way (no fast-forward, force-push, or drive-by commits) unless explicitly authorized.
- Read-only `git fetch` / `git rev-parse` of those refs is allowed.

## Local-only state (Cloud cannot see this)

- Never assume access to git stash (including `stash@{0}`), `.ai/`, `HANDOFF.md`, `CHANGELOG_SESSION.md`, iCloud copies, or local `.env`.
- Those paths are gitignored. If a fact is missing from `CLOUD_HANDOFF.md`, it is local-only or user-gated — ask; do not invent access.

## Secrets

- Never print, commit, or log secrets, tokens, JWTs, connection strings, or raw env values.
- User-gated host work (Railway, Vercel, Qdrant Cloud, production env vars) is **out of scope** unless the operator explicitly authorizes that console work.

## Do not touch

- Live Qdrant data or clusters
- Railway / Vercel / application deployment
- OP-026 and any in-flight live-data task named in `CLOUD_HANDOFF.md`
- `deployment/public-demo` and `deployment/live-google-demo` without explicit authorization

## Before finishing Cloud work

- Update `docs/agent/CLOUD_HANDOFF.md` (tasks + SHAs) when the session changed project state.
- Prefer `python scripts/sync_cloud_handoff.py` when a local `HANDOFF.md` exists; otherwise edit the Cloud file and keep it sanitized.
- The sync script does **not** commit or push — do that explicitly after reviewing the diff.

Workflow detail: `docs/agent/CLOUD_WORKFLOW.md`.
