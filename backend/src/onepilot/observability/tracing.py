"""Unified tracing abstraction supporting both local and LangSmith modes.

When LangSmith is configured (LANGSMITH_TRACING=true and LANGSMITH_API_KEY set):
- Traces are sent to LangSmith live
- Returns trace URLs for deep links

When LangSmith is not configured:
- Uses local trace mode
- Accumulates trace steps in memory
- No external dependencies
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from onepilot.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TraceContext:
    """Encapsulates trace metadata for a single request."""

    trace_id: str
    mode: str  # "local" or "langsmith"
    trace_url: str | None = None
    spans: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class TracingProvider(ABC):
    """Abstract interface for tracing providers."""

    @abstractmethod
    def start_trace(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> TraceContext: ...

    @abstractmethod
    def start_span(
        self, context: TraceContext, name: str, attributes: dict[str, Any] | None = None
    ) -> Any: ...

    @abstractmethod
    def end_span(
        self, context: TraceContext, span: Any, status: str = "ok", metadata: dict[str, Any] | None = None
    ) -> None: ...

    @abstractmethod
    def record_event(
        self, context: TraceContext, event: str, data: dict[str, Any] | None = None
    ) -> None: ...

    @abstractmethod
    def record_error(
        self, context: TraceContext, error: Exception, span: Any = None
    ) -> None: ...

    @abstractmethod
    def finalize_trace(self, context: TraceContext) -> None: ...


class LocalTracingProvider(TracingProvider):
    """Local in-memory tracing for development and fallback mode."""

    def start_trace(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> TraceContext:
        trace_id = f"local_{int(time.time() * 1000)}"
        ctx = TraceContext(
            trace_id=trace_id,
            mode="local",
            trace_url=None,
            metadata=metadata or {},
        )
        logger.debug(f"Started local trace: {name} ({trace_id})")
        return ctx

    def start_span(
        self, context: TraceContext, name: str, attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        span = {
            "name": name,
            "start_time": time.time(),
            "attributes": attributes or {},
        }
        return span

    def end_span(
        self, context: TraceContext, span: Any, status: str = "ok", metadata: dict[str, Any] | None = None
    ) -> None:
        if not isinstance(span, dict):
            return
        duration_ms = int((time.time() - span["start_time"]) * 1000)
        context.spans.append(
            {
                "step": span["name"],
                "detail": span["attributes"].get("detail", ""),
                "duration_ms": duration_ms,
                "status": status,
                **(metadata or {}),
            }
        )

    def record_event(
        self, context: TraceContext, event: str, data: dict[str, Any] | None = None
    ) -> None:
        context.spans.append(
            {
                "step": event,
                "detail": str(data or ""),
                "duration_ms": 0,
            }
        )

    def record_error(
        self, context: TraceContext, error: Exception, span: Any = None
    ) -> None:
        context.spans.append(
            {
                "step": "error",
                "detail": f"{error.__class__.__name__}: {str(error)}",
                "duration_ms": 0,
            }
        )

    def finalize_trace(self, context: TraceContext) -> None:
        logger.debug(f"Finalized local trace {context.trace_id} with {len(context.spans)} spans")


class LangSmithTracingProvider(TracingProvider):
    """LangSmith live tracing provider."""

    def __init__(self, api_key: str, project: str, endpoint: str | None = None):
        self.api_key = api_key
        self.project = project
        self.endpoint = endpoint or "https://api.smith.langchain.com"
        self._client: Any = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of LangSmith client."""
        if self._initialized:
            return

        try:
            from langsmith import Client

            # Set environment variables for LangSmith SDK
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.api_key
            os.environ["LANGCHAIN_PROJECT"] = self.project
            if self.endpoint:
                os.environ["LANGCHAIN_ENDPOINT"] = self.endpoint

            self._client = Client(api_key=self.api_key, api_url=self.endpoint)
            self._initialized = True
            logger.info(f"LangSmith tracing initialized: project={self.project}")
        except ImportError:
            logger.warning("langsmith package not installed, falling back to local tracing")
            raise
        except Exception as exc:
            logger.error(f"Failed to initialize LangSmith client: {exc}")
            raise

    def start_trace(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> TraceContext:
        try:
            self._ensure_initialized()
            from langsmith import traceable

            # Create a run ID for this trace
            import uuid
            run_id = str(uuid.uuid4())

            # Build trace URL
            trace_url = f"{self.endpoint}/o/default/projects/p/{self.project}/r/{run_id}"

            ctx = TraceContext(
                trace_id=run_id,
                mode="langsmith",
                trace_url=trace_url,
                metadata={"run_id": run_id, **(metadata or {})},
            )
            logger.debug(f"Started LangSmith trace: {name} ({run_id})")
            return ctx
        except Exception as exc:
            logger.warning(f"LangSmith trace failed, using local: {exc}")
            # Fallback to local
            return LocalTracingProvider().start_trace(name, metadata)

    def start_span(
        self, context: TraceContext, name: str, attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        # For LangSmith, we'll use the @traceable decorator in actual workflow
        # Here we just track for local fallback
        return {
            "name": name,
            "start_time": time.time(),
            "attributes": attributes or {},
        }

    def end_span(
        self, context: TraceContext, span: Any, status: str = "ok", metadata: dict[str, Any] | None = None
    ) -> None:
        if not isinstance(span, dict):
            return
        duration_ms = int((time.time() - span["start_time"]) * 1000)
        context.spans.append(
            {
                "step": span["name"],
                "detail": span["attributes"].get("detail", ""),
                "duration_ms": duration_ms,
                "status": status,
                **(metadata or {}),
            }
        )

    def record_event(
        self, context: TraceContext, event: str, data: dict[str, Any] | None = None
    ) -> None:
        context.spans.append(
            {
                "step": event,
                "detail": str(data or ""),
                "duration_ms": 0,
            }
        )

    def record_error(
        self, context: TraceContext, error: Exception, span: Any = None
    ) -> None:
        context.spans.append(
            {
                "step": "error",
                "detail": f"{error.__class__.__name__}: {str(error)}",
                "duration_ms": 0,
            }
        )
        logger.error(f"Trace error recorded: {error}", exc_info=error)

    def finalize_trace(self, context: TraceContext) -> None:
        logger.debug(f"Finalized LangSmith trace {context.trace_id}")


# Global provider singleton
_provider: TracingProvider | None = None


def get_tracing_provider() -> TracingProvider:
    """Get the configured tracing provider."""
    global _provider
    if _provider is None:
        _provider = LocalTracingProvider()
    return _provider


def set_tracing_provider(provider: TracingProvider) -> None:
    """Set the global tracing provider."""
    global _provider
    _provider = provider


def initialize_tracing(
    langsmith_enabled: bool = False,
    langsmith_api_key: str | None = None,
    langsmith_project: str = "onepilot-ai",
    langsmith_endpoint: str | None = None,
) -> None:
    """Initialize tracing based on configuration."""
    if langsmith_enabled and langsmith_api_key:
        try:
            provider = LangSmithTracingProvider(
                api_key=langsmith_api_key,
                project=langsmith_project,
                endpoint=langsmith_endpoint,
            )
            set_tracing_provider(provider)
            logger.info(f"Tracing initialized: LangSmith live mode (project={langsmith_project})")
        except Exception as exc:
            logger.warning(f"Failed to initialize LangSmith, using local tracing: {exc}")
            set_tracing_provider(LocalTracingProvider())
    else:
        set_tracing_provider(LocalTracingProvider())
        logger.info("Tracing initialized: local mode")


@contextmanager
def trace_span(
    context: TraceContext, name: str, attributes: dict[str, Any] | None = None
) -> Iterator[None]:
    """Context manager for tracing a span."""
    provider = get_tracing_provider()
    span = provider.start_span(context, name, attributes)
    try:
        yield
    except Exception as exc:
        provider.record_error(context, exc, span)
        raise
    finally:
        provider.end_span(context, span)


def sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive data from metadata before tracing."""
    sensitive_keys = {
        "api_key",
        "apikey",
        "api-key",
        "password",
        "secret",
        "token",
        "auth",
        "authorization",
        "credentials",
        "credential",
    }

    sanitized = {}
    for key, value in metadata.items():
        key_lower = key.lower().replace("_", "").replace("-", "")
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_metadata(value)
        else:
            sanitized[key] = value

    return sanitized
