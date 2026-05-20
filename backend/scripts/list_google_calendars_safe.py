#!/usr/bin/env python3
"""List Google calendars safely — IDs masked, no event data."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent
_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


def _load_dotenv() -> None:
    for path in (_PROJECT_ROOT / ".env", _BACKEND_ROOT / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _mask_calendar_id(calendar_id: str) -> str:
    if calendar_id == "primary":
        return "primary"
    if "@" in calendar_id:
        local, _, domain = calendar_id.partition("@")
        return f"{local[:2]}***@{domain}"
    return f"{calendar_id[:4]}***"


def main() -> int:
    _load_dotenv()
    sys.path.insert(0, str(_BACKEND_ROOT / "src"))

    from onepilot.core.config import get_settings
    from onepilot.providers.email.gmail_auth import GoogleOAuthClient

    settings = get_settings()
    configured_id = settings.GOOGLE_CALENDAR_ID or "primary"

    print("=== Google calendars (safe) ===\n")
    print(f"configured_calendar_id: {_mask_calendar_id(configured_id)}")

    if not settings.has_calendar_oauth:
        print("provider_mode: missing_oauth")
        return 1

    oauth = GoogleOAuthClient(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
    )
    token = oauth.get_access_token()

    with httpx.Client(timeout=20.0) as client:
        response = client.get(
            f"{_CALENDAR_API}/users/me/calendarList",
            headers={"Authorization": f"Bearer {token}"},
            params={"minAccessRole": "reader", "maxResults": 50},
        )

    if response.status_code != 200:
        print(f"api_status: {response.status_code}")
        return 1

    items = response.json().get("items") or []
    print(f"calendars_returned: {len(items)}\n")

    for idx, item in enumerate(items, start=1):
        cal_id = str(item.get("id") or "")
        selected = cal_id == configured_id or (
            configured_id == "primary" and bool(item.get("primary"))
        )
        print(f"--- calendar {idx} ---")
        print(f"calendar_id: {_mask_calendar_id(cal_id)}")
        print(f"primary: {bool(item.get('primary'))}")
        print(f"selected_in_env: {selected}")
        print(f"accessRole: {item.get('accessRole', 'unknown')}")
        if item.get("backgroundColor"):
            print(f"backgroundColor: {item.get('backgroundColor')}")

    print("\nTip: if your event is not on the configured calendar, set GOOGLE_CALENDAR_ID in .env")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
