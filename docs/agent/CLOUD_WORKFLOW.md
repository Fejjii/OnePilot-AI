# Cloud / mobile development workflow

Smallest safe path between a local Mac Cursor agent and a Cursor Cloud agent launched from a phone. The Mac may be offline after the handoff is published.

| File | Role | Git |
|------|------|-----|
| `HANDOFF.md` (repo root) | Full local/private session state | **gitignored** |
| `.ai/`, `CHANGELOG_SESSION.md` | Local scratch | **gitignored** |
| `docs/agent/CLOUD_HANDOFF.md` | Sanitized Cloud-visible state | **committed** |
| `scripts/sync_all_handoffs.sh` | Local → iCloud → Cloud wrapper | **committed** |
| `scripts/sync_cloud_handoff.py` | Local → Cloud sanitizer | committed |

`main` is canonical. Cloud never assumes access to stash, `.ai/`, iCloud, or local `.env`.

---

## Local → Cloud (Mac still online)

1. **Finish or checkpoint** the local session. Leave the tree in a known state (commit product work on its feature branch, or stash only if you accept that Cloud will not see the stash).
2. **Regenerate the normal local `HANDOFF.md`** with whatever the local agent already uses. This file stays private.
3. **Run the one-command handoff sync** (does not commit or push):

   ```bash
   make sync-handoffs
   ```

   This runs:
   - `~/.local/bin/sync-onepilot-handoff.sh` to sync repo `HANDOFF.md` → iCloud `HANDOFF.md`
   - verification (both HANDOFF files exist and iCloud mtime updates)
   - `python scripts/sync_cloud_handoff.py` to regenerate the committed, secret-sanitized `docs/agent/CLOUD_HANDOFF.md`
4. **Review the sanitized diff** of `docs/agent/CLOUD_HANDOFF.md`. Confirm no keys, JWTs, connection strings, or host-console values leaked. If the sanitizer exits non-zero, it refused to write — fix the local/iCloud handoff and re-run.
5. **Commit and push only the sanitized file** (and any intended product branch), explicitly:

   ```bash
   git add docs/agent/CLOUD_HANDOFF.md
   git commit -m "docs(agent): refresh sanitized cloud handoff"
   git push
   ```

6. **Launch a Cloud Agent from the phone** against this GitHub repo. Point it at `main` (or the branch that contains the updated `CLOUD_HANDOFF.md`). Tell it to read `docs/agent/CLOUD_HANDOFF.md` first. The Mac can go offline after the push is on the remote.

---

## iCloud HANDOFF.md vs docs/agent/CLOUD_HANDOFF.md

- iCloud `HANDOFF.md` is your private/local diary for the Mac Cursor agent (synced by `make sync-handoffs`).
- `docs/agent/CLOUD_HANDOFF.md` is the sanitized Cloud-visible context committed to git.
- They represent the same project state, but they are intentionally **not byte-identical**: `CLOUD_HANDOFF.md` is sanitized/redacted for Cloud safety and may omit other private/local-only sections.

Local/iCloud `HANDOFF.md` remains authoritative for private/local state; Cloud uses only the sanitized committed file.

---

## Phone / Cloud Agent

1. Open Cursor on the phone and start a Cloud Agent on `Fejjii/OnePilot-AI`.
2. Instruct: read `docs/agent/CLOUD_HANDOFF.md` and `AGENTS.md` before editing.
3. Work on a **feature/fix branch** off `main`. Do not edit `deployment/public-demo` or `deployment/live-google-demo` unless the operator named that branch and authorized it.
4. Do not touch Qdrant / Railway / Vercel / production env vars / OP-026 / live data. OP-026 is COMPLETE, but Cloud must still not re-run or modify live-data work.
5. Before finishing: update `docs/agent/CLOUD_HANDOFF.md` (completed / current / recommended next + SHAs if you fetched remotes). Re-run the sanitizer if a local `HANDOFF.md` exists in that environment; otherwise edit the Cloud file directly and keep it secret-free.
6. Commit, push the feature branch, open a PR into `main`. Do not merge unless asked.

---

## Cloud → Local (Mac back online)

1. Cloud Agent has pushed its branch (and updated `CLOUD_HANDOFF.md`).
2. On the Mac: `git fetch` and check out that branch.
3. Continue locally. **`HANDOFF.md` remains authoritative for local/private state** — merge Cloud's public facts into it by hand if useful. Do not treat `CLOUD_HANDOFF.md` as a full local diary.
4. Next time you hand back to the phone: update your private/local `HANDOFF.md` as needed, then run `make sync-handoffs` again to re-sync iCloud and regenerate the sanitized `docs/agent/CLOUD_HANDOFF.md`. Review the diff and commit/push the sanitized Cloud handoff.

---

## Security controls

- Sync script redacts keys, JWTs, bearer tokens, connection strings, vendor tokens, PEM blocks, and sensitive assignments.
- Fail-closed: residual secret-like patterns → non-zero exit, **output file not written**.
- Script never auto-commits or auto-pushes.
- Wrapper verifies that iCloud `HANDOFF.md` exists/looks valid and updates before running the sanitizer (fail-fast if missing/stale).
- Cloud file must distinguish canonical vs public-demo vs live-demo vs user-gated vs local-only.
- Tests: `python -m pytest -q scripts/tests`
