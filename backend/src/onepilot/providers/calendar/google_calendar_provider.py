from __future__ import annotations

import os
from datetime import datetime

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.calendar.base import CalendarProvider


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar API-backed calendar provider."""

    def __init__(self, credentials_json: str | None = None) -> None:
        self._credentials = credentials_json or os.environ.get("GOOGLE_CALENDAR_CREDENTIALS_JSON", "")
        if not self._credentials:
            raise ProviderUnavailableError("Google Calendar credentials not configured")

    def check_availability(self, start: datetime, end: datetime) -> list[dict]:
        raise NotImplementedError("Google Calendar check_availability not yet implemented")

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        attendees: list[str] | None = None,
    ) -> dict:
        raise NotImplementedError("Google Calendar create_event not yet implemented")

    def list_events(self, start: datetime, end: datetime) -> list[dict]:
        raise NotImplementedError("Google Calendar list_events not yet implemented")
