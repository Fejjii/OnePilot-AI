#!/usr/bin/env python3
"""Publish a sanitized Cloud agent report to agent/cloud-state.

Uses a temporary git worktree so the product working tree is not switched.
Never force-pushes. Never updates main or deployment/* refs.

Does not access iCloud. GitHub is the only Cloud → Mac bridge.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from agent_report import (
    FORBIDDEN_REFS,
    REPORT_ARCHIVE_DIR,
    REPORT_MAX_ARCHIVED,
    REPORT_PATH,
    REPORT_REF,
    ReportFormatError,
    SecretScanError,
    UnsafeRefError,
    archive_filename,
    assert_safe_ref,
    parse_and_sanitize,
    render_report,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_FAIL_AFTER_ENV = "ONEPILOT_REPORT_TEST_FAIL_AFTER"


@dataclass(frozen=True)
class ProductSnapshot:
    head: str
    branch: str
    porcelain: str


class PublishError(RuntimeError):
    """Raised for publisher safety or git failures (never includes secrets)."""


def _run_git(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    input_text: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if args and args[0] == "push":
        if any(part in {"--force", "-f", "--force-with-lease"} for part in args):
            raise UnsafeRefError("refusing git --force")
        if any(part.startswith("+") for part in args[1:]):
            raise UnsafeRefError("refusing forced refspec")
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
        env=env,
    )
    if check and result.returncode != 0:
        raise PublishError(_safe_git_error(args, result))
    return result


def _safe_git_error(args: list[str], result: subprocess.CompletedProcess[str]) -> str:
    # Never echo command output; it can contain worktree paths only, but
    # keep the message generic so secret-like file contents cannot leak.
    verb = args[0] if args else "git"
    return f"git {verb} failed (exit {result.returncode})"


def _git_stdout(args: list[str], *, cwd: Path, check: bool = True) -> str:
    return _run_git(args, cwd=cwd, check=check).stdout.strip()


def snapshot_product(repo_root: Path) -> ProductSnapshot:
    head = _git_stdout(["rev-parse", "HEAD"], cwd=repo_root)
    branch = _git_stdout(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    porcelain = _git_stdout(["status", "--porcelain"], cwd=repo_root, check=True)
    return ProductSnapshot(head=head, branch=branch, porcelain=porcelain)


def assert_product_unchanged(repo_root: Path, before: ProductSnapshot) -> None:
    after = snapshot_product(repo_root)
    if after.head != before.head:
        raise PublishError("product HEAD changed; aborting")
    if after.branch != before.branch:
        raise PublishError("product branch changed; aborting")
    if after.porcelain != before.porcelain:
        raise PublishError("product working tree changed; aborting")


def ref_exists(repo_root: Path, ref: str) -> bool:
    result = _run_git(["rev-parse", "--verify", "--quiet", ref], cwd=repo_root, check=False)
    return result.returncode == 0


def read_ref_sha(repo_root: Path, ref: str) -> str | None:
    result = _run_git(["rev-parse", "--verify", ref], cwd=repo_root, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def protected_ref_shas(repo_root: Path, remote: str) -> dict[str, str | None]:
    shas: dict[str, str | None] = {}
    for name in sorted(FORBIDDEN_REFS):
        shas[name] = read_ref_sha(repo_root, f"{remote}/{name}") or read_ref_sha(
            repo_root, name
        )
    return shas


def assert_protected_refs_unchanged(
    repo_root: Path, remote: str, before: dict[str, str | None]
) -> None:
    after = protected_ref_shas(repo_root, remote)
    for name in FORBIDDEN_REFS:
        if after.get(name) != before.get(name):
            raise UnsafeRefError(f"protected ref changed unexpectedly: {name}")


def ensure_local_identity(cwd: Path) -> None:
    name = _git_stdout(["config", "--get", "user.name"], cwd=cwd, check=False)
    email = _git_stdout(["config", "--get", "user.email"], cwd=cwd, check=False)
    if not name:
        _run_git(["config", "user.name", "OnePilot Cloud Agent"], cwd=cwd)
    if not email:
        _run_git(
            ["config", "user.email", "cloud-agent@users.noreply.github.com"],
            cwd=cwd,
        )


def empty_tree_oid(cwd: Path) -> str:
    return _run_git(["mktree"], cwd=cwd, input_text="").stdout.strip()


def maybe_test_fail(checkpoint: str) -> None:
    if os.environ.get(TEST_FAIL_AFTER_ENV, "") == checkpoint:
        raise PublishError(f"test-injected failure after {checkpoint}")


def cleanup_worktree(repo_root: Path, worktree: Path) -> None:
    if worktree.exists():
        remove = _run_git(
            ["worktree", "remove", "--force", str(worktree)],
            cwd=repo_root,
            check=False,
        )
        if remove.returncode != 0:
            shutil.rmtree(worktree, ignore_errors=True)
            _run_git(["worktree", "prune"], cwd=repo_root, check=False)
    else:
        _run_git(["worktree", "prune"], cwd=repo_root, check=False)


def worktrees_contain(repo_root: Path, path: Path) -> bool:
    listed = _git_stdout(["worktree", "list", "--porcelain"], cwd=repo_root, check=False)
    needle = str(path.resolve())
    return needle in listed


def _fetch_report_ref(repo_root: Path, remote: str) -> bool:
    result = _run_git(
        ["fetch", remote, f"{REPORT_REF}:refs/remotes/{remote}/{REPORT_REF}"],
        cwd=repo_root,
        check=False,
    )
    return result.returncode == 0


def _create_bootstrap_commit(repo_root: Path) -> str:
    ensure_local_identity(repo_root)
    tree = empty_tree_oid(repo_root)
    return _git_stdout(
        ["commit-tree", tree, "-m", "chore(agent): bootstrap agent/cloud-state"],
        cwd=repo_root,
    )


def _write_report_files(worktree: Path, rendered: str, archive_name: str) -> None:
    latest = worktree / REPORT_PATH
    latest.parent.mkdir(parents=True, exist_ok=True)
    previous = latest.read_text(encoding="utf-8") if latest.is_file() else None
    latest.write_text(rendered, encoding="utf-8")

    archive_dir = worktree / REPORT_ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    if previous and previous.strip() and previous != rendered:
        archived = archive_dir / archive_name
        if not archived.exists():
            # Prefer a name derived from the previous report when parseable.
            archived.write_text(previous, encoding="utf-8")
    current_archive = archive_dir / archive_name
    current_archive.write_text(rendered, encoding="utf-8")

    existing = sorted(p for p in archive_dir.iterdir() if p.is_file() and p.suffix == ".md")
    overflow = existing[: max(0, len(existing) - REPORT_MAX_ARCHIVED)]
    for stale in overflow:
        stale.unlink()

    readme = worktree / "README.md"
    if not readme.is_file():
        readme.write_text(
            "# agent/cloud-state\n\n"
            "Persistent sanitized Cloud-agent reports. "
            "This is not a product or deployment branch.\n\n"
            f"Latest report: `{REPORT_PATH}`\n",
            encoding="utf-8",
        )


def _commit_report(worktree: Path, task_name: str) -> bool:
    ensure_local_identity(worktree)
    _run_git(["add", "--", REPORT_PATH, REPORT_ARCHIVE_DIR, "README.md"], cwd=worktree)
    status = _git_stdout(["status", "--porcelain"], cwd=worktree)
    if not status:
        return False
    _run_git(
        ["commit", "-m", f"chore(agent): publish Cloud report ({task_name})"],
        cwd=worktree,
    )
    return True


def _push_report_ref(worktree: Path, remote: str) -> None:
    dest = assert_safe_ref(REPORT_REF)
    dest_ref = f"refs/heads/{dest}"
    # Explicit dest-only refspec. Never '+' / --force.
    _run_git(["push", remote, f"HEAD:{dest_ref}"], cwd=worktree)


def publish_report(
    *,
    repo_root: Path,
    report_text: str,
    remote: str = "origin",
    bootstrap: bool = False,
    push: bool = True,
    fetch: bool = True,
    worktree_parent: Path | None = None,
) -> dict[str, str]:
    report = parse_and_sanitize(report_text)
    rendered = render_report(report)
    dest = assert_safe_ref(REPORT_REF)
    if dest in FORBIDDEN_REFS:
        raise UnsafeRefError(f"refusing to publish to protected ref: {dest}")

    product = snapshot_product(repo_root)
    protected_before = protected_ref_shas(repo_root, remote)
    if fetch:
        _fetch_report_ref(repo_root, remote)

    remote_ref = f"{remote}/{REPORT_REF}"
    local_ref = f"refs/heads/{REPORT_REF}"
    has_remote = ref_exists(repo_root, remote_ref)
    has_local = ref_exists(repo_root, local_ref)
    if not has_remote and not has_local and not bootstrap:
        raise PublishError(
            f"{REPORT_REF} does not exist. After this infrastructure is merged, "
            "bootstrap once with --bootstrap (do not use main or deployment refs)."
        )

    parent = worktree_parent or Path(tempfile.mkdtemp(prefix="onepilot-cloud-state-"))
    worktree = parent / "worktree"
    worktree.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        if has_remote:
            start = remote_ref
        elif has_local:
            start = local_ref
        else:
            start = _create_bootstrap_commit(repo_root)
        _run_git(
            ["worktree", "add", "-B", REPORT_REF, str(worktree), start],
            cwd=repo_root,
        )
        created = True
        maybe_test_fail("worktree_created")
        # The new branch name lives only in this worktree.
        current = _git_stdout(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree)
        if current != REPORT_REF:
            raise PublishError("worktree is not on agent/cloud-state")
        _write_report_files(worktree, rendered, archive_filename(report))
        _commit_report(worktree, report.task_name)
        maybe_test_fail("committed")
        if push:
            _push_report_ref(worktree, remote)
        published_sha = _git_stdout(["rev-parse", "HEAD"], cwd=worktree)
    finally:
        if created or worktree.exists():
            cleanup_worktree(repo_root, worktree)
        if worktree_parent is None:
            shutil.rmtree(parent, ignore_errors=True)

    assert_product_unchanged(repo_root, product)
    assert_protected_refs_unchanged(repo_root, remote, protected_before)
    if worktrees_contain(repo_root, worktree):
        raise PublishError("temporary worktree was not cleaned up")

    return {
        "ref": REPORT_REF,
        "path": REPORT_PATH,
        "status": report.status,
        "task_name": report.task_name,
        "source_sha": report.source_sha,
        "published_sha": published_sha,
        "pushed": "true" if push else "false",
    }


def _read_input(path: Path | None) -> str:
    if path is None or str(path) == "-":
        return sys.stdin.read()
    if not path.is_file():
        raise PublishError(f"report file not found: {path}")
    return path.read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            f"Publish a sanitized report to {REPORT_REF}:{REPORT_PATH}. "
            "Never force-pushes. Never updates main or deployment branches."
        )
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=None,
        help="Prepared report markdown (use - for stdin)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Product repository root (working tree is preserved)",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Git remote that receives only agent/cloud-state (default: origin)",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Create agent/cloud-state if it does not exist (orphan/empty start)",
    )
    parser.add_argument(
        "--push",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Push agent/cloud-state (default: yes). --no-push keeps the commit local.",
    )
    parser.add_argument(
        "--fetch",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch origin/agent/cloud-state before publishing (default: yes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate/sanitize and prepare a worktree commit, but do not push",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and sanitize a report file; do not publish",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw = _read_input(args.input)
        if args.check:
            report = parse_and_sanitize(raw)
            print(
                f"ok: report valid status={report.status} task={report.task_name} "
                f"ref={REPORT_REF} path={REPORT_PATH}"
            )
            return 0
        result = publish_report(
            repo_root=args.repo_root,
            report_text=raw,
            remote=args.remote,
            bootstrap=args.bootstrap,
            push=False if args.dry_run else args.push,
            fetch=args.fetch,
        )
        pushed = result["pushed"] == "true"
        action = "published" if pushed else "prepared (not pushed)"
        print(
            f"{action} {result['ref']}:{result['path']} "
            f"status={result['status']} task={result['task_name']}"
        )
        return 0
    except BrokenPipeError:
        return 0
    except (ReportFormatError, PublishError, UnsafeRefError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except SecretScanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("Refusing to publish (fail-closed). No ref was updated.", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
