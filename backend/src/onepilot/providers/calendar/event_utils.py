"""Google Calendar event parsing and busy-blocking rules (no private data)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo


def is_blocking_event(item: dict) -> bool:
    """Return True when an event should block availability."""
    if str(item.get("status") or "").lower() == "cancelled":
        return False
    if str(item.get("transparency") or "").lower() == "transparent":
        return False
    start = item.get("start") or {}
    end = item.get("end") or {}
    if not isinstance(start, dict) or not isinstance(end, dict):
        return False
    # Timed events use dateTime; all-day events use date.
    return bool(start.get("dateTime") or start.get("date"))


def parse_event_bounds(
    start: dict | None,
    end: dict | None,
    *,
    default_timezone: str,
) -> tuple[datetime, datetime, str]:
    """Parse Google start/end to UTC-naive bounds.

    Returns (start, end, kind) where kind is ``timed`` or ``allday``.
    """
    start = start or {}
    end = end or {}
    tz = ZoneInfo(default_timezone)

    if start.get("dateTime"):
        start_local = _parse_date_time(str(start["dateTime"]), start.get("timeZone"), default_timezone)
        end_local = _parse_date_time(
            str(end.get("dateTime") or start["dateTime"]),
            end.get("timeZone") or start.get("timeZone"),
            default_timezone,
        )
        if end_local <= start_local:
            end_local = start_local + timedelta(minutes=30)
        return (
            _to_utc_naive(start_local),
            _to_utc_naive(end_local),
            "timed",
        )

    if start.get("date"):
        start_date = datetime.fromisoformat(str(start["date"])).date()
        end_date_raw = str(end.get("date") or start["date"])
        end_date = datetime.fromisoformat(end_date_raw).date()
        if end_date <= start_date:
            end_date = start_date + timedelta(days=1)
        day_start = datetime(start_date.year, start_date.month, start_date.day, 0, 0, tzinfo=tz)
        day_end = datetime(end_date.year, end_date.month, end_date.day, 0, 0, tzinfo=tz)
        return (_to_utc_naive(day_start), _to_utc_naive(day_end), "allday")

    now = datetime.now(UTC).replace(tzinfo=None)
    return now, now + timedelta(minutes=30), "unknown"


def _parse_date_time(raw: str, tz_name: str | None, default_timezone: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed
    zone = ZoneInfo(str(tz_name or default_timezone))
    return parsed.replace(tzinfo=zone)


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def overlaps_window(
    event_start: datetime,
    event_end: datetime,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    """True when [event_start, event_end) overlaps [window_start, window_end)."""
    return event_start < window_end and event_end > window_start
