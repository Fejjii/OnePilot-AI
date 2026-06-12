"""Calendar event approval preparation tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from onepilot.core.config import Settings
from onepilot.providers.calendar.time_parser import ParsedCalendarWindow
from onepilot.services import calendar_service


class TestCalendarEventApproval:
    def test_prepare_event_approval_preserves_tomorrow_3pm_local(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        parsed = ParsedCalendarWindow(
            time_min=datetime(2026, 6, 13, 13, 0),
            time_max=datetime(2026, 6, 13, 13, 30),
            timezone="Europe/Berlin",
            query_type="specific",
            label="tomorrow 15:00",
        )
        monkeypatch.setattr(
            calendar_service,
            "parse_calendar_window",
            lambda *args, **kwargs: parsed,
        )
        settings = Settings(
            GOOGLE_CALENDAR_DEFAULT_TIMEZONE="Europe/Berlin",
            GOOGLE_CALENDAR_SLOT_DURATION_MINUTES=30,
        )
        session = MagicMock()
        principal = MagicMock()

        result = calendar_service.prepare_event_approval(
            session,
            principal=principal,
            message="Schedule a 30 minute meeting demo call tomorrow at 3 p.m.",
            settings=settings,
        )

        slot = result["selected_slot"]
        assert "15:00:00" in slot["start_time"]
        assert "15:30:00" in slot["end_time"]
        assert result["timezone"] == "Europe/Berlin"
        assert result["approval_status"] == "pending"
