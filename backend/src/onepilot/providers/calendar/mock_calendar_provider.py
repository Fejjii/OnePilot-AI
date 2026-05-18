from __future__ import annotations

import uuid
from datetime import UTC, datetime

from onepilot.providers.calendar.base import CalendarProvider


class MockCalendarProvider(CalendarProvider):
    """In-memory calendar provider for tests and demos."""

    def __init__(self) -> None:
        self._events: dict[str, dict] = {}

    def check_availability(self, start: datetime, end: datetime) -> list[dict]:
        conflicts: list[dict] = []
        for event in self._events.values():
            if event["start"] < end and event["end"] > start:
                conflicts.append(event)
        return conflicts

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        attendees: list[str] | None = None,
    ) -> dict:
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        event = {
            "id": event_id,
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "attendees": attendees or [],
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._events[event_id] = {
            **event,
            "start": start,
            "end": end,
        }
        return event

    def list_events(self, start: datetime, end: datetime) -> list[dict]:
        results: list[dict] = []
        for event in self._events.values():
            if event["start"] < end and event["end"] > start:
                results.append({
                    "id": event["id"],
                    "title": event["title"],
                    "start": event["start"].isoformat() if isinstance(event["start"], datetime) else event["start"],
                    "end": event["end"].isoformat() if isinstance(event["end"], datetime) else event["end"],
                    "attendees": event.get("attendees", []),
                })
        return results
