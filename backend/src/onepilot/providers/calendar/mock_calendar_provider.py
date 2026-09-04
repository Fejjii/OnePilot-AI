from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

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

# Weekday-relative demo meetings (Monday=0). Times are local wall-clock.
_DEMO_MEETING_TEMPLATES: tuple[tuple[int, int, int, int, str, tuple[str, ...], str | None], ...] = (
    (0, 10, 0, 30, "Discovery call with Sarah Chen", ("Sarah Chen",), "Brightline Analytics"),
    (1, 14, 0, 45, "Proposal review with Marcus Webb", ("Marcus Webb",), "Northwind Legal"),
    (2, 11, 0, 30, "Product demo with Elena Rossi", ("Elena Rossi",), "Helio Commerce"),
    (3, 9, 30, 30, "Internal pipeline review", ("NovaEdge sales",), None),
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
                "list_events": True,
                "suggest_slots": True,
                "create_event": True,
                "requires_approval_for_create": True,
            },
        )

    def _seed_demo_meetings(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        timezone: str = "Europe/Berlin",
    ) -> None:
        """Insert a realistic, deterministic week of recruiter-facing meetings."""
        tz = ZoneInfo(timezone)
        start_aware = time_min.replace(tzinfo=UTC) if time_min.tzinfo is None else time_min
        end_aware = time_max.replace(tzinfo=UTC) if time_max.tzinfo is None else time_max
        start_local = start_aware.astimezone(tz)
        end_local = end_aware.astimezone(tz)
        week_monday = start_local.date() - timedelta(days=start_local.weekday())
        last_date = end_local.date()
        cursor = week_monday
        while cursor <= last_date:
            for weekday, hour, minute, duration, summary, attendees, company in (
                _DEMO_MEETING_TEMPLATES
            ):
                day = cursor + timedelta(days=weekday)
                event_id = f"evt_demo_{day.isoformat()}_{hour:02d}{minute:02d}"
                start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
                end = start + timedelta(minutes=duration)
                start_utc = start.astimezone(UTC).replace(tzinfo=None)
                end_utc = end.astimezone(UTC).replace(tzinfo=None)
                if start_utc < time_max and end_utc > time_min and event_id not in self._events:
                    self._events[event_id] = {
                        "id": event_id,
                        "summary": summary,
                        "start": start_utc,
                        "end": end_utc,
                        "attendees": list(attendees),
                        "company": company,
                    }
            cursor += timedelta(days=7)

    def _busy_events(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        timezone: str = "Europe/Berlin",
    ) -> list[CalendarEvent]:
        self._seed_demo_meetings(time_min, time_max, timezone=timezone)
        events: list[CalendarEvent] = []
        for raw in self._events.values():
            start = raw["start"]
            end = raw["end"]
            if start < time_max and end > time_min:
                company = raw.get("company")
                events.append(
                    CalendarEvent(
                        id=str(raw["id"]),
                        summary=str(raw["summary"]),
                        start_time=start,
                        end_time=end,
                        attendees=list(raw.get("attendees") or []),
                        company=str(company) if company else None,
                    )
                )
        events.sort(key=lambda event: event.start_time)
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
                "company": event.company,
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
        busy = self._busy_events(time_min, time_max, timezone=timezone)
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
        busy = self._busy_events(time_min, time_max, timezone=timezone)
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
