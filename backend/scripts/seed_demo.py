#!/usr/bin/env python3
"""
seed_demo.py — Seed the OnePilot AI demo knowledge base.

How it works
------------
1. Calls POST /demo/setup which upserts the deterministic demo org + user
   (IDs: org_demo_onepilot / usr_demo_admin) and returns a bearer token.
2. Calls POST /demo/seed with that token, seeding all NovaEdge markdown docs
   into that organization.
3. Calls GET /documents with the same token to verify the seeded docs are
   visible and prints a summary.

Because /demo/setup always resolves to the IDs configured in DEV_ORG_ID /
DEV_USER_ID, the seeded organization is the same one that dev-auth (no
Bearer header) uses — so the UI shows documents immediately after seeding.

Usage
-----
    python scripts/seed_demo.py
    python scripts/seed_demo.py --url http://backend:8000   # inside Docker

Environment variables
---------------------
    BACKEND_URL   Base URL of the running backend (default: http://localhost:8000)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = "http://localhost:8000"


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def _request(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    token: str | None = None,
) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers: dict[str, str] = {}
    if data:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {exc.reason} — {url}\n{body}") from exc


def _wait_for_backend(base_url: str, retries: int = 12, delay: float = 5.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=5):
                print(f"  Backend reachable at {base_url}")
                return
        except Exception:  # noqa: BLE001
            print(f"  Waiting for backend… ({attempt}/{retries})")
            time.sleep(delay)
    raise RuntimeError(f"Backend at {base_url} did not become healthy after {retries} retries.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    import os

    parser = argparse.ArgumentParser(description="Seed OnePilot AI demo data")
    parser.add_argument("--url", default=os.getenv("BACKEND_URL", DEFAULT_URL))
    args = parser.parse_args(argv)
    base_url = args.url.rstrip("/")

    print("\nOnePilot AI — Demo Seed")
    print("─" * 40)

    # ── 1. Health check ────────────────────────────────────────────────────────
    print("\n[1/4] Checking backend health…")
    _wait_for_backend(base_url)

    # ── 2. Upsert deterministic demo org + user ────────────────────────────────
    print("\n[2/4] Setting up demo identity…")
    setup = _request(f"{base_url}/demo/setup", method="POST", payload={})
    token = setup["access_token"]
    user_id = setup["user_id"]
    organization_id = setup["organization_id"]
    org_name = setup.get("organization_name", "OnePilot AI")
    print(f"  Organization : {org_name}  ({organization_id})")
    print(f"  User ID      : {user_id}")

    # ── 3. Seed knowledge base ─────────────────────────────────────────────────
    print("\n[3/4] Seeding NovaEdge knowledge base…")
    seed = _request(f"{base_url}/demo/seed", method="POST", payload={}, token=token)

    # ── 4. Verify — GET /documents with the same token ────────────────────────
    print("\n[4/4] Verifying seeded documents…")
    docs = _request(f"{base_url}/documents", token=token)
    verified_count = docs.get("total", 0)

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "─" * 40)
    print("Seed result:")
    print(f"  organization_id   : {organization_id}")
    print(f"  user_id           : {user_id}")
    print(f"  documents_created : {seed.get('documents_created', '?')}")
    print(f"  documents_skipped : {seed.get('documents_skipped', '?')}")
    print(f"  total_documents   : {seed.get('total_documents', '?')}")
    print(f"  total_chunks      : {seed.get('total_chunks', '?')}")
    print(f"  vector_upserts    : {seed.get('vector_upsert_count', '?')}")
    print(f"  verified_via_api  : {verified_count} document(s) visible")

    if verified_count == 0:
        print("\n[WARN] GET /documents returned 0 — check tenant alignment.")
        return 1

    print("\n✓ Demo data ready.")
    print("  Login credentials:")
    print("    Email    : admin@onepilot.ai")
    print("    Password : Demo1234!")
    print("    URL      : http://localhost:3000/login")
    return 0


if __name__ == "__main__":
    sys.exit(main())
