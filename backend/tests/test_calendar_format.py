"""Calendar answer formatting and timezone display tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from onepilot.providers.calendar.time_parser import parse_calendar_window
from onepilot.services.calendar_format import (
    contains_raw_iso_timestamps,
    format_availability_response,
    format_suggestion_response,
)


_REF = datetime(2026, 5, 20, 10, 0)  # Wednesday
_TZ = "Europe/Berlin"


class TestCalendarFormat:
    def test_friday_11am_displays_local_not_utc(self) -> None:
        parsed = parse_calendar_window(
            "Am I free Friday at 11 am?",
            timezone=_TZ,
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=_REF,
        )
        # May 22 11:00 Berlin = 09:00 UTC
        assert parsed.time_min.hour == 9

        raw = {
            "mode": "live",
            "timezone": _TZ,
            "query_type": "specific",
            "window_label": parsed.label,
            "time_min": parsed.time_min.isoformat(),
            "time_max": parsed.time_max.isoformat(),
            "busy_events": [],
            "available_slots": [
                {
                    "start_time": parsed.time_min.isoformat(),
                    "end_time": parsed.time_max.isoformat(),
                    "available": True,
                }
            ],
        }
        text = format_availability_response(raw)
        assert "11:00" in text
        assert "09:00" not in text
        assert not contains_raw_iso_timestamps(text)
        assert "Calendar availability checked in Europe/Berlin" in text

    def test_specific_query_detects_busy_with_timezone_field(self) -> None:
        from onepilot.providers.calendar.event_utils import parse_event_bounds

        ev_start, ev_end, _ = parse_event_bounds(
            {"dateTime": "2026-05-22T11:00:00", "timeZone": "Europe/Berlin"},
            {"dateTime": "2026-05-22T12:00:00", "timeZone": "Europe/Berlin"},
            default_timezone="Europe/Berlin",
        )
        parsed = parse_calendar_window(
            "Am I free Friday at 11 am?",
            timezone=_TZ,
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=_REF,
        )
        raw = {
            "mode": "live",
            "timezone": _TZ,
            "query_type": "specific",
            "window_label": parsed.label,
            "time_min": parsed.time_min.isoformat(),
            "time_max": parsed.time_max.isoformat(),
            "busy_events": [
                {
                    "id": "evt_1",
                    "start_time": ev_start.isoformat(),
                    "end_time": ev_end.isoformat(),
                }
            ],
            "available_slots": [
                {
                    "start_time": parsed.time_min.isoformat(),
                    "end_time": parsed.time_max.isoformat(),
                    "available": False,
                }
            ],
            "conflict_count": 1,
            "has_conflicts": True,
        }
        text = format_availability_response(raw)
        assert "not available" in text.lower() or "busy" in text.lower()
        assert "11:00" in text

    def test_specific_query_detects_busy_at_11_local(self) -> None:
        parsed = parse_calendar_window(
            "Am I free Friday at 11 am?",
            timezone=_TZ,
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=_REF,
        )
        # Event 11:00–12:00 Berlin stored as UTC-naive
        busy_start = parsed.time_min
        busy_end = busy_start + timedelta(hours=1)
        raw = {
            "mode": "live",
            "timezone": _TZ,
            "query_type": "specific",
            "window_label": parsed.label,
            "time_min": parsed.time_min.isoformat(),
            "time_max": parsed.time_max.isoformat(),
            "busy_events": [
                {
                    "id": "evt_1",
                    "start_time": busy_start.isoformat(),
                    "end_time": busy_end.isoformat(),
                }
            ],
            "available_slots": [
                {
                    "start_time": parsed.time_min.isoformat(),
                    "end_time": parsed.time_max.isoformat(),
                    "available": False,
                }
            ],
        }
        text = format_availability_response(raw)
        assert "not available" in text.lower() or "busy" in text.lower()
        assert "11:00" in text
        assert "09:00" not in text
        assert not contains_raw_iso_timestamps(text)

    def test_tomorrow_afternoon_shows_local_afternoon_slots(self) -> None:
        parsed = parse_calendar_window(
            "Am I free tomorrow afternoon?",
            timezone=_TZ,
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=_REF,
        )
        slots = []
        cursor = parsed.time_min
        while cursor < parsed.time_max:
            end = cursor + timedelta(minutes=30)
            slots.append(
                {
                    "start_time": cursor.isoformat(),
                    "end_time": end.isoformat(),
                    "available": True,
                }
            )
            cursor = end

        raw = {
            "mode": "live",
            "timezone": _TZ,
            "query_type": "range",
            "window_label": "tomorrow afternoon",
            "available_slots": slots[:3],
            "busy_events": [],
        }
        text = format_availability_response(raw)
        assert "tomorrow afternoon" in text.lower()
        assert "13:00" in text
        assert "13:30" in text
        assert not contains_raw_iso_timestamps(text)

    def test_slot_suggestions_use_local_times(self) -> None:
        monday_utc = datetime(2026, 5, 25, 7, 0, tzinfo=UTC).replace(tzinfo=None)
        raw = {
            "mode": "live",
            "timezone": _TZ,
            "window_label": "next week",
            "suggested_slots": [
                {
                    "start_time": monday_utc.isoformat(),
                    "end_time": (monday_utc + timedelta(minutes=30)).isoformat(),
                    "available": True,
                },
                {
                    "start_time": (monday_utc + timedelta(minutes=30)).isoformat(),
                    "end_time": (monday_utc + timedelta(hours=1)).isoformat(),
                    "available": True,
                },
                {
                    "start_time": (monday_utc + timedelta(hours=1)).isoformat(),
                    "end_time": (monday_utc + timedelta(hours=1, minutes=30)).isoformat(),
                    "available": True,
                },
            ],
        }
        text = format_suggestion_response(raw)
        assert "Suggested meeting slots next week" in text
        assert "Monday" in text
        assert "09:00" in text
        assert "07:00" not in text
        assert not contains_raw_iso_timestamps(text)

    def test_unhealthy_does_not_claim_open_slots(self) -> None:
        raw = {
            "mode": "unhealthy",
            "status": "error",
            "timezone": _TZ,
            "error_code": "missing_calendar_scope",
        }
        text = format_availability_response(raw)
        assert "No open slots" not in text
        assert "unhealthy" in text.lower()
