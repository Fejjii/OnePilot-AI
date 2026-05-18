from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|secret|token|authorization|api_key|api-key|apikey)",
    re.IGNORECASE,
)

_REDACTION_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        "Bearer [REDACTED]",
    ),
    (
        re.compile(r"\b(sk-[A-Za-z0-9]{20,})\b"),
        "[API_KEY_REDACTED]",
    ),
    (
        re.compile(r"\b(pk_[A-Za-z0-9]{20,})\b"),
        "[API_KEY_REDACTED]",
    ),
    (
        re.compile(r"\b[A-Fa-f0-9]{32,}\b"),
        "[KEY_REDACTED]",
    ),
    (
        re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        ),
        "[EMAIL_REDACTED]",
    ),
    (
        re.compile(
            r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b",
        ),
        "[PHONE_REDACTED]",
    ),
    (
        re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
        "[CC_REDACTED]",
    ),
]


def redact_sensitive(text: str) -> str:
    """Replace sensitive patterns in text with redaction markers."""
    for pattern, replacement in _REDACTION_RULES:
        text = pattern.sub(replacement, text)
    return text


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Deep-redact sensitive values in a dictionary."""
    return {key: _redact_value(key, value) for key, value in data.items()}


def _redact_value(key: str, value: Any) -> Any:
    if isinstance(value, dict):
        return redact_dict(value)
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    if _SENSITIVE_KEY_PATTERN.search(key):
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_sensitive(value)
    return value
