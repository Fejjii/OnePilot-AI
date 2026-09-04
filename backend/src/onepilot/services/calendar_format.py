"""User-facing calendar tool output formatting (no secrets, IDs, or provider jargon)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from onepilot.providers.calendar.slot_utils import events_overlap
from onepilot.schemas.calendar import CalendarEvent

_ISO_LIKE = re.compile(r"\d{4}[- ]?\d{2}[- ]?\d{2}T\d{2}:\d{2}")
_PROVIDER_JARGON = re.compile(
    r"(?i)\b(provider mode|google calendar|calendar_id|event_id|unhealthy|"
    r"/health|/providers)\b"
)


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


def public_person_label(value: str) -> str:
    """Turn an email or raw attendee string into a recruiter-facing name."""
    text = value.strip()
    if not text:
        return ""
    if "@" in text and " " not in text:
        local = text.split("@", 1)[0]
        return local.replace(".", " ").replace("_", " ").title()
    return text


def _timezone_footer(timezone: str) -> str:
    return f"Times shown in {timezone}."


def _unavailable_calendar_message(*, action: str) -> str:
    return f"I couldn't {action} right now. Please try again in a moment."


def _window_phrase(label: str) -> str:
    cleaned = str(label or "").strip().lower()
    if cleaned in {"this week", "next week", "tomorrow", "tomorrow afternoon"}:
        return cleaned
    return ""


def format_meetings_response(raw: dict) -> str:
    """Render a seeded/live meeting list. Never returns availability slots."""
    if raw.get("mode") == "unhealthy" or raw.get("status") == "error":
        return _unavailable_calendar_message(action="read the calendar")

    timezone = raw.get("timezone", "Europe/Berlin")
    phrase = _window_phrase(str(raw.get("window_label") or ""))
    events = _load_listed_events(raw.get("events") or raw.get("busy_events") or [])
    events.sort(key=lambda event: event.start_time)

    if not events:
        if phrase:
            return f"No meetings are on the calendar {phrase}."
        return "No meetings are on the calendar in that window."

    heading = "Upcoming meetings"
    if phrase:
        heading = f"Upcoming meetings {phrase}"
    lines = [f"{heading}:"]
    for idx, event in enumerate(events, start=1):
        when = format_local_slot_range(event.start_time, event.end_time, timezone)
        title = event.summary.strip() or "Meeting"
        lines.append(f"{idx}. {title} — {when}")
        detail = _meeting_detail_line(event)
        if detail:
            lines.append(f"   {detail}")
    lines.append(_timezone_footer(timezone))
    return "\n".join(lines)


def format_availability_response(raw: dict) -> str:
    timezone = raw.get("timezone", "Europe/Berlin")

    if raw.get("mode") == "unhealthy" or raw.get("status") == "error":
        return _unavailable_calendar_message(action="check availability")

    query_type = raw.get("query_type", "range")
    busy = _load_busy_events(raw.get("busy_events") or [])
    slots = raw.get("available_slots") or []

    if query_type == "specific":
        return _format_specific_availability(raw, busy, slots, timezone)

    free = [s for s in slots if s.get("available", True)]
    label = str(raw.get("window_label") or "").strip().lower()
    lines = ["Available time slots:", "These are open times, not existing meetings."]
    if free:
        if label == "tomorrow afternoon":
            lines.append("Open times tomorrow afternoon:")
        elif label in {"this week", "next week"}:
            lines.append(f"Open times {label}:")
        for idx, slot in enumerate(free[:5], start=1):
            start = _parse_utc_naive(slot.get("start_time"))
            end = _parse_utc_naive(slot.get("end_time"))
            lines.append(f"{idx}. {format_local_slot_range(start, end, timezone)}")
    else:
        lines.append("No open times in the requested window.")
    lines.append(_timezone_footer(timezone))
    return "\n".join(lines)


def _format_specific_availability(
    raw: dict,
    busy: list[CalendarEvent],
    slots: list[dict],
    timezone: str,
) -> str:
    lines = ["Available time slots:", "These are open times, not existing meetings."]
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
        when = format_local_slot_range(start, end, timezone)
        if is_free:
            lines.append(f"That time is open ({when}).")
        else:
            at_time = format_local_time(start, timezone)
            lines.append(
                f"That time is not open ({at_time}). It overlaps an existing meeting."
            )
        lines.append(_timezone_footer(timezone))
        return "\n".join(lines)

    if busy:
        lines.append("That time overlaps an existing meeting.")
        lines.append(_timezone_footer(timezone))
        return "\n".join(lines)

    lines.append("That time is open.")
    lines.append(_timezone_footer(timezone))
    return "\n".join(lines)


def format_suggestion_response(raw: dict) -> str:
    timezone = raw.get("timezone", "Europe/Berlin")

    if raw.get("mode") == "unhealthy" or raw.get("status") == "error":
        return _unavailable_calendar_message(action="find open meeting times")

    slots = raw.get("suggested_slots") or []
    label = str(raw.get("window_label") or "").strip().lower()
    lines = [
        "Available meeting times:",
        "These are open slots you can book, not existing meetings.",
    ]
    if not slots:
        lines.append("No open meeting times could be suggested for that window.")
        lines.append(_timezone_footer(timezone))
        return "\n".join(lines)

    if label == "next week":
        lines.append("Suggested open times next week:")
    elif label == "this week":
        lines.append("Suggested open times this week:")
    for idx, slot in enumerate(slots, start=1):
        start = _parse_utc_naive(slot.get("start_time"))
        end = _parse_utc_naive(slot.get("end_time"))
        lines.append(f"{idx}. {format_local_slot_range(start, end, timezone)}")
    lines.append(_timezone_footer(timezone))
    return "\n".join(lines)


def format_proposal_response(raw: dict) -> str:
    payload = raw.get("approval_payload") or {}
    slot = raw.get("selected_slot") or {}
    timezone = str(payload.get("timezone") or raw.get("timezone") or "Europe/Berlin")
    start_raw = slot.get("start_time") or payload.get("start_time")
    end_raw = slot.get("end_time") or payload.get("end_time")
    when = ""
    if start_raw and end_raw:
        when = format_local_slot_range(
            _parse_utc_naive(start_raw),
            _parse_utc_naive(end_raw),
            timezone,
        )
    lines = [
        f"Title: {payload.get('summary', 'Meeting')}",
        f"Date and time: {when}" if when else "Date and time: To be confirmed",
        f"Timezone: {timezone}",
        f"Approval status: {raw.get('approval_status', 'pending')}",
        "Next action: Review and approve to create this meeting.",
        "This meeting will be created only after you approve it.",
    ]
    attendees = [
        public_person_label(str(item))
        for item in (payload.get("attendees") or [])
        if str(item).strip()
    ]
    attendees = [name for name in attendees if name]
    if attendees:
        lines.insert(3, f"Attendees: {', '.join(attendees)}")
    return "\n".join(lines)


def _meeting_detail_line(event: CalendarEvent) -> str:
    people = [public_person_label(name) for name in event.attendees if str(name).strip()]
    people = [name for name in people if name]
    parts: list[str] = []
    if people:
        parts.append(", ".join(people))
    if event.company:
        parts.append(event.company.strip())
    return " · ".join(part for part in parts if part)


def _load_listed_events(rows: list) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    for row in rows:
        if isinstance(row, CalendarEvent):
            events.append(row)
            continue
        if not isinstance(row, dict):
            continue
        start_raw = row.get("start_time") or row.get("start")
        end_raw = row.get("end_time") or row.get("end")
        if not start_raw or not end_raw:
            continue
        events.append(
            CalendarEvent(
                id=str(row.get("id", "")),
                summary=str(row.get("summary") or "Meeting"),
                start_time=_parse_utc_naive(start_raw),
                end_time=_parse_utc_naive(end_raw),
                attendees=[str(item) for item in (row.get("attendees") or []) if str(item).strip()],
                company=str(row["company"]).strip() if row.get("company") else None,
                location=str(row["location"]).strip() if row.get("location") else None,
            )
        )
    return events


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


def contains_provider_jargon(text: str) -> bool:
    """Return True if recruiter-facing copy leaked provider/internal wording."""
    return bool(_PROVIDER_JARGON.search(text))
