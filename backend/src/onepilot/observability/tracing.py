from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TracingProvider(ABC):
    @abstractmethod
    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any: ...

    @abstractmethod
    def end_span(self, span: Any, status: str = "ok") -> None: ...


class NoOpTracingProvider(TracingProvider):
    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        return None

    def end_span(self, span: Any, status: str = "ok") -> None:
        pass


_provider: TracingProvider = NoOpTracingProvider()


def get_tracing_provider() -> TracingProvider:
    return _provider


def set_tracing_provider(provider: TracingProvider) -> None:
    global _provider
    _provider = provider
