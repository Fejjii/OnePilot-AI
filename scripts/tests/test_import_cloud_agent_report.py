"""Local HANDOFF import: markers, preservation, idempotency, missing/malformed."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import agent_report as schema  # noqa: E402
import import_cloud_agent_report as importer  # noqa: E402
import publish_cloud_agent_report as publish  # noqa: E402
from git_harness import connect_origin, init_bare_remote, init_product_repo, run_git  # noqa: E402

JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
    "c2lnbmF0dXJlX2Jsb2NrX2hlcmVfMTIz"
)

PRIVATE = """# Private HANDOFF

## Local only
stash note: do not delete
iCloud reminder: keep this paragraph exactly.

## Current task
- continue locally
"""


def _seed_report(tmp_path: Path, markdown: str) -> tuple[Path, Path]:
    repo = init_product_repo(tmp_path / "repo")
    remote = init_bare_remote(tmp_path / "remote.git")
    connect_origin(repo, remote)
    report_path = tmp_path / "report.md"
    report_path.write_text(markdown, encoding="utf-8")
    code = publish.main(
        [
            "--repo-root",
            str(repo),
            "--input",
            str(report_path),
            "--remote",
            "origin",
            "--bootstrap",
            "--no-fetch",
        ]
    )
    assert code == 0
    run_git(["fetch", "origin", "agent/cloud-state"], cwd=repo)
    return repo, remote


def test_import_inserts_markers_and_preserves_private_text(tmp_path: Path) -> None:
    repo, _remote = _seed_report(tmp_path, schema.example_report_markdown())
    handoff = tmp_path / "HANDOFF.md"
    handoff.write_text(PRIVATE, encoding="utf-8")

    code = importer.main(
        [
            "--repo-root",
            str(repo),
            "--handoff",
            str(handoff),
            "--no-fetch",
        ]
    )
    assert code == 0
    text = handoff.read_text(encoding="utf-8")
    assert text.startswith("# Private HANDOFF")
    assert "stash note: do not delete" in text
    assert "keep this paragraph exactly." in text
    assert schema.HANDOFF_REPORT_BEGIN in text
    assert schema.HANDOFF_REPORT_END in text
    assert "example-cloud-report" in text
    assert "Cloud Agent Report" in text


def test_import_is_idempotent(tmp_path: Path) -> None:
    repo, _remote = _seed_report(tmp_path, schema.example_report_markdown())
    handoff = tmp_path / "HANDOFF.md"
    handoff.write_text(PRIVATE, encoding="utf-8")
    args = [
        "--repo-root",
        str(repo),
        "--handoff",
        str(handoff),
        "--no-fetch",
    ]
    assert importer.main(args) == 0
    first = handoff.read_text(encoding="utf-8")
    assert importer.main(args) == 0
    second = handoff.read_text(encoding="utf-8")
    assert second == first


def test_no_report_available_writes_placeholder(tmp_path: Path) -> None:
    repo = init_product_repo(tmp_path / "repo")
    handoff = tmp_path / "HANDOFF.md"
    handoff.write_text(PRIVATE, encoding="utf-8")
    code = importer.main(
        [
            "--repo-root",
            str(repo),
            "--handoff",
            str(handoff),
            "--no-fetch",
        ]
    )
    assert code == 0
    text = handoff.read_text(encoding="utf-8")
    assert "stash note: do not delete" in text
    assert "No Cloud agent report is available" in text
    assert schema.HANDOFF_REPORT_BEGIN in text


def test_malformed_report_does_not_change_handoff(tmp_path: Path) -> None:
    repo, _remote = _seed_report(tmp_path, schema.example_report_markdown())
    work = tmp_path / "wt"
    run_git(["worktree", "add", str(work), "agent/cloud-state"], cwd=repo)
    latest = work / schema.REPORT_PATH
    latest.write_text("# not a valid report\n", encoding="utf-8")
    run_git(["add", schema.REPORT_PATH], cwd=work)
    run_git(["commit", "-m", "break report"], cwd=work)
    run_git(["worktree", "remove", str(work)], cwd=repo)
    run_git(["remote", "remove", "origin"], cwd=repo, check=False)

    handoff = tmp_path / "HANDOFF.md"
    handoff.write_text(PRIVATE, encoding="utf-8")
    code = importer.main(
        [
            "--repo-root",
            str(repo),
            "--handoff",
            str(handoff),
            "--no-fetch",
        ]
    )
    assert code == 1
    assert handoff.read_text(encoding="utf-8") == PRIVATE


def test_unsafe_report_is_fail_closed(tmp_path: Path) -> None:
    dirty = schema.example_report_markdown().replace("None.", f"token={JWT}", 1)
    # Residual JWT after a broken redaction is covered in schema tests.
    # Here: a report that is valid after redaction should import; a report
    # that remains dirty because we skip sanitizer is not possible through
    # the importer. Seed a published clean report, then replace the blob
    # with an unsanitized JWT document on the local reporting branch.
    repo, _remote = _seed_report(tmp_path, schema.example_report_markdown())
    work = tmp_path / "wt"
    run_git(["worktree", "add", str(work), "agent/cloud-state"], cwd=repo)
    (work / schema.REPORT_PATH).write_text(dirty, encoding="utf-8")
    run_git(["add", schema.REPORT_PATH], cwd=work)
    run_git(["commit", "-m", "inject jwt fixture"], cwd=work)
    run_git(["worktree", "remove", str(work)], cwd=repo)
    run_git(["remote", "remove", "origin"], cwd=repo, check=False)

    handoff = tmp_path / "HANDOFF.md"
    handoff.write_text(PRIVATE, encoding="utf-8")
    code = importer.main(
        [
            "--repo-root",
            str(repo),
            "--handoff",
            str(handoff),
            "--no-fetch",
        ]
    )
    # Importer sanitizes first; a JWT fixture is redacted, then residual scan
    # should pass. Assert it either imported with redaction or refused without
    # writing secrets.
    text = handoff.read_text(encoding="utf-8")
    assert JWT not in text
    assert "stash note: do not delete" in text
    if code == 0:
        assert "[JWT_REDACTED]" in text or "[TOKEN_REDACTED]" in text
    else:
        assert text == PRIVATE


def test_require_report_fails_when_missing(tmp_path: Path) -> None:
    repo = init_product_repo(tmp_path / "repo")
    handoff = tmp_path / "HANDOFF.md"
    handoff.write_text(PRIVATE, encoding="utf-8")
    code = importer.main(
        [
            "--repo-root",
            str(repo),
            "--handoff",
            str(handoff),
            "--no-fetch",
            "--require-report",
        ]
    )
    assert code == 1
    assert handoff.read_text(encoding="utf-8") == PRIVATE


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    repo, _remote = _seed_report(tmp_path, schema.example_report_markdown())
    handoff = tmp_path / "HANDOFF.md"
    handoff.write_text(PRIVATE, encoding="utf-8")
    code = importer.main(
        [
            "--repo-root",
            str(repo),
            "--handoff",
            str(handoff),
            "--no-fetch",
            "--dry-run",
        ]
    )
    assert code == 0
    assert handoff.read_text(encoding="utf-8") == PRIVATE
