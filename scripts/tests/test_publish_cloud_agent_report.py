"""Publisher safety: worktrees, forbidden refs, bootstrap dry-run, no remotes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import agent_report as schema  # noqa: E402
import publish_cloud_agent_report as publish  # noqa: E402
from git_harness import (  # noqa: E402
    PROTECTED_BRANCHES,
    connect_origin,
    init_bare_remote,
    init_product_repo,
    ref_exists,
    run_git,
    sha,
)

JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
    "c2lnbmF0dXJlX2Jsb2NrX2hlcmVfMTIz"
)


def _report(**overrides: str) -> str:
    return schema.example_report_markdown(
        task_name=overrides.get("task_name", "infra/cloud-agent-report-bridge"),
        task_type=overrides.get("task_type", "implementation"),
        status=overrides.get("status", "PASS"),
        source_branch=overrides.get("source_branch", "infra/cloud-agent-report-bridge"),
        source_sha=overrides.get(
            "source_sha", "b87e8ca4aa99c08c3d5d4205b9139eceb7cb2ea8"
        ),
        generated_utc=overrides.get("generated_utc", "2026-09-05T12:00:00Z"),
    )


def test_check_validates_without_git(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    report_path.write_text(_report(), encoding="utf-8")
    code = publish.main(["--input", str(report_path), "--check"])
    assert code == 0


def test_check_fail_closed_does_not_print_secret(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dirty = schema.example_report_markdown()
    dirty = dirty.replace("None.", f"leaked {JWT}", 1)
    report_path = tmp_path / "dirty.md"
    report_path.write_text(dirty, encoding="utf-8")

    def no_redact(text: str) -> str:
        return text

    monkeypatch.setattr(schema, "redact_text", no_redact)
    monkeypatch.setattr(publish, "parse_and_sanitize", schema.parse_and_sanitize)
    code = publish.main(["--input", str(report_path), "--check"])
    captured = capsys.readouterr()
    assert code == 2
    assert JWT not in captured.out
    assert JWT not in captured.err


def test_bootstrap_dry_run_does_not_push_and_preserves_product(tmp_path: Path) -> None:
    repo = init_product_repo(tmp_path / "repo")
    remote = init_bare_remote(tmp_path / "remote.git")
    connect_origin(repo, remote)
    run_git(["checkout", "-b", "infra/cloud-agent-report-bridge"], cwd=repo)
    dirty = repo / "notes.txt"
    dirty.write_text("local product note\n", encoding="utf-8")
    before_head = sha(repo, "HEAD")
    before_protected = {name: sha(remote, name) for name in PROTECTED_BRANCHES}

    report_path = tmp_path / "report.md"
    report_path.write_text(_report(), encoding="utf-8")
    code = publish.main(
        [
            "--repo-root",
            str(repo),
            "--input",
            str(report_path),
            "--remote",
            "origin",
            "--bootstrap",
            "--dry-run",
            "--no-fetch",
        ]
    )
    assert code == 0
    assert sha(repo, "HEAD") == before_head
    assert run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).stdout.strip() == (
        "infra/cloud-agent-report-bridge"
    )
    assert dirty.read_text(encoding="utf-8") == "local product note\n"
    assert not ref_exists(remote, "agent/cloud-state")
    for name in PROTECTED_BRANCHES:
        assert sha(remote, name) == before_protected[name]
    listed = run_git(["worktree", "list", "--porcelain"], cwd=repo).stdout
    assert "onepilot-cloud-state-" not in listed


def test_publish_updates_only_cloud_state(tmp_path: Path) -> None:
    repo = init_product_repo(tmp_path / "repo")
    remote = init_bare_remote(tmp_path / "remote.git")
    connect_origin(repo, remote)
    run_git(["checkout", "-b", "infra/feature"], cwd=repo)
    before_protected = {name: sha(remote, name) for name in PROTECTED_BRANCHES}
    before_head = sha(repo, "HEAD")

    report_path = tmp_path / "report.md"
    report_path.write_text(_report(), encoding="utf-8")
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
    assert ref_exists(remote, "agent/cloud-state")
    latest = run_git(
        ["show", f"origin/{schema.REPORT_REF}:{schema.REPORT_PATH}"],
        cwd=repo,
    ).stdout
    assert "Cloud Agent Report" in latest
    assert "infra/cloud-agent-report-bridge" in latest
    for name in PROTECTED_BRANCHES:
        assert sha(remote, name) == before_protected[name]
    assert sha(repo, "HEAD") == before_head
    assert run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).stdout.strip() == (
        "infra/feature"
    )


def test_refuses_missing_branch_without_bootstrap(tmp_path: Path) -> None:
    repo = init_product_repo(tmp_path / "repo")
    remote = init_bare_remote(tmp_path / "remote.git")
    connect_origin(repo, remote)
    report_path = tmp_path / "report.md"
    report_path.write_text(_report(), encoding="utf-8")
    code = publish.main(
        [
            "--repo-root",
            str(repo),
            "--input",
            str(report_path),
            "--remote",
            "origin",
            "--no-fetch",
            "--no-push",
        ]
    )
    assert code == 1
    assert not ref_exists(remote, "agent/cloud-state")


def test_force_git_args_are_rejected(tmp_path: Path) -> None:
    repo = init_product_repo(tmp_path / "repo")
    with pytest.raises(schema.UnsafeRefError):
        publish._run_git(["push", "--force", "origin", "HEAD"], cwd=repo)
    with pytest.raises(schema.UnsafeRefError):
        publish._run_git(["push", "-f", "origin", "HEAD"], cwd=repo)


def test_worktree_cleanup_after_injected_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_product_repo(tmp_path / "repo")
    remote = init_bare_remote(tmp_path / "remote.git")
    connect_origin(repo, remote)
    monkeypatch.setenv("ONEPILOT_REPORT_TEST_FAIL_AFTER", "worktree_created")
    report_path = tmp_path / "report.md"
    report_path.write_text(_report(), encoding="utf-8")
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
            "--no-push",
        ]
    )
    assert code == 1
    listed = run_git(["worktree", "list", "--porcelain"], cwd=repo).stdout
    assert "onepilot-cloud-state-" not in listed
    assert run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).stdout.strip() == "main"
    assert (repo / "README.md").read_text(encoding="utf-8") == "product tree\n"


def test_second_publish_archives_previous(tmp_path: Path) -> None:
    repo = init_product_repo(tmp_path / "repo")
    remote = init_bare_remote(tmp_path / "remote.git")
    connect_origin(repo, remote)
    first = tmp_path / "first.md"
    first.write_text(
        _report(generated_utc="2026-09-05T12:00:00Z", task_name="first-report"),
        encoding="utf-8",
    )
    second = tmp_path / "second.md"
    second.write_text(
        _report(generated_utc="2026-09-05T13:00:00Z", task_name="second-report"),
        encoding="utf-8",
    )
    assert (
        publish.main(
            [
                "--repo-root",
                str(repo),
                "--input",
                str(first),
                "--remote",
                "origin",
                "--bootstrap",
                "--no-fetch",
            ]
        )
        == 0
    )
    assert (
        publish.main(
            [
                "--repo-root",
                str(repo),
                "--input",
                str(second),
                "--remote",
                "origin",
                "--no-fetch",
            ]
        )
        == 0
    )
    latest = run_git(
        ["show", f"origin/{schema.REPORT_REF}:{schema.REPORT_PATH}"],
        cwd=repo,
    ).stdout
    assert "second-report" in latest
    tree = run_git(
        ["ls-tree", "-r", "--name-only", f"origin/{schema.REPORT_REF}"],
        cwd=repo,
    ).stdout
    assert schema.REPORT_PATH in tree
    assert "docs/agent/reports/" in tree
    assert "first-report" in tree or "20260905T120000Z" in tree
