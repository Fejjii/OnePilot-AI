"""Google Calendar create_event payload tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider


class TestGoogleCalendarCreateEventPayload:
    def test_create_event_sends_local_wall_clock_with_timezone(self) -> None:
        provider = GoogleCalendarProvider(
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            create_enabled=True,
        )
        captured: dict = {}

        def _fake_api_request(method: str, path: str, **kwargs) -> dict:
            captured["json"] = kwargs.get("json")
            return {"id": "evt_123"}

        with patch.object(provider, "_api_request", side_effect=_fake_api_request):
            provider.create_event(
                "Demo call",
                datetime(2026, 6, 13, 16, 0),
                datetime(2026, 6, 13, 16, 30),
                timezone="Europe/Berlin",
            )

        body = captured["json"]
        assert body["start"] == {
            "dateTime": "2026-06-13T16:00:00",
            "timeZone": "Europe/Berlin",
        }
        assert body["end"] == {
            "dateTime": "2026-06-13T16:30:00",
            "timeZone": "Europe/Berlin",
        }
