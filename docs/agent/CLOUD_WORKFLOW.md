# Cloud / mobile development workflow

Smallest safe path between a local Mac Cursor agent and a Cursor Cloud agent launched from a phone. The Mac may be offline after the handoff is published.

Cloud **cannot** write iCloud or local `HANDOFF.md`. GitHub is the bridge.

| File / ref | Role | Git |
|------------|------|-----|
| `HANDOFF.md` (repo root) | Full local/private session state | **gitignored** |
| `.ai/`, `CHANGELOG_SESSION.md` | Local scratch | **gitignored** |
| `docs/agent/CLOUD_HANDOFF.md` | Sanitized Cloud-visible **project state** | **committed** on product branches |
| `agent/cloud-state` → `docs/agent/LATEST_AGENT_REPORT.md` | Sanitized Cloud **execution/result** | **committed** only on the reporting ref |
| `scripts/sync_all_handoffs.sh` | GitHub report → local HANDOFF → iCloud → Cloud wrapper | **committed** |
| `scripts/sync_cloud_handoff.py` | Local → Cloud sanitizer | committed |
| `scripts/publish_cloud_agent_report.py` | Cloud → `agent/cloud-state` publisher | committed |
| `scripts/import_cloud_agent_report.py` | GitHub report → marked local HANDOFF section | committed |

`main` is canonical. Cloud never assumes access to stash, `.ai/`, iCloud, or local `.env`.

Full report contract: `docs/agent/AGENT_REPORTS.md`.

---

## Local → Cloud (Mac still online)

1. **Finish or checkpoint** the local session. Leave the tree in a known state (commit product work on its feature branch, or stash only if you accept that Cloud will not see the stash).
2. **Regenerate the normal local `HANDOFF.md`** with whatever the local agent already uses. This file stays private.
3. **Run the one-command handoff sync** (does not commit or push):

   ```bash
   make sync-handoffs
   ```

   This runs, in order:
   - `python scripts/import_cloud_agent_report.py` to import `origin/agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md` into the marked section of local `HANDOFF.md` (skipped safely if no report exists yet)
   - `~/.local/bin/sync-onepilot-handoff.sh` to sync repo `HANDOFF.md` → iCloud `HANDOFF.md` (do not assume this script exists in Cloud)
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

If the Mac is offline, GitHub remains authoritative for the latest Cloud report until this sync runs.

---

## iCloud HANDOFF.md vs docs/agent/CLOUD_HANDOFF.md vs LATEST_AGENT_REPORT.md

- iCloud `HANDOFF.md` is your private/local diary for the Mac Cursor agent (synced by `make sync-handoffs`). It may contain a generated Cloud-report section.
- `docs/agent/CLOUD_HANDOFF.md` is the sanitized Cloud-visible **project-state** context committed to git.
- `agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md` is the sanitized **execution/result** of the last Cloud run.

They are intentionally **not** the same document. `CLOUD_HANDOFF.md` is sanitized/redacted for Cloud safety and may omit private/local-only sections. The agent report is not a substitute for project-state context.

Local/iCloud `HANDOFF.md` remains authoritative for private/local state; Cloud uses the sanitized committed handoff plus, when present, the reporting ref.

---

## Phone / Cloud Agent

1. Open Cursor on the phone and start a Cloud Agent on `Fejjii/OnePilot-AI`.
2. Instruct: read `docs/agent/CLOUD_HANDOFF.md` and `AGENTS.md` before editing. Optionally fetch `origin/agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md` for the previous run result.
3. **Product feature/fix:** work on a feature/fix branch off `main`. Do not edit `deployment/public-demo` or `deployment/live-google-demo` unless the operator named that branch and authorized it.
4. **Read-only audit/review:** no product branch/PR is required. Do not modify product code. Publish only the sanitized agent report.
5. Do not touch Qdrant / Railway / Vercel / production env vars / OP-026 / live data. OP-026 is COMPLETE, but Cloud must still not re-run or modify live-data work.
6. Before finishing:
   - Product work: update `docs/agent/CLOUD_HANDOFF.md` (completed / current / recommended next + SHAs if you fetched remotes) **in the same product PR** when project state changed.
   - Every Cloud session: write a sanitized final report and publish it to `agent/cloud-state` when the publisher exists on the branch you are using (`python scripts/publish_cloud_agent_report.py --input report.md`). If `agent/cloud-state` does not exist yet, bootstrap once after the infrastructure PR is merged (`--bootstrap`).
   - Re-run the sanitizer if a local `HANDOFF.md` exists in that environment; otherwise edit the Cloud file directly and keep it secret-free.
7. For product work: commit, push the feature branch, open a PR into `main`. Do not merge unless asked. Do not open a PR merely to publish a runtime report.

---

## Cloud → Local (Mac back online)

1. Cloud Agent has published a sanitized report to `agent/cloud-state` (and, for product work, pushed its branch with an updated `CLOUD_HANDOFF.md`).
2. On the Mac: `git fetch` (include `origin/agent/cloud-state` when present) and check out the product branch if you are continuing implementation.
3. Run `make sync-handoffs` (or `python scripts/import_cloud_agent_report.py`) so the latest GitHub report is copied into the marked section of private `HANDOFF.md`, then to iCloud, then used as input to the Cloud sanitizer.
4. **`HANDOFF.md` remains authoritative for local/private state** — the importer never deletes unmarked sections. Do not treat `CLOUD_HANDOFF.md` as a full local diary.
5. Next time you hand back to the phone: update your private/local `HANDOFF.md` as needed, then run `make sync-handoffs` again. Review the sanitized Cloud handoff diff and commit/push it if project state changed.

---

## Security controls

- Sync and report scripts redact keys, JWTs, bearer tokens, connection strings, vendor tokens, PEM blocks, and sensitive assignments (shared scanner in `scripts/sync_cloud_handoff.py`).
- Fail-closed: residual secret-like patterns → non-zero exit, **output / ref not written**.
- Handoff sanitizer never auto-commits or auto-pushes.
- Publisher never force-pushes and never updates `main` or deployment refs. It uses a temporary worktree.
- Importer updates only `<!-- CLOUD_AGENT_REPORT_BEGIN/END -->` and never commits `HANDOFF.md`.
- Wrapper verifies that iCloud `HANDOFF.md` exists/looks valid and updates before running the sanitizer (fail-fast if missing/stale). Unsafe imports abort before iCloud sync.
- Cloud file must distinguish canonical vs public-demo vs live-demo vs user-gated vs local-only vs the reporting ref.
- Tests: `python -m pytest -q scripts/tests`
