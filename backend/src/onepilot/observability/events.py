from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event_type: str, payload: dict[str, Any]) -> None: ...


class NoOpEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self._events.append({"type": event_type, "payload": payload})


_publisher: EventPublisher = NoOpEventPublisher()


def get_event_publisher() -> EventPublisher:
    return _publisher


def set_event_publisher(publisher: EventPublisher) -> None:
    global _publisher
    _publisher = publisher
