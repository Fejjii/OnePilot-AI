#!/usr/bin/env python3
"""Import the latest sanitized Cloud agent report into local HANDOFF.md.

Reads origin/agent/cloud-state:docs/agent/LATEST_AGENT_REPORT.md and updates
only the marked generated section. All other private HANDOFF contents are
preserved. Never commits HANDOFF.md. Never copies residual secrets.

GitHub remains authoritative if this Mac is offline or the import is skipped.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from agent_report import (
    HANDOFF_REPORT_BEGIN,
    HANDOFF_REPORT_END,
    NO_REPORT_INNER,
    REPORT_PATH,
    REPORT_REF,
    ReportFormatError,
    SecretScanError,
    parse_and_sanitize,
    render_report,
    upsert_handoff_report_section,
)
from sync_cloud_handoff import assert_no_residual_secrets, redact_text

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HANDOFF = REPO_ROOT / "HANDOFF.md"

NO_REPORT_EXIT = 0
UNSAFE_EXIT = 2


class ReportImportError(RuntimeError):
    """Importer failure that is safe to print (no secret material)."""


def _run_git(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise ReportImportError(f"git {args[0]} failed (exit {result.returncode})")
    return result


def fetch_report_ref(repo_root: Path, remote: str) -> bool:
    result = _run_git(
        ["fetch", remote, f"{REPORT_REF}:refs/remotes/{remote}/{REPORT_REF}"],
        cwd=repo_root,
        check=False,
    )
    return result.returncode == 0


def show_latest_report(repo_root: Path, remote: str) -> str | None:
    spec = f"{remote}/{REPORT_REF}:{REPORT_PATH}"
    result = _run_git(["show", spec], cwd=repo_root, check=False)
    if result.returncode != 0:
        local = _run_git(["show", f"{REPORT_REF}:{REPORT_PATH}"], cwd=repo_root, check=False)
        if local.returncode != 0:
            return None
        return local.stdout
    return result.stdout


def render_imported_section(report_text: str) -> str:
    report = parse_and_sanitize(report_text)
    body = render_report(report)
    preamble = (
        "Imported from "
        f"`origin/{REPORT_REF}:{REPORT_PATH}`. "
        "GitHub remains authoritative if this Mac copy is stale. "
        "This generated section is execution/result context only; "
        "it does not replace the rest of this private HANDOFF.\n\n"
    )
    inner = redact_text(preamble + body)
    assert_no_residual_secrets(inner)
    return inner


def import_report(
    *,
    repo_root: Path,
    handoff_path: Path,
    remote: str = "origin",
    fetch: bool = True,
    dry_run: bool = False,
    require_report: bool = False,
) -> str:
    if fetch:
        fetch_report_ref(repo_root, remote)
    raw = show_latest_report(repo_root, remote)

    if raw is None:
        if require_report:
            raise ReportImportError(
                f"no report at {remote}/{REPORT_REF}:{REPORT_PATH}"
            )
        inner = NO_REPORT_INNER
        status = "no-report"
    else:
        inner = render_imported_section(raw)
        status = "imported"

    if not handoff_path.is_file():
        existing = ""
    else:
        existing = handoff_path.read_text(encoding="utf-8")

    updated = upsert_handoff_report_section(existing, inner)
    if HANDOFF_REPORT_BEGIN not in updated or HANDOFF_REPORT_END not in updated:
        raise ReportImportError("failed to apply HANDOFF report markers")
    # Do not scan the entire private HANDOFF (it may contain local-only
    # material that must stay local). Scan only the generated section.
    begin = updated.index(HANDOFF_REPORT_BEGIN)
    end = updated.index(HANDOFF_REPORT_END) + len(HANDOFF_REPORT_END)
    generated = updated[begin:end]
    assert_no_residual_secrets(generated)

    if dry_run:
        return status
    handoff_path.write_text(updated, encoding="utf-8")
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import origin/agent/cloud-state latest report into the marked "
            "section of local HANDOFF.md. Never commits or pushes."
        )
    )
    parser.add_argument(
        "--handoff",
        type=Path,
        default=DEFAULT_HANDOFF,
        help="Local HANDOFF.md path (default: ./HANDOFF.md)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Git repository root used to read origin/agent/cloud-state",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Git remote (default: origin)",
    )
    parser.add_argument(
        "--fetch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="git fetch the reporting ref (default: yes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the import; do not write HANDOFF.md",
    )
    parser.add_argument(
        "--require-report",
        action="store_true",
        help="Exit non-zero when no report is available yet",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        status = import_report(
            repo_root=args.repo_root,
            handoff_path=args.handoff,
            remote=args.remote,
            fetch=args.fetch,
            dry_run=args.dry_run,
            require_report=args.require_report,
        )
        action = "would update" if args.dry_run else "updated"
        if status == "no-report":
            print(
                f"{action} {args.handoff} (no report available yet; "
                "GitHub remains authoritative)"
            )
        else:
            print(f"{action} generated Cloud report section in {args.handoff}")
        return NO_REPORT_EXIT
    except (ReportFormatError, ReportImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except SecretScanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(
            "Refusing to write HANDOFF.md (fail-closed). "
            "Private contents were not deleted.",
            file=sys.stderr,
        )
        return UNSAFE_EXIT
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
