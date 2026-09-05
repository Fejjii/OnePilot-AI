#!/usr/bin/env python3
"""Sanitized Cloud agent report schema, validation, and HANDOFF markers.

Cloud reports are public once committed. Every report is redacted with the
same fail-closed secret scanner used by sync_cloud_handoff.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping

from sync_cloud_handoff import (
    SecretScanError,
    assert_no_residual_secrets,
    find_residual_secrets,
    redact_text,
)

REPORT_REF = "agent/cloud-state"
REPORT_PATH = "docs/agent/LATEST_AGENT_REPORT.md"
REPORT_ARCHIVE_DIR = "docs/agent/reports"
REPORT_MAX_ARCHIVED = 20

FORBIDDEN_REFS = frozenset(
    {
        "main",
        "deployment/public-demo",
        "deployment/live-google-demo",
    }
)

HANDOFF_REPORT_BEGIN = "<!-- CLOUD_AGENT_REPORT_BEGIN -->"
HANDOFF_REPORT_END = "<!-- CLOUD_AGENT_REPORT_END -->"

TASK_TYPES = frozenset(
    {"implementation", "review", "audit", "release", "investigation"}
)
STATUSES = frozenset({"PASS", "PASS_WITH_ISSUES", "FAIL", "BLOCKED"})

REQUIRED_META = (
    "generated_utc",
    "task_name",
    "repository",
    "source_branch",
    "source_sha",
    "task_type",
    "status",
)
OPTIONAL_META = ("agent_mode", "agent_model")

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "work_performed": ("work performed",),
    "important_findings": ("important findings", "findings"),
    "p0_blockers": ("p0 blockers", "p0"),
    "p1_issues": ("p1 issues", "p1"),
    "p2_deferred": (
        "p2 / deferred",
        "p2/deferred",
        "p2 deferred",
        "p2/deferred items",
        "p2 deferred items",
        "p2",
    ),
    "tests_validation": (
        "tests / validation",
        "tests/validation",
        "tests",
        "validation",
    ),
    "files_changed": ("files changed",),
    "production_verification": ("production verification",),
    "blockers": ("blockers",),
    "recommended_next_step": (
        "recommended next step",
        "recommended next",
        "next step",
    ),
}

REQUIRED_SECTIONS = (
    "work_performed",
    "important_findings",
    "p0_blockers",
    "p1_issues",
    "p2_deferred",
    "tests_validation",
    "blockers",
    "recommended_next_step",
)
OPTIONAL_SECTIONS = ("files_changed", "production_verification")

CANONICAL_SECTION_HEADINGS: dict[str, str] = {
    "work_performed": "Work performed",
    "important_findings": "Important findings",
    "p0_blockers": "P0 blockers",
    "p1_issues": "P1 issues",
    "p2_deferred": "P2 / deferred",
    "tests_validation": "Tests / validation",
    "files_changed": "Files changed",
    "production_verification": "Production verification",
    "blockers": "Blockers",
    "recommended_next_step": "Recommended next step",
}

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")
_FORBIDDEN_HEADING = re.compile(
    r"(system\s+prompt|hidden\s+reasoning|chain\s+of\s+thought)",
    re.IGNORECASE,
)
NO_REPORT_INNER = (
    "No Cloud agent report is available on "
    f"`origin/{REPORT_REF}:{REPORT_PATH}` yet. "
    "GitHub remains authoritative once the reporting ref exists."
)


class ReportFormatError(ValueError):
    """Raised when a report is missing required metadata or sections."""


class UnsafeRefError(RuntimeError):
    """Raised when a git operation would touch a forbidden or unexpected ref."""


@dataclass
class AgentReport:
    generated_utc: str
    task_name: str
    repository: str
    source_branch: str
    source_sha: str
    task_type: str
    status: str
    agent_mode: str = "unknown"
    agent_model: str = "unknown"
    sections: dict[str, str] = field(default_factory=dict)

    def section(self, key: str) -> str:
        return self.sections.get(key, "").strip()


def normalize_heading(heading: str) -> str:
    return re.sub(r"\s+", " ", heading).strip().lower()


def _alias_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for key, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            mapping[normalize_heading(alias)] = key
    return mapping


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (metadata, remainder) from a simple `---` key: value block."""
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        raise ReportFormatError("report must start with YAML-like frontmatter (---)")
    lines = stripped.splitlines()
    if lines[0].strip() != "---":
        raise ReportFormatError("report must start with YAML-like frontmatter (---)")
    meta: dict[str, str] = {}
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise ReportFormatError("frontmatter lines must be `key: value`")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key:
            raise ReportFormatError("frontmatter key is empty")
        meta[key] = value
    if end_index is None:
        raise ReportFormatError("frontmatter is not closed with ---")
    remainder = "\n".join(lines[end_index + 1 :])
    return meta, remainder


def parse_sections(body: str) -> dict[str, str]:
    aliases = _alias_map()
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_level: int | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current_key, buf
        if current_key is None:
            return
        existing = sections.get(current_key, "")
        chunk = "\n".join(buf).strip()
        sections[current_key] = f"{existing}\n\n{chunk}".strip() if existing else chunk
        buf = []

    for raw_line in body.splitlines():
        match = _HEADING.match(raw_line)
        if match:
            level = len(match.group(1))
            heading = match.group(2).strip()
            if _FORBIDDEN_HEADING.search(heading):
                raise ReportFormatError(
                    "report contains a forbidden heading kind "
                    "(system prompt / hidden reasoning / chain of thought)"
                )
            if level <= 2:
                key = aliases.get(normalize_heading(heading))
                flush()
                current_key = key
                current_level = level
                if key is None and level == 1:
                    continue
                if key is None:
                    current_key = None
                continue
            if current_key is not None and current_level is not None and level > current_level:
                buf.append(raw_line)
                continue
        elif current_key is not None:
            buf.append(raw_line)
    flush()
    return sections


def parse_utc(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise ReportFormatError("generated_utc is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ReportFormatError("generated_utc must be ISO-8601 UTC") from exc
    if parsed.tzinfo is None:
        raise ReportFormatError("generated_utc must include a timezone (use Z)")
    return parsed.astimezone(timezone.utc)


def validate_metadata(meta: Mapping[str, str]) -> None:
    missing = [key for key in REQUIRED_META if not str(meta.get(key, "")).strip()]
    if missing:
        raise ReportFormatError(f"missing required metadata: {', '.join(missing)}")
    try:
        parse_utc(meta["generated_utc"])
    except ReportFormatError:
        raise
    task_type = meta["task_type"].strip().lower()
    if task_type not in TASK_TYPES:
        raise ReportFormatError(
            f"task_type must be one of: {', '.join(sorted(TASK_TYPES))}"
        )
    status = meta["status"].strip().upper()
    if status not in STATUSES:
        raise ReportFormatError(f"status must be one of: {', '.join(sorted(STATUSES))}")
    if not _SHA.fullmatch(meta["source_sha"].strip()):
        raise ReportFormatError("source_sha must be a git SHA (7-40 hex chars)")


def validate_sections(sections: Mapping[str, str]) -> None:
    missing = [key for key in REQUIRED_SECTIONS if not str(sections.get(key, "")).strip()]
    if missing:
        labels = [CANONICAL_SECTION_HEADINGS[key] for key in missing]
        raise ReportFormatError(f"missing required sections: {', '.join(labels)}")


def parse_report(text: str) -> AgentReport:
    meta, remainder = parse_frontmatter(text)
    validate_metadata(meta)
    sections = parse_sections(remainder)
    validate_sections(sections)
    return AgentReport(
        generated_utc=parse_utc(meta["generated_utc"]).strftime("%Y-%m-%dT%H:%M:%SZ"),
        task_name=meta["task_name"].strip(),
        repository=meta["repository"].strip(),
        source_branch=meta["source_branch"].strip(),
        source_sha=meta["source_sha"].strip().lower(),
        task_type=meta["task_type"].strip().lower(),
        status=meta["status"].strip().upper(),
        agent_mode=(meta.get("agent_mode") or "unknown").strip() or "unknown",
        agent_model=(meta.get("agent_model") or "unknown").strip() or "unknown",
        sections={key: sections.get(key, "").strip() for key in (*REQUIRED_SECTIONS, *OPTIONAL_SECTIONS)},
    )


def sanitize_report(report: AgentReport) -> AgentReport:
    """Redact secret-like content. Never returns residual secrets."""

    def clean(value: str) -> str:
        return redact_text(value).strip()

    cleaned = AgentReport(
        generated_utc=clean(report.generated_utc),
        task_name=clean(report.task_name),
        repository=clean(report.repository),
        source_branch=clean(report.source_branch),
        source_sha=clean(report.source_sha),
        task_type=clean(report.task_type),
        status=clean(report.status),
        agent_mode=clean(report.agent_mode),
        agent_model=clean(report.agent_model),
        sections={key: clean(body) for key, body in report.sections.items()},
    )
    validate_metadata(
        {
            "generated_utc": cleaned.generated_utc,
            "task_name": cleaned.task_name,
            "repository": cleaned.repository,
            "source_branch": cleaned.source_branch,
            "source_sha": cleaned.source_sha,
            "task_type": cleaned.task_type,
            "status": cleaned.status,
        }
    )
    validate_sections(cleaned.sections)
    rendered = render_report(cleaned)
    assert_no_residual_secrets(rendered)
    return cleaned


def parse_and_sanitize(text: str) -> AgentReport:
    return sanitize_report(parse_report(text))


def render_report(report: AgentReport) -> str:
    lines = [
        "---",
        f"generated_utc: {report.generated_utc}",
        f"task_name: {report.task_name}",
        f"agent_mode: {report.agent_mode}",
        f"agent_model: {report.agent_model}",
        f"repository: {report.repository}",
        f"source_branch: {report.source_branch}",
        f"source_sha: {report.source_sha}",
        f"task_type: {report.task_type}",
        f"status: {report.status}",
        "---",
        "",
        "# Cloud Agent Report",
        "",
        f"Ref: `{REPORT_REF}`  ",
        f"Path: `{REPORT_PATH}`",
        "",
        "This file is public/sanitized execution context. "
        "It is not a substitute for `docs/agent/CLOUD_HANDOFF.md` (project state).",
        "",
    ]
    for key in (*REQUIRED_SECTIONS, *OPTIONAL_SECTIONS):
        heading = CANONICAL_SECTION_HEADINGS[key]
        body = report.section(key) or "n/a"
        lines.extend([f"## {heading}", "", body, ""])
    return "\n".join(lines).rstrip() + "\n"


def render_no_report_placeholder() -> str:
    return (
        f"{HANDOFF_REPORT_BEGIN}\n"
        f"{NO_REPORT_INNER}\n"
        f"{HANDOFF_REPORT_END}"
    )


def upsert_handoff_report_section(handoff_text: str, inner: str) -> str:
    """Replace or append the marked Cloud-report section. Preserve all else."""
    block = f"{HANDOFF_REPORT_BEGIN}\n{inner.rstrip()}\n{HANDOFF_REPORT_END}"
    pattern = re.compile(
        re.escape(HANDOFF_REPORT_BEGIN) + r".*?" + re.escape(HANDOFF_REPORT_END),
        re.DOTALL,
    )
    if pattern.search(handoff_text):
        return pattern.sub(block, handoff_text, count=1)
    prefix = handoff_text
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    return prefix + block + "\n"


def extract_handoff_report_section(handoff_text: str) -> str | None:
    pattern = re.compile(
        re.escape(HANDOFF_REPORT_BEGIN) + r"(.*?)" + re.escape(HANDOFF_REPORT_END),
        re.DOTALL,
    )
    match = pattern.search(handoff_text)
    if not match:
        return None
    return match.group(1)


def assert_safe_ref(ref: str, *, allow_report_ref: bool = True) -> str:
    name = ref.strip()
    if name.startswith("refs/heads/"):
        name = name[len("refs/heads/") :]
    if name.startswith("origin/"):
        name = name[len("origin/") :]
    if name.startswith("+"):
        raise UnsafeRefError("refusing forced refspec")
    if name in FORBIDDEN_REFS:
        raise UnsafeRefError(f"refusing to modify protected ref: {name}")
    if not allow_report_ref and name == REPORT_REF:
        raise UnsafeRefError(f"refusing unexpected use of {REPORT_REF}")
    if allow_report_ref and name != REPORT_REF:
        raise UnsafeRefError(
            f"publisher may only update {REPORT_REF}, not {name or '<empty>'}"
        )
    return name


def archive_filename(report: AgentReport) -> str:
    stamp = parse_utc(report.generated_utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", report.task_name.lower()).strip("-")[:40] or "report"
    return f"{stamp}-{slug}.md"


def example_report_markdown(
    *,
    generated_utc: str = "2026-09-05T12:00:00Z",
    task_name: str = "example-cloud-report",
    task_type: str = "investigation",
    status: str = "PASS",
    source_branch: str = "infra/example",
    source_sha: str = "b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8",
) -> str:
    return f"""---
generated_utc: {generated_utc}
task_name: {task_name}
agent_mode: cloud
agent_model: unknown
repository: Fejjii/OnePilot-AI
source_branch: {source_branch}
source_sha: {source_sha}
task_type: {task_type}
status: {status}
---

# Cloud Agent Report

## Work performed
- Prepared a sanitized Cloud agent report.

## Important findings
- None.

## P0 blockers
- None.

## P1 issues
- None.

## P2 / deferred
- None.

## Tests / validation
- Not run.

## Files changed
- n/a

## Production verification
- n/a

## Blockers
- None.

## Recommended next step
- Review the reporting contract in docs/agent/AGENT_REPORTS.md.
"""


__all__ = [
    "AgentReport",
    "FORBIDDEN_REFS",
    "HANDOFF_REPORT_BEGIN",
    "HANDOFF_REPORT_END",
    "REPORT_ARCHIVE_DIR",
    "REPORT_MAX_ARCHIVED",
    "REPORT_PATH",
    "REPORT_REF",
    "ReportFormatError",
    "STATUSES",
    "SecretScanError",
    "TASK_TYPES",
    "UnsafeRefError",
    "archive_filename",
    "assert_no_residual_secrets",
    "assert_safe_ref",
    "example_report_markdown",
    "extract_handoff_report_section",
    "find_residual_secrets",
    "parse_and_sanitize",
    "parse_report",
    "redact_text",
    "render_no_report_placeholder",
    "render_report",
    "sanitize_report",
    "upsert_handoff_report_section",
]
