import re
from contextvars import ContextVar
from typing import Any

import structlog

from onepilot.core.config import get_settings

_SENSITIVE_PATTERN = re.compile(
    r"(password|secret|token|authorization|api_key|api-key|apikey)",
    re.IGNORECASE,
)

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def redact_sensitive(
    logger: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    for key, value in event_dict.items():
        if isinstance(value, str) and _SENSITIVE_PATTERN.search(key):
            event_dict[key] = "[REDACTED]"
    return event_dict


def bind_request_id(
    logger: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    rid = request_id_ctx.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def _configure_structlog() -> None:
    settings = get_settings()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        bind_request_id,
        redact_sensitive,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_dev:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_structlog()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
