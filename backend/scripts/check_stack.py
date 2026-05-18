#!/usr/bin/env python3
"""
check_stack.py — verify that all OnePilot AI services are reachable.

Usage:
    python scripts/check_stack.py
    python scripts/check_stack.py --backend-url http://localhost:8000

Exit code 0 if all required services pass; 1 if any required service fails.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Check:
    name: str
    fn: Callable[[], tuple[bool, str]]
    required: bool = True
    result: bool = field(default=False, init=False)
    detail: str = field(default="", init=False)

    def run(self) -> None:
        try:
            self.result, self.detail = self.fn()
        except Exception as exc:  # noqa: BLE001
            self.result = False
            self.detail = str(exc)


def _http_get(url: str, timeout: int = 5) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 400, f"HTTP {resp.status}"
    except urllib.error.URLError as exc:
        return False, str(exc.reason)


def _check_postgres(url: str) -> tuple[bool, str]:
    try:
        import psycopg  # type: ignore[import]

        with psycopg.connect(url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True, "connected"
    except ImportError:
        return False, "psycopg not installed"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _check_redis(url: str) -> tuple[bool, str]:
    try:
        import redis as redis_lib  # type: ignore[import]

        r = redis_lib.from_url(url, socket_connect_timeout=5)
        r.ping()
        return True, "PONG"
    except ImportError:
        return False, "redis package not installed"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def build_checks(
    backend_url: str,
    postgres_url: str,
    redis_url: str,
    qdrant_url: str,
) -> list[Check]:
    return [
        Check(
            "Backend /health",
            lambda: _http_get(f"{backend_url}/health"),
            required=True,
        ),
        Check(
            "PostgreSQL",
            lambda: _check_postgres(postgres_url.replace("+psycopg", "").replace("+asyncpg", "")),
            required=True,
        ),
        Check(
            "Redis",
            lambda: _check_redis(redis_url),
            required=False,
        ),
        Check(
            "Qdrant /healthz",
            lambda: _http_get(f"{qdrant_url}/healthz"),
            required=False,
        ),
        Check(
            "Frontend root",
            lambda: _http_get("http://localhost:3000"),
            required=False,
        ),
    ]


_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"


def _icon(result: bool, required: bool) -> str:
    if result:
        return f"{_GREEN}✓{_RESET}"
    return f"{_RED}✗{_RESET}" if required else f"{_YELLOW}⚠{_RESET}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check OnePilot AI stack health")
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument(
        "--postgres-url",
        default="postgresql+psycopg://onepilot:onepilot@localhost:5432/onepilot",
    )
    parser.add_argument("--redis-url", default="redis://localhost:6379/0")
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    args = parser.parse_args(argv)

    checks = build_checks(
        backend_url=args.backend_url,
        postgres_url=args.postgres_url,
        redis_url=args.redis_url,
        qdrant_url=args.qdrant_url,
    )

    print("\nOnePilot AI — Stack Health Check\n" + "─" * 40)
    for check in checks:
        check.run()
        label = "required" if check.required else "optional"
        icon = _icon(check.result, check.required)
        print(f"  {icon}  {check.name:<25} [{label}]  {check.detail}")

    print("─" * 40)
    failed_required = [c for c in checks if c.required and not c.result]
    if failed_required:
        names = ", ".join(c.name for c in failed_required)
        print(f"\n{_RED}FAIL{_RESET}: {len(failed_required)} required service(s) unhealthy: {names}")
        return 1

    print(f"\n{_GREEN}OK{_RESET}: All required services are healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
