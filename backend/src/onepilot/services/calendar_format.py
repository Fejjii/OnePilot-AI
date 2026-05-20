"""User-facing calendar tool output formatting (no secrets or private titles)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from onepilot.providers.calendar.slot_utils import events_overlap
from onepilot.schemas.calendar import CalendarEvent

_ISO_LIKE = re.compile(r"\d{4}[- ]?\d{2}[- ]?\d{2}T\d{2}:\d{2}")


def _parse_utc_naive(value: object) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _to_local(dt: datetime, timezone: str) -> datetime:
    utc = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return utc.astimezone(ZoneInfo(timezone))


def format_local_date(dt: datetime, timezone: str) -> str:
    """Weekday, day, month — e.g. Friday, 22 May."""
    local = _to_local(dt, timezone)
    return f"{local.strftime('%A')}, {local.day} {local.strftime('%B')}"


def format_local_time(dt: datetime, timezone: str) -> str:
    local = _to_local(dt, timezone)
    return local.strftime("%H:%M")


def format_local_slot_range(start: datetime, end: datetime, timezone: str) -> str:
    """Human-friendly slot — e.g. Friday, 22 May, 11:00 to 11:30."""
    start_local = _to_local(start, timezone)
    end_local = _to_local(end, timezone)
    if start_local.date() == end_local.date():
        return (
            f"{format_local_date(start, timezone)}, "
            f"{start_local.strftime('%H:%M')} to {end_local.strftime('%H:%M')}"
        )
    return (
        f"{format_local_date(start, timezone)}, {start_local.strftime('%H:%M')} to "
        f"{format_local_date(end, timezone)}, {end_local.strftime('%H:%M')}"
    )


def format_availability_response(raw: dict) -> str:
    mode = raw.get("mode") or raw.get("provider_mode") or "mock"
    timezone = raw.get("timezone", "Europe/Berlin")

    if mode == "unhealthy" or raw.get("status") == "error":
        reason = raw.get("error_code") or "unknown"
        return (
            "I could not check your live Google Calendar because the Calendar provider "
            f"is unhealthy ({reason}). Check provider diagnostics at /health and /providers.\n"
            f"(Checked timezone: {timezone}, provider mode: unhealthy)"
        )

    query_type = raw.get("query_type", "range")
    busy = _load_busy_events(raw.get("busy_events") or [])
    slots = raw.get("available_slots") or []

    if query_type == "specific":
        return _format_specific_availability(raw, busy, slots, timezone, mode)

    free = [s for s in slots if s.get("available", True)]
    label = str(raw.get("window_label") or "").strip().lower()
    lines = [f"Calendar availability checked in {timezone}."]
    if free:
        if label == "tomorrow afternoon":
            lines.append("You are available tomorrow afternoon. Open slots:")
        else:
            lines.append(f"Open slots found: {len(free)}")
        for idx, slot in enumerate(free[:5], start=1):
            start = _parse_utc_naive(slot.get("start_time"))
            end = _parse_utc_naive(slot.get("end_time"))
            lines.append(f"{idx}. {format_local_slot_range(start, end, timezone)}")
    else:
        lines.append("No open slots in the requested window.")
    lines.append(f"(Provider mode: {mode})")
    return "\n".join(lines)


def _format_specific_availability(
    raw: dict,
    busy: list[CalendarEvent],
    slots: list[dict],
    timezone: str,
    mode: str,
) -> str:
    lines = [f"Calendar availability checked in {timezone}."]
    requested_slots = slots or []
    if not requested_slots and raw.get("time_min") and raw.get("time_max"):
        requested_slots = [
            {
                "start_time": raw["time_min"],
                "end_time": raw["time_max"],
                "available": True,
            }
        ]

    if requested_slots:
        slot = requested_slots[0]
        start = _parse_utc_naive(slot.get("start_time"))
        end = _parse_utc_naive(slot.get("end_time"))
        is_free = bool(slot.get("available", True)) and not events_overlap(start, end, busy)

        if is_free:
            when = format_local_slot_range(start, end, timezone)
            lines.append(f"You are available at the requested time ({when}).")
        else:
            when = format_local_date(start, timezone)
            at_time = format_local_time(start, timezone)
            lines.append(
                f"You are not available at {at_time}. "
                "That time overlaps with an existing calendar event."
            )
            lines.append(f"You are busy on {when} at {at_time} {timezone}.")
        lines.append(f"(Provider mode: {mode})")
        return "\n".join(lines)

    if busy:
        lines.append(
            "You are not available at the requested time. "
            "That time overlaps with an existing calendar event."
        )
        lines.append(f"(Provider mode: {mode})")
        return "\n".join(lines)

    lines.append("You are available at the requested time.")
    lines.append(f"(Provider mode: {mode})")
    return "\n".join(lines)


def format_suggestion_response(raw: dict) -> str:
    mode = raw.get("mode") or raw.get("provider_mode") or "mock"
    timezone = raw.get("timezone", "Europe/Berlin")

    if mode == "unhealthy" or raw.get("status") == "error":
        reason = raw.get("error_code") or "unknown"
        return (
            "I could not suggest slots from your live Google Calendar because the Calendar "
            f"provider is unhealthy ({reason}). Check provider diagnostics.\n"
            f"(Checked timezone: {timezone}, provider mode: unhealthy)"
        )

    slots = raw.get("suggested_slots") or []
    label = str(raw.get("window_label") or "").strip().lower()
    lines = [f"Calendar availability checked in {timezone}."]
    if not slots:
        lines.append("No meeting slots could be suggested for that window.")
        lines.append(f"(Provider mode: {mode})")
        return "\n".join(lines)

    if label == "next week":
        lines.append("Suggested meeting slots next week:")
    else:
        lines.append("Suggested meeting slots:")
    for idx, slot in enumerate(slots, start=1):
        start = _parse_utc_naive(slot.get("start_time"))
        end = _parse_utc_naive(slot.get("end_time"))
        lines.append(f"{idx}. {format_local_slot_range(start, end, timezone)}")
    lines.append(f"(Provider mode: {mode})")
    return "\n".join(lines)


def _load_busy_events(rows: list) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    for row in rows:
        if isinstance(row, dict):
            events.append(
                CalendarEvent(
                    id=str(row.get("id", "")),
                    summary="Busy",
                    start_time=_parse_utc_naive(row.get("start_time") or row.get("start")),
                    end_time=_parse_utc_naive(row.get("end_time") or row.get("end")),
                )
            )
        else:
            events.append(row)
    return events


def contains_raw_iso_timestamps(text: str) -> bool:
    """Return True if text still contains machine-readable ISO timestamps."""
    return bool(_ISO_LIKE.search(text))
