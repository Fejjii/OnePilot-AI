"""Google Calendar event parsing and busy-blocking tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from onepilot.providers.calendar.event_utils import (
    is_blocking_event,
    overlaps_window,
    parse_event_bounds,
)
from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider
from onepilot.providers.calendar.slot_utils import build_available_slots, events_overlap
from onepilot.schemas.calendar import CalendarEvent


class TestEventUtils:
    def test_timed_event_without_offset_uses_timezone_field(self) -> None:
        start, end, kind = parse_event_bounds(
            {"dateTime": "2026-05-22T11:00:00", "timeZone": "Europe/Berlin"},
            {"dateTime": "2026-05-22T12:00:00", "timeZone": "Europe/Berlin"},
            default_timezone="Europe/Berlin",
        )
        assert kind == "timed"
        # 11:00 Berlin (CEST) -> 09:00 UTC
        assert start.hour == 9
        assert end.hour == 10

    def test_timed_event_with_offset(self) -> None:
        start, end, kind = parse_event_bounds(
            {"dateTime": "2026-05-22T11:00:00+02:00"},
            {"dateTime": "2026-05-22T12:00:00+02:00"},
            default_timezone="Europe/Berlin",
        )
        assert kind == "timed"
        assert start.hour == 9
        assert end.hour == 10

    def test_cancelled_event_not_blocking(self) -> None:
        item = {
            "status": "cancelled",
            "start": {"dateTime": "2026-05-22T11:00:00", "timeZone": "Europe/Berlin"},
            "end": {"dateTime": "2026-05-22T12:00:00", "timeZone": "Europe/Berlin"},
        }
        assert is_blocking_event(item) is False

    def test_transparent_event_not_blocking(self) -> None:
        item = {
            "transparency": "transparent",
            "start": {"dateTime": "2026-05-22T11:00:00", "timeZone": "Europe/Berlin"},
            "end": {"dateTime": "2026-05-22T12:00:00", "timeZone": "Europe/Berlin"},
        }
        assert is_blocking_event(item) is False

    def test_11_to_12_berlin_blocks_11_to_1130_slot(self) -> None:
        ev_start, ev_end, _ = parse_event_bounds(
            {"dateTime": "2026-05-22T11:00:00", "timeZone": "Europe/Berlin"},
            {"dateTime": "2026-05-22T12:00:00", "timeZone": "Europe/Berlin"},
            default_timezone="Europe/Berlin",
        )
        slot_start = datetime(2026, 5, 22, 9, 0)
        slot_end = datetime(2026, 5, 22, 9, 30)
        event = CalendarEvent(id="1", summary="Busy", start_time=ev_start, end_time=ev_end)
        assert events_overlap(slot_start, slot_end, [event]) is True
        assert overlaps_window(ev_start, ev_end, slot_start, slot_end) is True

    def test_build_available_slots_marks_specific_window_busy(self) -> None:
        ev_start, ev_end, _ = parse_event_bounds(
            {"dateTime": "2026-05-22T11:00:00", "timeZone": "Europe/Berlin"},
            {"dateTime": "2026-05-22T12:00:00", "timeZone": "Europe/Berlin"},
            default_timezone="Europe/Berlin",
        )
        busy = [
            CalendarEvent(id="1", summary="Busy", start_time=ev_start, end_time=ev_end),
        ]
        time_min = datetime(2026, 5, 22, 9, 0)
        time_max = datetime(2026, 5, 22, 9, 30)
        slots = build_available_slots(
            time_min,
            time_max,
            timezone="Europe/Berlin",
            workday_start="09:00",
            workday_end="17:00",
            slot_duration_minutes=30,
            busy_events=busy,
        )
        assert len(slots) == 1
        assert slots[0].available is False


class TestGoogleCalendarEventTimeParsing:
    def test_datetime_with_offset_converts_to_utc_naive(self) -> None:
        parsed = GoogleCalendarProvider._parse_event_time(
            {"dateTime": "2026-05-22T11:00:00+02:00"},
            default_timezone="Europe/Berlin",
        )
        assert parsed.hour == 9
        assert parsed.minute == 0
        assert parsed.tzinfo is None

    def test_datetime_without_offset_uses_timezone(self) -> None:
        parsed = GoogleCalendarProvider._parse_event_time(
            {"dateTime": "2026-05-22T11:00:00", "timeZone": "Europe/Berlin"},
            default_timezone="Europe/Berlin",
        )
        assert parsed.hour == 9
