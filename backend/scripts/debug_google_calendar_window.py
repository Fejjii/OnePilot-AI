#!/usr/bin/env python3
"""Safe Google Calendar window probe — no titles, tokens, or raw payloads."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

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


def _format_rfc3339(dt: datetime) -> str:
    return dt.isoformat()


def main() -> int:
    _load_dotenv()
    sys.path.insert(0, str(_BACKEND_ROOT / "src"))

    from onepilot.core.config import get_settings
    from onepilot.providers.calendar.event_utils import is_blocking_event, parse_event_bounds, overlaps_window
    from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider
    from onepilot.providers.email.gmail_auth import GoogleOAuthClient

    settings = get_settings()
    timezone = settings.GOOGLE_CALENDAR_DEFAULT_TIMEZONE or "Europe/Berlin"
    calendar_id = settings.GOOGLE_CALENDAR_ID or "primary"

    tz = ZoneInfo(timezone)
    window_start_local = datetime(2026, 5, 22, 10, 30, tzinfo=tz)
    window_end_local = datetime(2026, 5, 22, 12, 30, tzinfo=tz)
    requested_start_local = datetime(2026, 5, 22, 11, 0, tzinfo=tz)
    requested_end_local = datetime(2026, 5, 22, 11, 30, tzinfo=tz)

    print("=== Google Calendar window debug (safe) ===\n")
    print(f"calendar_id: {_mask_calendar_id(calendar_id)}")
    print(f"timezone: {timezone}")

    if not settings.has_calendar_oauth:
        print("provider_mode: missing_oauth")
        return 1

    oauth = GoogleOAuthClient(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
    )
    token = oauth.get_access_token()
    status = GoogleCalendarProvider(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        calendar_id=calendar_id,
    ).get_status()
    print(f"provider_mode: {status.mode}")

    params = {
        "timeMin": _format_rfc3339(window_start_local),
        "timeMax": _format_rfc3339(window_end_local),
        "singleEvents": "true",
        "orderBy": "startTime",
        "timeZone": timezone,
        "showDeleted": "false",
        "maxResults": 50,
    }
    print(f"timeMin: {params['timeMin']}")
    print(f"timeMax: {params['timeMax']}")

    cal_path = quote(calendar_id, safe="@._-")
    url = f"{_CALENDAR_API}/calendars/{cal_path}/events"
    with httpx.Client(timeout=20.0) as client:
        response = client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)

        if response.status_code != 200:
            print(f"api_status: {response.status_code}")
            return 1

        items = response.json().get("items") or []
        print(f"events_returned_primary: {len(items)}")

        all_items: list[dict] = list(items)
        list_resp = client.get(
            f"{_CALENDAR_API}/users/me/calendarList",
            headers={"Authorization": f"Bearer {token}"},
            params={"maxResults": 50},
        )
        if list_resp.status_code == 200:
            selected = [
                str(row["id"])
                for row in (list_resp.json().get("items") or [])
                if row.get("selected") is True and row.get("id")
            ]
            print(f"selected_calendars: {len(selected)}")
            seen_ids: set[str] = {str(item.get("id")) for item in items if item.get("id")}
            for cal in selected:
                encoded = quote(cal, safe="@._-")
                per_resp = client.get(
                    f"{_CALENDAR_API}/calendars/{encoded}/events",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                count = 0
                if per_resp.status_code == 200:
                    per_items = per_resp.json().get("items") or []
                    count = len(per_items)
                    for row in per_items:
                        row_id = str(row.get("id") or "")
                        if row_id and row_id not in seen_ids:
                            seen_ids.add(row_id)
                            all_items.append(row)
                print(f"calendar {_mask_calendar_id(cal)} events_in_window: {count}")

        items = all_items
        print(f"events_returned_aggregate: {len(items)}")

    req_start, req_end, _ = parse_event_bounds(
        {"dateTime": requested_start_local.replace(tzinfo=None).isoformat(), "timeZone": timezone},
        {"dateTime": requested_end_local.replace(tzinfo=None).isoformat(), "timeZone": timezone},
        default_timezone=timezone,
    )

    blocking = 0
    for idx, item in enumerate(items, start=1):
        start = item.get("start") or {}
        end = item.get("end") or {}
        ev_start, ev_end, kind = parse_event_bounds(start, end, default_timezone=timezone)
        blocking_flag = is_blocking_event(item)
        overlaps_requested = blocking_flag and overlaps_window(ev_start, ev_end, req_start, req_end)
        if blocking_flag:
            blocking += 1
        print(f"\n--- event {idx} ---")
        print(f"start: {start.get('dateTime') or start.get('date')}")
        print(f"end: {end.get('dateTime') or end.get('date')}")
        print(f"start_timeZone: {start.get('timeZone') or timezone}")
        print(f"status: {item.get('status', 'confirmed')}")
        print(f"transparency: {item.get('transparency', 'opaque')}")
        print(f"event_type: {kind}")
        print(f"considered_busy: {blocking_flag}")
        print(f"overlaps_11_00_11_30: {overlaps_requested}")

    print(f"\nblocking_events: {blocking}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
