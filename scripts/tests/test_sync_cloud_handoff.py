"""Tests for scripts/sync_cloud_handoff.py secret redaction and fail-closed write."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "sync_cloud_handoff.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("sync_cloud_handoff", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync = _load_module()


SAFE_HANDOFF = """# Local handoff

## Completed
- OP-025 merged to main

## Current task
- Finish cloud handoff docs on a feature branch

## Backlog
- HTTP-only cookies

## Recommended next
- Pick a near-term roadmap item

## Architecture
- FastAPI + Next.js, mock Gmail on public demo

## Tests
- pytest + vitest via CI

## Production JWT secret
JWT_SECRET=super-secret-value-do-not-ship

## Raw API keys
OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456
"""


def test_redacts_openai_and_proj_keys() -> None:
    text = (
        "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456 "
        "other=sk-proj-abc_DEF-1234567890abcdefghijklmnop"
    )
    out = sync.redact_text(text)
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in out
    assert "sk-proj-" not in out
    assert "[API_KEY_REDACTED]" in out
    assert "[REDACTED]" in out


def test_redacts_jwt_and_bearer() -> None:
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "c2lnbmF0dXJlX2Jsb2NrX2hlcmVfMTIz"
    )
    out = sync.redact_text(f"Authorization: Bearer {jwt}")
    assert jwt not in out
    assert "Bearer [TOKEN_REDACTED]" in out
    assert "[JWT_REDACTED]" in sync.redact_text(jwt)


def test_redacts_connection_strings_and_url_secrets() -> None:
    text = (
        "DATABASE_URL=postgresql://onepilot:hunter2@db.example.com:5432/app "
        "https://api.example.com/v1?api_key=abcdEFGHijklMNOP"
    )
    out = sync.redact_text(text)
    assert "hunter2" not in out
    assert "abcdEFGHijklMNOP" not in out
    assert "[CONNECTION_REDACTED]" in out or "[REDACTED]" in out
    assert "[URL_SECRET_REDACTED]" in out


def test_redacts_cloud_vendor_and_qdrant_tokens() -> None:
    text = (
        "RAILWAY_TOKEN=rak_abcdefghijklmnopqrstuv "
        "VERCEL_TOKEN=abcdefghijklmnopqrstuvwxyz12 "
        "QDRANT_API_KEY=qdrant_abcdefghijklmnopqrstuv"
    )
    out = sync.redact_text(text)
    assert "rak_abcdefghijklmnopqrstuv" not in out
    assert "qdrant_abcdefghijklmnopqrstuv" not in out
    assert "abcdefghijklmnopqrstuvwxyz12" not in out
    assert "[REDACTED]" in out or "[API_KEY_REDACTED]" in out


def test_redacts_aws_github_pem() -> None:
    pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEAtotallyfakeprivatekeymaterialhere\n"
        "-----END RSA PRIVATE KEY-----"
    )
    text = f"AKIAIOSFODNN7EXAMPLE ghp_{'a' * 36} {pem}"
    out = sync.redact_text(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in out
    assert "ghp_" not in out
    assert "BEGIN RSA PRIVATE KEY" not in out
    assert "[AWS_KEY_REDACTED]" in out
    assert "[GITHUB_TOKEN_REDACTED]" in out
    assert "[PRIVATE_KEY_REDACTED]" in out


def test_preserves_git_shas_and_task_ids() -> None:
    sha = "1c3dd0172250891d71f89c21a4a57e6002a5119d"
    text = f"origin/main {sha} completed OP-025"
    out = sync.redact_text(text)
    assert sha in out
    assert "OP-025" in out
    assert sync.find_residual_secrets(out) == []


def test_extract_drops_secret_sections_keeps_tasks() -> None:
    extracted = sync.extract_safe_handoff(SAFE_HANDOFF)
    headings = {h.lower() for h in extracted.sections}
    assert any("completed" in h for h in headings)
    assert any("current" in h for h in headings)
    assert all("jwt" not in h and "api key" not in h for h in headings)
    joined = "\n".join(extracted.sections.values())
    assert "sk-" not in joined
    assert "super-secret-value-do-not-ship" not in joined
    assert "OP-025" in joined


def test_residual_scan_finds_unredacted_jwt() -> None:
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "c2lnbmF0dXJlX2Jsb2NrX2hlcmVfMTIz"
    )
    assert "jwt" in sync.find_residual_secrets(f"token={jwt}")


def test_write_if_safe_refuses_residual_secrets(tmp_path: Path) -> None:
    target = tmp_path / "CLOUD_HANDOFF.md"
    target.write_text("safe-placeholder\n", encoding="utf-8")
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "c2lnbmF0dXJlX2Jsb2NrX2hlcmVfMTIz"
    )
    with pytest.raises(sync.SecretScanError) as exc:
        sync.write_if_safe(target, f"leaked {jwt}\n")
    assert "jwt" in exc.value.findings
    assert target.read_text(encoding="utf-8") == "safe-placeholder\n"


def test_generate_from_handoff_is_safe_and_useful(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "HANDOFF.md").write_text(SAFE_HANDOFF, encoding="utf-8")
    output = tmp_path / "out.md"
    rendered = sync.generate_cloud_handoff(
        repo_root=repo,
        handoff_path=repo / "HANDOFF.md",
        output_path=output,
        fetch=False,
        generated_at="2026-09-03 15:00",
    )
    assert "sk-" not in rendered
    assert "JWT_SECRET=" not in rendered or "[REDACTED]" in rendered
    assert "super-secret-value-do-not-ship" not in rendered
    assert "OP-025" in rendered
    assert "HTTP-only cookies" in rendered
    assert "canonical" in rendered.lower()
    assert "deployment/live-google-demo" in rendered
    assert "Local-only" in rendered
    assert sync.find_residual_secrets(rendered) == []


def test_generate_without_handoff_uses_defaults(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    rendered = sync.generate_cloud_handoff(
        repo_root=repo,
        handoff_path=repo / "missing-HANDOFF.md",
        output_path=tmp_path / "out.md",
        fetch=False,
        generated_at="2026-09-03 15:00",
    )
    assert "OP-025" in rendered
    assert "OP-026" in rendered
    assert "must not" in rendered.lower()
    assert sync.find_residual_secrets(rendered) == []


def test_cli_dry_run_does_not_write(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    output = tmp_path / "CLOUD_HANDOFF.md"
    code = sync.main(
        [
            "--repo-root",
            str(repo),
            "--handoff",
            str(repo / "nope.md"),
            "--output",
            str(output),
            "--no-fetch",
            "--dry-run",
        ]
    )
    assert code == 0
    assert not output.exists()


def test_cli_check_fail_closed(tmp_path: Path) -> None:
    dirty = tmp_path / "dirty.md"
    dirty.write_text(
        "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456\n",
        encoding="utf-8",
    )
    code = sync.main(["--output", str(dirty), "--check"])
    assert code == 2
    # Original file must remain (check does not rewrite).
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" in dirty.read_text(encoding="utf-8")


def test_cli_writes_only_after_clean_scan(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "HANDOFF.md").write_text(SAFE_HANDOFF, encoding="utf-8")
    output = tmp_path / "docs" / "agent" / "CLOUD_HANDOFF.md"
    code = sync.main(
        [
            "--repo-root",
            str(repo),
            "--handoff",
            str(repo / "HANDOFF.md"),
            "--output",
            str(output),
            "--no-fetch",
        ]
    )
    assert code == 0
    text = output.read_text(encoding="utf-8")
    assert "sk-" not in text
    assert "does not commit or push" in text.lower() or "This script does not commit" in (
        # CLI prints the reminder; file says the generator does not commit.
        output.read_text(encoding="utf-8")
    )
    assert sync.find_residual_secrets(text) == []


def test_prose_about_secrets_is_not_a_false_positive() -> None:
    prose = (
        "Never include API keys, JWTs, bearer tokens, or sk- prefixes. "
        "Do not print Railway or Vercel tokens. Never commit JWT_SECRET."
    )
    assert sync.find_residual_secrets(prose) == []
    assert sync.find_residual_secrets(sync.redact_text(prose)) == []
