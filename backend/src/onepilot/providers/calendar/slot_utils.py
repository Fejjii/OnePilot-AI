"""Shared calendar slot generation helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from onepilot.schemas.calendar import CalendarEvent, CalendarSlot


def parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {value}")
    return int(parts[0]), int(parts[1])


def _to_tz(dt: datetime, tz_name: str) -> datetime:
    tz = ZoneInfo(tz_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC).astimezone(tz)
    return dt.astimezone(tz)


def _from_tz(dt: datetime) -> datetime:
    return dt.astimezone(UTC).replace(tzinfo=None)


def iter_workday_slots(
    time_min: datetime,
    time_max: datetime,
    *,
    timezone: str,
    workday_start: str,
    workday_end: str,
    slot_duration_minutes: int,
) -> list[tuple[datetime, datetime]]:
    """Yield UTC-naive slot boundaries within work hours."""
    start_h, start_m = parse_hhmm(workday_start)
    end_h, end_m = parse_hhmm(workday_end)
    tz = ZoneInfo(timezone)
    local_min = _to_tz(time_min, timezone)
    local_max = _to_tz(time_max, timezone)
    duration = timedelta(minutes=slot_duration_minutes)

    slots: list[tuple[datetime, datetime]] = []
    day = local_min.date()
    end_day = local_max.date()

    while day <= end_day:
        day_start = datetime(day.year, day.month, day.day, start_h, start_m, tzinfo=tz)
        day_end = datetime(day.year, day.month, day.day, end_h, end_m, tzinfo=tz)
        cursor = max(day_start, local_min)
        while cursor + duration <= day_end and cursor + duration <= local_max:
            slot_end = cursor + duration
            if slot_end > local_min:
                slots.append((_from_tz(cursor), _from_tz(slot_end)))
            cursor += duration
        day += timedelta(days=1)

    return slots


def events_overlap(
    slot_start: datetime,
    slot_end: datetime,
    events: list[CalendarEvent],
) -> bool:
    for event in events:
        ev_start = event.start_time
        ev_end = event.end_time
        if ev_start.tzinfo is not None:
            ev_start = ev_start.replace(tzinfo=None)
        if ev_end.tzinfo is not None:
            ev_end = ev_end.replace(tzinfo=None)
        if ev_start < slot_end and ev_end > slot_start:
            return True
    return False


def build_available_slots(
    time_min: datetime,
    time_max: datetime,
    *,
    timezone: str,
    workday_start: str,
    workday_end: str,
    slot_duration_minutes: int,
    busy_events: list[CalendarEvent],
) -> list[CalendarSlot]:
    slots: list[CalendarSlot] = []
    for start, end in iter_workday_slots(
        time_min,
        time_max,
        timezone=timezone,
        workday_start=workday_start,
        workday_end=workday_end,
        slot_duration_minutes=slot_duration_minutes,
    ):
        available = not events_overlap(start, end, busy_events)
        slots.append(CalendarSlot(start_time=start, end_time=end, available=available))
    return slots


def pick_suggested_slots(
    available_slots: list[CalendarSlot],
    *,
    max_slots: int,
) -> list[CalendarSlot]:
    free = [slot for slot in available_slots if slot.available]
    return free[:max_slots]
