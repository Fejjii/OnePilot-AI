"""Calendar natural-language time window parsing tests."""

from __future__ import annotations

from datetime import datetime

from onepilot.providers.calendar.time_parser import parse_calendar_window


_REF = datetime(2026, 5, 20, 10, 0)  # Wednesday


class TestCalendarTimeParser:
    def test_tomorrow_afternoon_berlin(self) -> None:
        parsed = parse_calendar_window(
            "Am I free tomorrow afternoon?",
            timezone="Europe/Berlin",
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=_REF,
        )
        assert parsed.query_type == "range"
        assert parsed.label == "tomorrow afternoon"
        # May 21 13:00 Berlin ≈ 11:00 UTC
        assert parsed.time_min.hour in {9, 10, 11}
        assert parsed.time_max > parsed.time_min

    def test_friday_at_11am_specific(self) -> None:
        parsed = parse_calendar_window(
            "Am I free Friday at 11 am?",
            timezone="Europe/Berlin",
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=_REF,
        )
        assert parsed.query_type == "specific"
        assert parsed.time_min < parsed.time_max
        duration_min = (parsed.time_max - parsed.time_min).total_seconds() / 60
        assert duration_min == 30

    def test_next_week_range(self) -> None:
        parsed = parse_calendar_window(
            "Suggest three meeting slots next week.",
            timezone="Europe/Berlin",
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=_REF,
        )
        assert parsed.label == "next week"
        assert (parsed.time_max - parsed.time_min).days >= 4
