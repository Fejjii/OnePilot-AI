"""Natural-language calendar window parsing (Europe/Berlin demo defaults)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

_WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_AFTERNOON = re.compile(r"\bafternoon\b", re.IGNORECASE)
_TOMORROW = re.compile(r"\btomorrow\b", re.IGNORECASE)
_NEXT_WEEK = re.compile(r"\b(next week|following week)\b", re.IGNORECASE)
_AMPM = r"a\.?\s*m\.?|p\.?\s*m\.?"
_SCHEDULE_CUE = re.compile(
    r"\b(schedule|book|set up|create|meeting|call|demo|appointment)\b",
    re.IGNORECASE,
)
_WEEKDAY_AT_TIME = re.compile(
    rf"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    rf".{{0,20}}\b(?:at\s+)?(\d{{1,2}})(?::(\d{{2}}))?\s*({_AMPM})?\b",
    re.IGNORECASE,
)
_AT_TIME = re.compile(
    rf"\b(?:at\s+)?(\d{{1,2}})(?::(\d{{2}}))?\s*({_AMPM})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ParsedCalendarWindow:
    """UTC-naive bounds for Google Calendar API calls."""

    time_min: datetime
    time_max: datetime
    timezone: str
    query_type: str  # "range" | "specific"
    label: str = ""


def _local_now(timezone: str, *, reference: datetime | None = None) -> datetime:
    tz = ZoneInfo(timezone)
    if reference is None:
        return datetime.now(tz)
    if reference.tzinfo is None:
        return reference.replace(tzinfo=UTC).astimezone(tz)
    return reference.astimezone(tz)


def _to_utc_naive(local_dt: datetime) -> datetime:
    if local_dt.tzinfo is None:
        return local_dt
    return local_dt.astimezone(UTC).replace(tzinfo=None)


def _normalize_ampm(ampm: str | None) -> str | None:
    if not ampm:
        return None
    cleaned = re.sub(r"[\.\s]", "", ampm.lower())
    if cleaned.startswith("p"):
        return "pm"
    if cleaned.startswith("a"):
        return "am"
    return ampm.lower()


def _parse_hour(hour: int, minute: int, ampm: str | None) -> tuple[int, int]:
    normalized = _normalize_ampm(ampm)
    if normalized:
        if normalized == "pm" and hour < 12:
            hour += 12
        if normalized == "am" and hour == 12:
            hour = 0
    return hour, minute


def _next_weekday(local_now: datetime, weekday: int) -> datetime.date:
    days_ahead = (weekday - local_now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (local_now + timedelta(days=days_ahead)).date()


def parse_calendar_window(
    message: str,
    *,
    timezone: str,
    lookahead_days: int,
    slot_duration_minutes: int,
    reference: datetime | None = None,
) -> ParsedCalendarWindow:
    """Best-effort parsing for demo calendar prompts."""
    lower = message.lower()
    local_now = _local_now(timezone, reference=reference)
    tz = ZoneInfo(timezone)
    duration = timedelta(minutes=max(15, slot_duration_minutes))

    # Friday at 11 am — specific instant
    weekday_match = _WEEKDAY_AT_TIME.search(message)
    if weekday_match:
        day_name = weekday_match.group(1).lower()
        hour = int(weekday_match.group(2))
        minute = int(weekday_match.group(3) or 0)
        ampm = weekday_match.group(4)
        hour, minute = _parse_hour(hour, minute, ampm)
        target_date = _next_weekday(local_now, _WEEKDAY_NAMES[day_name])
        start_local = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            minute,
            tzinfo=tz,
        )
        end_local = start_local + duration
        return ParsedCalendarWindow(
            time_min=_to_utc_naive(start_local),
            time_max=_to_utc_naive(end_local),
            timezone=timezone,
            query_type="specific",
            label=f"{day_name.title()} {hour:02d}:{minute:02d}",
        )

    # Tomorrow afternoon — 13:00–17:00 local
    if _TOMORROW.search(lower):
        target_date = (local_now + timedelta(days=1)).date()
        if _AFTERNOON.search(lower) and not _AT_TIME.search(message):
            start_local = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                13,
                0,
                tzinfo=tz,
            )
            end_local = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                17,
                0,
                tzinfo=tz,
            )
            return ParsedCalendarWindow(
                time_min=_to_utc_naive(start_local),
                time_max=_to_utc_naive(end_local),
                timezone=timezone,
                query_type="range",
                label="tomorrow afternoon",
            )
        tomorrow_at = _AT_TIME.search(message)
        if tomorrow_at:
            hour = int(tomorrow_at.group(1))
            minute = int(tomorrow_at.group(2) or 0)
            ampm = tomorrow_at.group(3)
            hour, minute = _parse_hour(hour, minute, ampm)
            start_local = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                hour,
                minute,
                tzinfo=tz,
            )
            end_local = start_local + duration
            return ParsedCalendarWindow(
                time_min=_to_utc_naive(start_local),
                time_max=_to_utc_naive(end_local),
                timezone=timezone,
                query_type="specific",
                label=f"tomorrow {hour:02d}:{minute:02d}",
            )
        start_local = datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        return ParsedCalendarWindow(
            time_min=_to_utc_naive(start_local),
            time_max=_to_utc_naive(end_local),
            timezone=timezone,
            query_type="range",
            label="tomorrow",
        )

    # Next week — next calendar week Mon–Fri work hours
    if _NEXT_WEEK.search(lower):
        days_until_monday = (7 - local_now.weekday()) % 7 or 7
        monday = (local_now + timedelta(days=days_until_monday)).date()
        start_local = datetime(monday.year, monday.month, monday.day, 0, 0, tzinfo=tz)
        end_local = start_local + timedelta(days=5)
        return ParsedCalendarWindow(
            time_min=_to_utc_naive(start_local),
            time_max=_to_utc_naive(end_local),
            timezone=timezone,
            query_type="range",
            label="next week",
        )

    # Explicit local time for scheduling or availability checks
    at_match = _AT_TIME.search(message)
    if at_match and (
        "free" in lower
        or "available" in lower
        or "busy" in lower
        or _SCHEDULE_CUE.search(lower)
    ):
        hour = int(at_match.group(1))
        minute = int(at_match.group(2) or 0)
        ampm = at_match.group(3)
        hour, minute = _parse_hour(hour, minute, ampm)
        target_date = local_now.date()
        if _TOMORROW.search(lower):
            target_date = (local_now + timedelta(days=1)).date()
        start_local = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            minute,
            tzinfo=tz,
        )
        end_local = start_local + duration
        return ParsedCalendarWindow(
            time_min=_to_utc_naive(start_local),
            time_max=_to_utc_naive(end_local),
            timezone=timezone,
            query_type="specific",
            label=f"{hour:02d}:{minute:02d}",
        )

    lookahead = max(1, lookahead_days)
    start_local = datetime(local_now.year, local_now.month, local_now.day, 0, 0, tzinfo=tz)
    end_local = start_local + timedelta(days=lookahead)
    return ParsedCalendarWindow(
        time_min=_to_utc_naive(start_local),
        time_max=_to_utc_naive(end_local),
        timezone=timezone,
        query_type="range",
        label="default",
    )
