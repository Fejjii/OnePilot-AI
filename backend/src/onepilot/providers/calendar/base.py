from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from onepilot.schemas.calendar import CalendarProviderStatus


class CalendarProvider(ABC):
    @abstractmethod
    def get_status(self) -> CalendarProviderStatus: ...

    @abstractmethod
    def list_events(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        calendar_id: str | None = None,
    ) -> list[dict]: ...

    @abstractmethod
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
    ) -> dict: ...

    @abstractmethod
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
    ) -> dict: ...

    @abstractmethod
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
    ) -> dict: ...
