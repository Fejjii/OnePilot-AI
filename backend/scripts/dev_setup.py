#!/usr/bin/env python3
"""
dev_setup.py — first-time local development environment setup.

This script:
1. Verifies Python version (>= 3.11)
2. Installs the backend package in editable mode with dev extras
3. Copies .env.example → .env if .env does not exist
4. Optionally runs Alembic migrations if DATABASE_URL is reachable
5. Prints next steps

Usage:
    python scripts/dev_setup.py
    python scripts/dev_setup.py --skip-migrate
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
ENV_FILE = REPO_ROOT / ".env"

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"  {_GREEN}✓{_RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}⚠{_RESET}  {msg}")


def _err(msg: str) -> None:
    print(f"  {_RED}✗{_RESET}  {msg}")


def check_python() -> None:
    print("\n[1/4] Checking Python version...")
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 11):
        _err(f"Python 3.11+ required, found {major}.{minor}")
        sys.exit(1)
    _ok(f"Python {major}.{minor} ✓")


def install_package() -> None:
    print("\n[2/4] Installing backend package...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        cwd=BACKEND_DIR,
        capture_output=False,
    )
    if result.returncode != 0:
        _err("pip install failed. Check the output above.")
        sys.exit(1)
    _ok("Backend package installed")


def copy_env() -> None:
    print("\n[3/4] Checking .env file...")
    if ENV_FILE.exists():
        _ok(".env already exists — skipping copy")
        return
    if not ENV_EXAMPLE.exists():
        _warn(".env.example not found — skipping")
        return
    shutil.copy(ENV_EXAMPLE, ENV_FILE)
    _ok(f"Created .env from .env.example at {ENV_FILE}")
    _warn("Edit .env and set OPENAI_API_KEY if you want real LLM responses.")


def run_migrations(skip: bool) -> None:
    print("\n[4/4] Running Alembic migrations...")
    if skip:
        _warn("Skipped (--skip-migrate)")
        return

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        _warn(
            "DATABASE_URL not set in environment. "
            "Start infrastructure first (docker compose up -d postgres redis qdrant) "
            "and ensure .env is sourced, then run: cd backend && alembic upgrade head"
        )
        return

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        capture_output=False,
    )
    if result.returncode != 0:
        _err("Migrations failed. Is Postgres running and DATABASE_URL correct?")
        _warn("Start infra: docker compose up -d postgres redis qdrant")
    else:
        _ok("Migrations applied")


def print_next_steps() -> None:
    print("\n" + "─" * 50)
    print("Setup complete. Next steps:")
    print()
    print("  1. Start infrastructure:")
    print("       docker compose up -d postgres redis qdrant")
    print()
    print("  2. Run migrations (if skipped above):")
    print("       cd backend && alembic upgrade head")
    print()
    print("  3. Start backend dev server:")
    print("       cd backend && uvicorn onepilot.api.main:app --reload --port 8000")
    print()
    print("  4. Start frontend dev server (separate terminal):")
    print("       cd frontend && pnpm install && pnpm dev")
    print()
    print("  5. Seed demo data (backend must be running):")
    print("       cd backend && python scripts/seed_demo.py")
    print()
    print("  6. Open http://localhost:3000")
    print()
    print("  7. Run tests:")
    print("       cd backend && pytest -v")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OnePilot AI first-time dev setup")
    parser.add_argument("--skip-migrate", action="store_true", help="Skip Alembic migrations")
    args = parser.parse_args(argv)

    print("\nOnePilot AI — Dev Setup\n" + "─" * 40)
    check_python()
    install_package()
    copy_env()
    run_migrations(skip=args.skip_migrate)
    print_next_steps()
    return 0


if __name__ == "__main__":
    sys.exit(main())
