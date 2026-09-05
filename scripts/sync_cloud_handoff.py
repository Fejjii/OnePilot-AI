#!/usr/bin/env python3
"""Generate a sanitized Cloud-agent handoff file.

Reads optional local HANDOFF.md, merges safe git/repo state, aggressively
redacts secrets, and writes docs/agent/CLOUD_HANDOFF.md.

Does not commit or push. Fail-closed: if residual secret-like patterns remain
after redaction, exit non-zero and do not write the output file.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HANDOFF = REPO_ROOT / "HANDOFF.md"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "agent" / "CLOUD_HANDOFF.md"

CANONICAL_BRANCH = "main"
PUBLIC_DEMO_BRANCH = "deployment/public-demo"
LIVE_DEMO_BRANCH = "deployment/live-google-demo"
TRACKED_BRANCHES = (CANONICAL_BRANCH, PUBLIC_DEMO_BRANCH, LIVE_DEMO_BRANCH)

REDACTED = "[REDACTED]"
PLACEHOLDER_VALUES = {
    REDACTED,
    "[API_KEY_REDACTED]",
    "[JWT_REDACTED]",
    "[TOKEN_REDACTED]",
    "[AWS_KEY_REDACTED]",
    "[GITHUB_TOKEN_REDACTED]",
    "[SLACK_TOKEN_REDACTED]",
    "[PRIVATE_KEY_REDACTED]",
    "[CONNECTION_REDACTED]",
    "[URL_SECRET_REDACTED]",
    "<secret>",
    "<PASSWORD>",
    "<API_KEY>",
    "changeme",
    "change-me",
}

# High-confidence secret shapes. Order matters: more specific first.
_REDACTION_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[PRIVATE_KEY_REDACTED]",
    ),
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "[JWT_REDACTED]",
    ),
    (
        re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        "Bearer [TOKEN_REDACTED]",
    ),
    (re.compile(r"\bsk-proj-[A-Za-z0-9_-]{16,}\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\bsk-svcacct-[A-Za-z0-9_-]{16,}\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\bpk_(?:live|test)_[A-Za-z0-9]{16,}\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\brak_[A-Za-z0-9]{16,}\b"), "[API_KEY_REDACTED]"),  # Railway
    (re.compile(r"\bqdrant_[A-Za-z0-9]{16,}\b", re.IGNORECASE), "[API_KEY_REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS_KEY_REDACTED]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[GITHUB_TOKEN_REDACTED]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[GITHUB_TOKEN_REDACTED]"),
    (re.compile(r"\bxox[baprs]-\S+"), "[SLACK_TOKEN_REDACTED]"),
    (
        re.compile(
            r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|rediss|amqp|amqps)"
            r"://[^\s:]+:[^\s@/]+@[^\s)]+"
        ),
        "[CONNECTION_REDACTED]",
    ),
    (
        re.compile(
            r"(https?://[^\s)>\]]+[?&](?:token|key|api[_-]?key|access[_-]?token|"
            r"auth|secret|password|jwt)=)[^\s&#)]+",
            re.IGNORECASE,
        ),
        r"\1[URL_SECRET_REDACTED]",
    ),
    (
        re.compile(
            r"(?i)\b("
            r"JWT_SECRET|DATABASE_URL|REDIS_URL|QDRANT_API_KEY|QDRANT_URL|"
            r"OPENAI_API_KEY|SERPER_API_KEY|LANGSMITH_API_KEY|"
            r"RAILWAY_TOKEN|RAILWAY_API_TOKEN|VERCEL_TOKEN|"
            r"GOOGLE_CLIENT_SECRET|GOOGLE_REFRESH_TOKEN|GOOGLE_CLIENT_ID|"
            r"GITHUB_TOKEN|GH_TOKEN|AWS_SECRET_ACCESS_KEY|AWS_ACCESS_KEY_ID|"
            r"API_KEY|API-KEY|"
            r"PASSWORD|PASSWD|SECRET|ACCESS_TOKEN|REFRESH_TOKEN|PRIVATE_TOKEN"
            r")(\s*[:=]\s*)(\S+)"
        ),
        rf"\1\2{REDACTED}",
    ),
]

# Residual scan after redaction. Must not match documentation that only
# mentions prefixes (e.g. "never include sk- keys") without a real token.
_RESIDUAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("pem_private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
    (
        "bearer_token",
        re.compile(r"\bBearer\s+(?!\[TOKEN_REDACTED\])[A-Za-z0-9\-._~+/]{12,}", re.I),
    ),
    ("openai_key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{16,}\b")),
    ("stripe_key", re.compile(r"\bpk_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-\S+")),
    (
        "connection_string",
        re.compile(
            r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|rediss)://[^\s:]+:"
        ),
    ),
    (
        "url_with_secret",
        re.compile(
            r"(?i)[?&](?:token|key|api[_-]?key|access[_-]?token|secret|password|jwt)="
            r"(?!\[URL_SECRET_REDACTED\]|\[REDACTED\])[^\s&#]{8,}"
        ),
    ),
    (
        "sensitive_assignment",
        re.compile(
            r"(?i)\b(?:JWT_SECRET|DATABASE_URL|REDIS_URL|QDRANT_API_KEY|"
            r"OPENAI_API_KEY|SERPER_API_KEY|RAILWAY_TOKEN|VERCEL_TOKEN|"
            r"GOOGLE_CLIENT_SECRET|GOOGLE_REFRESH_TOKEN|AWS_SECRET_ACCESS_KEY|"
            r"PASSWORD|SECRET)\s*[:=]\s*(?!\[REDACTED\]|<secret>|<PASSWORD>)\S{8,}"
        ),
    ),
]

_DENY_SECTION = re.compile(
    r"(secret|credential|password|api[\s_-]?key|access[\s_-]?token|"
    r"refresh[\s_-]?token|env(?:ironment)?\s*var|\.env|"
    r"connection\s*string|jwt\s*secret|private\s*key)",
    re.IGNORECASE,
)
_ALLOW_SECTION = re.compile(
    r"(current|completed|backlog|task|architecture|test|branch|protect|"
    r"next|status|constraint|must\s*not|do\s*not|canonical|deploy|"
    r"handoff|recommended|visibility|local-only|user-gated)",
    re.IGNORECASE,
)

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class SecretScanError(RuntimeError):
    """Raised when residual secret-like patterns remain after redaction."""

    def __init__(self, findings: list[str]) -> None:
        self.findings = findings
        kinds = ", ".join(findings)
        super().__init__(f"fail-closed: residual secret-like patterns: {kinds}")


@dataclass(frozen=True)
class BranchRef:
    name: str
    sha: str | None
    note: str = ""


@dataclass
class GitSnapshot:
    branches: list[BranchRef] = field(default_factory=list)
    fetched: bool = False

    def sha_for(self, name: str) -> str:
        for branch in self.branches:
            if branch.name == name:
                return branch.sha or "unknown"
        return "unknown"


@dataclass
class ExtractedHandoff:
    sections: dict[str, str] = field(default_factory=dict)
    dropped_headings: list[str] = field(default_factory=list)
    source_present: bool = False


def redact_text(text: str) -> str:
    """Replace known secret shapes with redaction markers."""
    redacted = text
    for pattern, replacement in _REDACTION_RULES:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def find_residual_secrets(text: str) -> list[str]:
    """Return unique finding kinds (never the matched secret values)."""
    found: list[str] = []
    for kind, pattern in _RESIDUAL_PATTERNS:
        if pattern.search(text) and kind not in found:
            found.append(kind)
    return found


def assert_no_residual_secrets(text: str) -> None:
    findings = find_residual_secrets(text)
    if findings:
        raise SecretScanError(findings)


def parse_markdown_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) pairs. Preamble uses heading ''."""
    sections: list[tuple[str, str]] = []
    current_heading = ""
    body_lines: list[str] = []
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            sections.append((current_heading, "\n".join(body_lines).strip()))
            current_heading = match.group(2).strip()
            body_lines = []
        else:
            body_lines.append(line)
    sections.append((current_heading, "\n".join(body_lines).strip()))
    return sections


def extract_safe_handoff(text: str) -> ExtractedHandoff:
    """Keep useful project-state sections; drop credential-oriented ones."""
    extracted = ExtractedHandoff(source_present=True)
    for heading, body in parse_markdown_sections(text):
        if not heading:
            continue
        if _DENY_SECTION.search(heading):
            extracted.dropped_headings.append(heading)
            continue
        if not _ALLOW_SECTION.search(heading):
            extracted.dropped_headings.append(heading)
            continue
        cleaned = redact_text(body)
        assert_no_residual_secrets(cleaned)
        extracted.sections[heading] = cleaned
    return extracted


def _run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def collect_git_snapshot(repo_root: Path, *, fetch: bool) -> GitSnapshot:
    """Read-only SHA lookup. Never checks out or modifies branches."""
    snapshot = GitSnapshot(fetched=False)
    if fetch:
        fetch_result = subprocess.run(
            ["git", "fetch", "origin", *TRACKED_BRANCHES],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        snapshot.fetched = fetch_result.returncode == 0

    for name in TRACKED_BRANCHES:
        sha = _run_git(["rev-parse", "--verify", f"origin/{name}"], repo_root)
        if not sha:
            sha = _run_git(["rev-parse", "--verify", name], repo_root)
        note = ""
        if not sha:
            note = "ref not available in this clone"
        snapshot.branches.append(BranchRef(name=name, sha=sha or None, note=note))
    return snapshot


def _existing_section_block(existing: str, heading: str) -> str | None:
    for name, body in parse_markdown_sections(existing):
        if name.lower() == heading.lower() and body.strip():
            cleaned = redact_text(body)
            assert_no_residual_secrets(cleaned)
            return cleaned
    return None


def _joined_extracted(extracted: ExtractedHandoff, *needles: str) -> str | None:
    parts: list[str] = []
    for heading, body in extracted.sections.items():
        lowered = heading.lower()
        if any(needle in lowered for needle in needles) and body.strip():
            parts.append(f"### {heading}\n\n{body}")
    return "\n\n".join(parts) if parts else None


DEFAULT_COMPLETED = """\
- OP-028 — CRM-grounded email drafting + recruiter-facing approval copy (merged to `main`, PR #25)
- OP-027 / OP-029 — workspace insights focus + evaluation report polish (merged to `main`, PR #24)
- Cloud/mobile handoff infrastructure (merged to `main`, PR #23)
- OP-025 — deterministic UUID5 Qdrant point IDs for idempotent upsert (merged to `main`, PR #22)
- OP-024 — `organization_id` payload index for strict-mode filtered Qdrant search (PR #21)
- OP-023 — empty `gpt-5-nano` completion handling for RAG and email drafts (PR #20)
- OP-022 — public-demo managed-provider enablement checklist (docs only; host env is user-gated)
- OP-015–OP-021 — shared-demo isolation, spend/abuse caps, workspace-insight routing
- OP-016 / OP-019 — OpenAI client timeouts/retries and secret redaction
- Public demo live on Vercel + Railway with **mock** Gmail/Calendar
- Canonical branch consolidation: `main` + thin `deployment/public-demo`
"""

DEFAULT_CURRENT = """\
- **This file** is the sanitized Cloud/mobile handoff context. Local `HANDOFF.md` (gitignored) remains authoritative for private/local state.
- Public infrastructure is essentially complete (OP-026 COMPLETE). Cloud must not re-run live Qdrant work.
- Recruiter-facing polish on `main` includes OP-027/OP-029 and OP-028. Product work belongs on a feature/fix branch off `main`, never on a deployment branch.
"""

DEFAULT_BACKLOG = """\
From `docs/limitations_roadmap.md` (near-term, product — pick explicitly):
- HTTP-only cookie auth with refresh tokens
- Real OpenAI streaming (SSE)
- Object storage for uploaded files
- Background task queue
- Optional demo-reset endpoint

Do **not** treat host-console work (Railway / Vercel / Qdrant Cloud env) as Cloud-agent work.
"""

DEFAULT_NEXT = """\
Recommended next Cloud-safe task: a scoped recruiter-demo consistency pass, or a named near-term item from `docs/limitations_roadmap.md`, after the operator names the task.

OP-026 is complete; do not re-run live Qdrant or modify deployment branches unless the operator explicitly authorizes that exact branch.
"""

DEFAULT_ARCHITECTURE = """\
- Multi-tenant FastAPI + Next.js workspace: LangGraph agent, RAG + citations, HITL approvals, usage/quotas, memory.
- Public demo: Vercel frontend + Railway API/Postgres/Redis; Gmail/Calendar **mock**; shared-demo agent memory disabled.
- Private live-Google track exists on `deployment/live-google-demo` and is **user-gated**. Cloud must not assume OAuth or live Google access.
- Vectors: Qdrant when configured, in-memory fallback otherwise. Cloud must not target live Qdrant clusters.
"""

DEFAULT_TESTS = """\
- Documented counts in README (2026-07-20): **703** backend tests (3 skipped), **126** frontend tests. Later merges added Qdrant/OpenAI coverage — trust current CI on `main`.
- CI (`.github/workflows/ci.yml`) runs backend pytest + frontend typecheck/tests/build on PRs to `main` and `deployment/**`.
- Public-demo smoke: `python scripts/smoke_test_public_demo.py --base-url <public-api>` (never print tokens).
- Cloud-handoff sync tests: `python -m pytest -q scripts/tests`
"""


def render_cloud_handoff(
    snapshot: GitSnapshot,
    extracted: ExtractedHandoff,
    *,
    existing_text: str | None,
    generated_at: str,
) -> str:
    main_sha = snapshot.sha_for(CANONICAL_BRANCH)
    public_sha = snapshot.sha_for(PUBLIC_DEMO_BRANCH)
    live_sha = snapshot.sha_for(LIVE_DEMO_BRANCH)
    public_aligned = (
        main_sha != "unknown" and public_sha != "unknown" and main_sha == public_sha
    )
    public_note = (
        "matches `main` (thin deploy pointer)"
        if public_aligned
        else "differs from `main` — treat as a separate deploy pointer; do not fast-forward unless authorized"
    )

    completed = (
        _joined_extracted(extracted, "completed")
        or (existing_text and _existing_section_block(existing_text, "Completed"))
        or DEFAULT_COMPLETED.strip()
    )
    current = (
        _joined_extracted(extracted, "current task", "current")
        or (existing_text and _existing_section_block(existing_text, "Current task / in progress"))
        or DEFAULT_CURRENT.strip()
    )
    backlog = (
        _joined_extracted(extracted, "backlog")
        or (existing_text and _existing_section_block(existing_text, "Backlog"))
        or DEFAULT_BACKLOG.strip()
    )
    next_task = (
        _joined_extracted(extracted, "recommended", "next")
        or (existing_text and _existing_section_block(existing_text, "Recommended next task"))
        or DEFAULT_NEXT.strip()
    )
    architecture = (
        _joined_extracted(extracted, "architecture")
        or (existing_text and _existing_section_block(existing_text, "Architecture state"))
        or DEFAULT_ARCHITECTURE.strip()
    )
    tests = (
        _joined_extracted(extracted, "test")
        or (existing_text and _existing_section_block(existing_text, "Tests / status"))
        or DEFAULT_TESTS.strip()
    )

    source_line = (
        "Local `HANDOFF.md` was present and sanitized into the task sections below."
        if extracted.source_present
        else "No local `HANDOFF.md` was available. Task sections use repo defaults and/or the previous Cloud file."
    )
    dropped = ""
    if extracted.dropped_headings:
        dropped = (
            "Dropped local headings (denied or not allow-listed): "
            + ", ".join(f"`{h}`" for h in extracted.dropped_headings)
            + ".\n"
        )

    body = f"""# Cloud agent handoff (sanitized)

Generated: {generated_at} UTC  
Generator: `scripts/sync_cloud_handoff.py` (does **not** commit or push)

This file is the **only** committed project-state brief for Cursor Cloud / phone agents.
It is intentionally smaller than any local `HANDOFF.md` and contains **no secrets**.

{source_line}
{dropped}

## How to read this file

| Layer | What it is | Cloud can use it? |
|-------|------------|-------------------|
| **Canonical repository** | `main` at the SHA below | Yes — default base for product work |
| **Deployed public-demo** | `deployment/public-demo` (Vercel + Railway, mock Gmail/Calendar) | Read SHAs only. Do not push/fast-forward unless explicitly authorized |
| **Private live-demo** | `deployment/live-google-demo` (live Google OAuth track) | **No** unless the operator names that branch and authorizes the change |
| **User-gated operations** | Railway / Vercel / Qdrant Cloud / production env vars | **No** — operator does this in host consoles |
| **Local-only state** | `HANDOFF.md`, `.ai/`, `CHANGELOG_SESSION.md`, git stash, iCloud, local `.env` | **Invisible** to Cloud. Never assume it exists |
| **Latest Cloud agent report** | `agent/cloud-state` → `docs/agent/LATEST_AGENT_REPORT.md` | Yes — last execution/result only. Not project state and not a product/deploy branch |

## Canonical and deployment SHAs

| Ref | SHA | Notes |
|-----|-----|-------|
| `origin/main` (canonical) | `{main_sha}` | Product source of truth |
| `origin/deployment/public-demo` | `{public_sha}` | {public_note} |
| `origin/deployment/live-google-demo` | `{live_sha}` | Private live-Google pointer; **do not modify** |

## Completed

{completed}

## Current task / in progress

{current}

## Backlog

{backlog}

## Architecture state

{architecture}

## Tests / status

{tests}

## Protected branches and do-not-touch

Cloud (and any agent) must **not** touch:

- `deployment/public-demo` and `deployment/live-google-demo` (no checkout-for-edit, no force-push, no fast-forward) unless the operator explicitly authorizes that exact branch
- Live **Qdrant**, **Railway**, **Vercel**, production env vars, or application deployment
- OP-026 and any in-flight live-data work
- git `stash` (including `stash@{{0}}`)
- gitignored local files: `.ai/`, `HANDOFF.md`, `CHANGELOG_SESSION.md`, `.env`, `.env.local`

`main` is canonical. All product changes go on a feature/fix branch, then a PR into `main`. Do not merge unless asked.

## Recommended next task

{next_task}

## Local-only reminder

Cloud cannot see the operator's Mac stash, iCloud copies, local `.ai/` notes, or private `HANDOFF.md`. If something is missing here, it is local-only or user-gated — ask; do not invent access.
"""
    return body.strip() + "\n"


def generate_cloud_handoff(
    *,
    repo_root: Path,
    handoff_path: Path,
    output_path: Path,
    fetch: bool,
    generated_at: str | None = None,
) -> str:
    snapshot = collect_git_snapshot(repo_root, fetch=fetch)
    extracted = ExtractedHandoff()
    if handoff_path.is_file():
        raw = handoff_path.read_text(encoding="utf-8")
        # Fail closed on the raw input if a PEM key is present and we cannot
        # prove the extracted allow-listed body is clean (extract already scans).
        extracted = extract_safe_handoff(raw)

    existing = output_path.read_text(encoding="utf-8") if output_path.is_file() else None
    timestamp = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    rendered = render_cloud_handoff(
        snapshot,
        extracted,
        existing_text=existing,
        generated_at=timestamp,
    )
    rendered = redact_text(rendered)
    assert_no_residual_secrets(rendered)
    return rendered


def write_if_safe(output_path: Path, content: str) -> None:
    assert_no_residual_secrets(content)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a sanitized docs/agent/CLOUD_HANDOFF.md. "
            "Never commits or pushes."
        )
    )
    parser.add_argument(
        "--handoff",
        type=Path,
        default=DEFAULT_HANDOFF,
        help="Local HANDOFF.md path (optional; default: ./HANDOFF.md)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output path (default: docs/agent/CLOUD_HANDOFF.md)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Git repository root",
    )
    parser.add_argument(
        "--fetch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="git fetch origin main + deployment branches (read-only; default: yes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated markdown to stdout; do not write the output file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Scan an existing output file for residual secrets and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            target = args.output
            if not target.is_file():
                print(f"error: nothing to check at {target}", file=sys.stderr)
                return 1
            assert_no_residual_secrets(target.read_text(encoding="utf-8"))
            print(f"ok: no residual secret patterns in {target}")
            return 0

        content = generate_cloud_handoff(
            repo_root=args.repo_root,
            handoff_path=args.handoff,
            output_path=args.output,
            fetch=args.fetch,
        )
        if args.dry_run:
            sys.stdout.write(content)
            return 0
        write_if_safe(args.output, content)
        print(f"wrote {args.output}")
        print("Review the sanitized diff, then commit and push explicitly.")
        print("This script does not commit or push.")
        return 0
    except SecretScanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("Refusing to write output (fail-closed). No file was updated.", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
