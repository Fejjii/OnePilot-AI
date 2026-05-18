from __future__ import annotations

import json

from onepilot.providers.llm.base import LLMProvider, LLMResponse


class FallbackLLMProvider(LLMProvider):
    """Deterministic in-memory LLM provider for tests and demos."""

    def __init__(self) -> None:
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self._call_count += 1
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break

        content = (
            f"I'm a demo assistant running in fallback mode. "
            f"You said: {last_user_msg!r}"
        )
        return LLMResponse(
            content=content,
            model=model or "fallback-v1",
            input_tokens=len(last_user_msg.split()),
            output_tokens=len(content.split()),
            finish_reason="stop",
        )

    def chat_structured(
        self,
        messages: list[dict],
        response_schema: dict,
        model: str | None = None,
    ) -> LLMResponse:
        self._call_count += 1
        payload = _build_default_payload(response_schema)
        content = json.dumps(payload)
        return LLMResponse(
            content=content,
            model=model or "fallback-v1",
            input_tokens=10,
            output_tokens=len(content.split()),
            finish_reason="stop",
        )


def _build_default_payload(schema: dict) -> dict | list | str:
    """Build a minimal JSON value that satisfies a JSON-Schema-like dict."""
    schema_type = schema.get("type", "object")
    if schema_type == "object":
        result: dict = {}
        for key, prop in schema.get("properties", {}).items():
            result[key] = _build_default_payload(prop)
        return result
    if schema_type == "array":
        return []
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0.0
    if schema_type == "boolean":
        return False
    return ""
