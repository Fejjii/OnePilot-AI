from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from onepilot.providers.calendar.base import CalendarProvider
from onepilot.providers.calendar.slot_utils import (
    build_available_slots,
    pick_suggested_slots,
)
from onepilot.schemas.calendar import (
    CalendarAvailabilityResult,
    CalendarCreateEventResult,
    CalendarEvent,
    CalendarProviderStatus,
    CalendarSlotSuggestionResult,
)


class MockCalendarProvider(CalendarProvider):
    """Deterministic in-memory calendar provider for tests and demos."""

    def __init__(self, *, calendar_id: str = "primary") -> None:
        self._events: dict[str, dict] = {}
        self._calendar_id = calendar_id

    def get_status(self) -> CalendarProviderStatus:
        return CalendarProviderStatus(
            configured=False,
            mode="mock",
            active=True,
            fallback_used=True,
            calendar_id=self._calendar_id,
            create_enabled=True,
            status_reason=None,
            scope_check_ok=None,
            capabilities={
                "availability_check": True,
                "suggest_slots": True,
                "create_event": True,
                "requires_approval_for_create": True,
            },
        )

    def _seed_busy_block(self, time_min: datetime, time_max: datetime) -> None:
        """Insert a deterministic busy block on the second weekday afternoon."""
        midpoint = time_min + (time_max - time_min) / 2
        busy_start = midpoint.replace(hour=14, minute=0, second=0, microsecond=0)
        busy_end = busy_start + timedelta(hours=1)
        event_id = "evt_mock_busy_01"
        if event_id not in self._events:
            self._events[event_id] = {
                "id": event_id,
                "summary": "Mock internal sync",
                "start": busy_start,
                "end": busy_end,
                "attendees": [],
            }

    def _busy_events(self, time_min: datetime, time_max: datetime) -> list[CalendarEvent]:
        self._seed_busy_block(time_min, time_max)
        events: list[CalendarEvent] = []
        for raw in self._events.values():
            start = raw["start"]
            end = raw["end"]
            if start < time_max and end > time_min:
                events.append(
                    CalendarEvent(
                        id=str(raw["id"]),
                        summary=str(raw["summary"]),
                        start_time=start,
                        end_time=end,
                        attendees=list(raw.get("attendees") or []),
                    )
                )
        return events

    def list_events(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        calendar_id: str | None = None,
    ) -> list[dict]:
        return [
            {
                "id": event.id,
                "summary": event.summary,
                "start": event.start_time.isoformat(),
                "end": event.end_time.isoformat(),
                "attendees": event.attendees,
            }
            for event in self._busy_events(time_min, time_max)
        ]

    def get_availability(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        timezone: str,
        workday_start: str,
        workday_end: str,
        slot_duration_minutes: int,
        calendar_id: str | None = None,
        query_type: str = "range",
    ) -> dict:
        busy = self._busy_events(time_min, time_max)
        slots = build_available_slots(
            time_min,
            time_max,
            timezone=timezone,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_duration_minutes=slot_duration_minutes,
            busy_events=busy,
        )
        result = CalendarAvailabilityResult(
            mode="mock",
            timezone=timezone,
            busy_events=busy,
            available_slots=slots,
            fallback_used=True,
        )
        payload = result.model_dump(mode="json")
        payload["query_type"] = query_type
        return payload

    def suggest_slots(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        timezone: str,
        duration_minutes: int,
        max_slots: int,
        workday_start: str,
        workday_end: str,
        calendar_id: str | None = None,
    ) -> dict:
        busy = self._busy_events(time_min, time_max)
        available = build_available_slots(
            time_min,
            time_max,
            timezone=timezone,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_duration_minutes=duration_minutes,
            busy_events=busy,
        )
        suggested = pick_suggested_slots(available, max_slots=max_slots)
        result = CalendarSlotSuggestionResult(
            mode="mock",
            timezone=timezone,
            suggested_slots=suggested,
            fallback_used=True,
        )
        return result.model_dump(mode="json")

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        *,
        timezone: str,
        attendees: list[str] | None = None,
        description: str | None = None,
        location: str | None = None,
        calendar_id: str | None = None,
    ) -> dict:
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        event = {
            "id": event_id,
            "summary": summary,
            "start": start_time,
            "end": end_time,
            "attendees": attendees or [],
            "description": description,
            "location": location,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._events[event_id] = event
        result = CalendarCreateEventResult(
            mode="mock",
            status="success",
            event_id=event_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            attendee_count=len(attendees or []),
            fallback_used=True,
        )
        return {**event, **result.model_dump(mode="json")}
