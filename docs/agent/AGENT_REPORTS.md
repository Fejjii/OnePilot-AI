# Cloud agent reports

Durable, sanitized execution/result reports for Cursor Cloud agents.

GitHub is the bridge. Cloud **cannot** write iCloud, local `HANDOFF.md`, `.ai/`,
stash, or the Mac filesystem. A later Mac sync imports the GitHub report into
the private handoff and, when the Mac is online, copies that file to iCloud.

| Layer | Role | Authoritative when |
|-------|------|--------------------|
| `docs/agent/CLOUD_HANDOFF.md` | Sanitized **project-state** context | Always for Cloud/phone product context |
| `agent/cloud-state` → `docs/agent/LATEST_AGENT_REPORT.md` | Sanitized **execution/result** context | Always for the latest Cloud run result |
| Local / iCloud `HANDOFF.md` | Private diary + generated report section | Mac / local agent only |

Do not conflate these files. Do not use a product PR merely to publish a runtime
report. Do not treat `agent/cloud-state` as a product or deployment branch.

## Contract (ChatGPT / GitHub tools)

Another system with GitHub read access can retrieve the latest report without
the original Cursor chat:

- **ref:** `agent/cloud-state`
- **path:** `docs/agent/LATEST_AGENT_REPORT.md`

Example:

```bash
git fetch origin agent/cloud-state
git show origin/agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md
```

If the Mac is offline, **GitHub remains authoritative** for the latest Cloud
report until `make sync-handoffs` runs on the Mac.

## Why Cloud cannot write iCloud

Cloud Agents run on a remote VM. They cannot see the operator Mac, iCloud Drive,
local `HANDOFF.md`, `.ai/`, git stash, or local `.env`. Writing those paths from
Cloud would be invented access. The public repository is the only durable
channel Cloud is allowed to use, and every committed report must be treated as
public.

## Lifecycle

### A. Mac → Cloud

1. Update private local `HANDOFF.md` as usual.
2. Run `make sync-handoffs` (does not commit or push).
3. Review and commit only sanitized `docs/agent/CLOUD_HANDOFF.md` on the
   intended branch.
4. Launch a Cloud Agent. It reads `CLOUD_HANDOFF.md` first. The Mac may go
   offline.

### B. Cloud feature / fix → GitHub report

1. Product work stays on a feature/fix branch + PR into `main` (unchanged).
2. Update `CLOUD_HANDOFF.md` **in that same product PR** when project state
   changed.
3. After the run, publish a sanitized agent report to `agent/cloud-state`
   (not via a docs-only PR, and not by committing the report on `main`).

```bash
python scripts/publish_cloud_agent_report.py --input report.md
```

### C. Cloud read-only audit / review → GitHub report

1. No product branch or PR is required.
2. Do not modify product code.
3. Publish only the sanitized report through `agent/cloud-state`.

### D. ChatGPT reads the latest report

Read `origin/agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md` using GitHub
tools. That file is the handoff for another agent or ChatGPT when the original
Cursor chat is gone.

### E. Mac comes online → private HANDOFF → iCloud

`make sync-handoffs` now does:

1. Import GitHub `LATEST_AGENT_REPORT.md` into the marked section of local
   `HANDOFF.md`
2. Copy local `HANDOFF.md` → iCloud `HANDOFF.md` (existing Mac script)
3. Regenerate sanitized `docs/agent/CLOUD_HANDOFF.md`

The generated section is delimited by:

```markdown
<!-- CLOUD_AGENT_REPORT_BEGIN -->
...
<!-- CLOUD_AGENT_REPORT_END -->
```

All other private HANDOFF contents are preserved.

### F. Next Cloud session

The next Cloud agent reads sanitized `CLOUD_HANDOFF.md` (project state). It may
also fetch `agent/cloud-state` for the previous execution result. Those remain
separate documents.

## Publisher (Cloud)

```bash
# Validate only
python scripts/publish_cloud_agent_report.py --input report.md --check

# Stdin
python scripts/publish_cloud_agent_report.py --input - < report.md

# First-time ref (only after this infrastructure is merged)
python scripts/publish_cloud_agent_report.py --bootstrap --input report.md

# Prepare without pushing (tests / dry-run)
python scripts/publish_cloud_agent_report.py --bootstrap --dry-run --input report.md
```

Safety:

- Temporary git worktree; product branch and dirty files are left untouched
- Never force-pushes
- Never updates `main`, `deployment/public-demo`, or `deployment/live-google-demo`
- Reuses `scripts/sync_cloud_handoff.py` redaction
- Fail-closed if residual secret-like patterns remain (no publish, no secret print)

Bounded history (optional, on the reporting ref only):

- `docs/agent/reports/` keeps the latest 20 sanitized reports

## Importer (Mac)

```bash
python scripts/import_cloud_agent_report.py
# or
make import-agent-report
```

- Fetches `origin/agent/cloud-state`
- Validates and re-sanitizes the report
- Updates only the marked generated section
- Idempotent
- Missing report is non-fatal (placeholder; GitHub remains authoritative)
- Malformed or unsafe reports do not rewrite private HANDOFF contents

Do not assume `~/.local/bin/sync-onepilot-handoff.sh` exists in Cloud.

## Report format

Use `docs/agent/AGENT_REPORT_TEMPLATE.md`. Required metadata:

- `generated_utc` (ISO-8601 UTC, `Z`)
- `task_name`
- `repository`
- `source_branch`
- `source_sha`
- `task_type`: `implementation` / `review` / `audit` / `release` / `investigation`
- `status`: `PASS` / `PASS_WITH_ISSUES` / `FAIL` / `BLOCKED`

Optional metadata: `agent_mode`, `agent_model`.

Required sections: work performed, important findings, P0 / P1 / P2, tests,
blockers, recommended next step. Include files changed and production
verification when applicable.

Never include chain of thought, hidden reasoning, system prompts, secrets,
JWTs, connection strings, API keys, raw provider payloads, or private user data.

## Bootstrap after merge

`agent/cloud-state` is **not** created by the infrastructure PR. After merge:

1. Confirm `main` contains the publisher.
2. From Cloud or Mac, publish the first sanitized report with `--bootstrap`.
3. Do not force-push. Do not bootstrap onto `main` or a deployment branch.
