#!/usr/bin/env python3
"""Safe Google Calendar connectivity check for local developers (no secrets printed)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent


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


def main() -> int:
    _load_dotenv()
    sys.path.insert(0, str(_BACKEND_ROOT / "src"))

    from onepilot.core.config import calendar_runtime_status, get_settings
    from onepilot.providers import get_calendar_provider, reset_provider_cache
    from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider
    from onepilot.providers.calendar.scope_utils import (
        missing_calendar_scopes,
        scopes_from_tokeninfo,
    )
    from onepilot.providers.email.gmail_auth import GoogleOAuthClient

    reset_provider_cache()
    settings = get_settings()
    runtime = calendar_runtime_status(settings)

    print("=== Google Calendar status (safe) ===\n")
    print(f"configured: {runtime['calendar_configured']}")
    print(f"mode: {runtime['calendar_mode']}")
    print(f"reason: {runtime.get('calendar_status_reason') or 'ok'}")
    print(f"calendar_id: {settings.GOOGLE_CALENDAR_ID or 'primary'}")
    print(f"timezone: {settings.GOOGLE_CALENDAR_DEFAULT_TIMEZONE}")

    if not settings.has_calendar_oauth:
        print("\nOAuth credentials incomplete. See docs/google_workspace_oauth_setup.md")
        return 1

    try:
        oauth = GoogleOAuthClient(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        )
        access = oauth.get_access_token()
        granted = scopes_from_tokeninfo(access)
        missing = missing_calendar_scopes(granted) if granted else []
        if missing:
            print("scope_check: missing_calendar_scope")
            print("missing_scopes_count:", len(missing))
        else:
            print("scope_check: ok")
    except Exception:
        print("scope_check: token_refresh_failed")
        return 1

    provider = get_calendar_provider(settings)
    if isinstance(provider, GoogleCalendarProvider):
        try:
            count = provider.count_events_next_days(7)
            print(f"events_next_7_days_count: {count}")
        except Exception:
            print("events_next_7_days_count: unavailable")
            print("api_probe: failed (see reason above)")
            return 1

    print("\nDone.")
    return 0 if runtime["calendar_mode"] == "live" else 1


if __name__ == "__main__":
    raise SystemExit(main())
