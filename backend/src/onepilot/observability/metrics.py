from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MetricsProvider(ABC):
    @abstractmethod
    def increment(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None: ...

    @abstractmethod
    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None: ...

    @abstractmethod
    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None: ...


class NoOpMetricsProvider(MetricsProvider):
    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def increment(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        self._records.append({"type": "counter", "name": name, "value": value, "tags": tags})

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self._records.append({"type": "gauge", "name": name, "value": value, "tags": tags})

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self._records.append({"type": "histogram", "name": name, "value": value, "tags": tags})


_provider: MetricsProvider = NoOpMetricsProvider()


def get_metrics_provider() -> MetricsProvider:
    return _provider


def set_metrics_provider(provider: MetricsProvider) -> None:
    global _provider
    _provider = provider
