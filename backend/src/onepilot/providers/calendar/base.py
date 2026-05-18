from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class CalendarProvider(ABC):
    @abstractmethod
    def check_availability(self, start: datetime, end: datetime) -> list[dict]: ...

    @abstractmethod
    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        attendees: list[str] | None = None,
    ) -> dict: ...

    @abstractmethod
    def list_events(self, start: datetime, end: datetime) -> list[dict]: ...
