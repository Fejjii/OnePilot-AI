"""Local-only git helpers for report-bridge tests. Never touches real remotes."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROTECTED_BRANCHES = (
    "main",
    "deployment/public-demo",
    "deployment/live-google-demo",
)


def run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"git {args} failed in {cwd}: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def init_product_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.name", "Report Bridge Test"], cwd=path)
    run_git(["config", "user.email", "report-bridge-test@example.com"], cwd=path)
    (path / "README.md").write_text("product tree\n", encoding="utf-8")
    (path / "docs" / "agent").mkdir(parents=True, exist_ok=True)
    (path / "docs" / "agent" / "CLOUD_HANDOFF.md").write_text(
        "# Cloud handoff\n\nproject state\n", encoding="utf-8"
    )
    run_git(["add", "README.md", "docs/agent/CLOUD_HANDOFF.md"], cwd=path)
    run_git(["commit", "-m", "init product"], cwd=path)
    run_git(["branch", "deployment/public-demo"], cwd=path)
    run_git(["branch", "deployment/live-google-demo"], cwd=path)
    return path


def init_bare_remote(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "--bare", "-b", "main"], cwd=path)
    return path


def connect_origin(repo: Path, remote: Path) -> None:
    run_git(["remote", "add", "origin", str(remote)], cwd=repo)
    run_git(
        [
            "push",
            "-u",
            "origin",
            "main",
            "deployment/public-demo",
            "deployment/live-google-demo",
        ],
        cwd=repo,
    )


def sha(repo: Path, ref: str) -> str:
    return run_git(["rev-parse", ref], cwd=repo).stdout.strip()


def ref_exists(repo: Path, ref: str) -> bool:
    return run_git(["rev-parse", "--verify", "--quiet", ref], cwd=repo, check=False).returncode == 0
