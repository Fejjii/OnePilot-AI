"""Tests for observability tracing abstraction."""

from __future__ import annotations

import pytest

from onepilot.observability.tracing import (
    LocalTracingProvider,
    LangSmithTracingProvider,
    initialize_tracing,
    get_tracing_provider,
    set_tracing_provider,
    sanitize_metadata,
)


def test_local_tracing_provider():
    """Test local tracing provider creates traces and spans."""
    provider = LocalTracingProvider()

    # Start trace
    ctx = provider.start_trace("test_trace", {"user_id": "test_user"})
    assert ctx.trace_id.startswith("local_")
    assert ctx.mode == "local"
    assert ctx.trace_url is None
    assert ctx.metadata["user_id"] == "test_user"

    # Start and end span
    span = provider.start_span(ctx, "test_span", {"detail": "test detail"})
    assert span["name"] == "test_span"
    assert "start_time" in span

    provider.end_span(ctx, span, status="ok")
    assert len(ctx.spans) == 1
    assert ctx.spans[0]["step"] == "test_span"
    assert ctx.spans[0]["status"] == "ok"
    assert ctx.spans[0]["duration_ms"] >= 0

    # Record event
    provider.record_event(ctx, "test_event", {"data": "value"})
    assert len(ctx.spans) == 2
    assert ctx.spans[1]["step"] == "test_event"

    # Record error
    error = ValueError("test error")
    provider.record_error(ctx, error)
    assert len(ctx.spans) == 3
    assert ctx.spans[2]["step"] == "error"
    assert "ValueError" in ctx.spans[2]["detail"]

    # Finalize
    provider.finalize_trace(ctx)


def test_langsmith_tracing_provider_without_langsmith():
    """Test LangSmith provider falls back gracefully when langsmith not installed."""
    provider = LangSmithTracingProvider(
        api_key="test_key",
        project="test_project",
    )

    # Should fall back to local tracing if langsmith package not available
    ctx = provider.start_trace("test_trace")
    # Either succeeds with langsmith or falls back to local
    assert ctx.trace_id
    assert ctx.mode in ("langsmith", "local")


def test_initialize_tracing_local_mode():
    """Test tracing initialization defaults to local mode."""
    initialize_tracing(langsmith_enabled=False)

    provider = get_tracing_provider()
    assert isinstance(provider, LocalTracingProvider)


def test_initialize_tracing_langsmith_without_key():
    """Test tracing initialization falls back without API key."""
    initialize_tracing(langsmith_enabled=True, langsmith_api_key=None)

    provider = get_tracing_provider()
    # Should fall back to local since no key provided
    assert isinstance(provider, LocalTracingProvider)


def test_initialize_tracing_langsmith_with_key():
    """Test tracing initialization attempts LangSmith with key."""
    initialize_tracing(
        langsmith_enabled=True,
        langsmith_api_key="test_key_12345",
        langsmith_project="test_project",
    )

    provider = get_tracing_provider()
    # Either LangSmith if package available, or Local fallback
    assert provider is not None


def test_sanitize_metadata_removes_sensitive_keys():
    """Test metadata sanitization removes sensitive keys."""
    metadata = {
        "user_id": "user123",
        "api_key": "secret123",
        "API_KEY": "secret456",
        "password": "pass123",
        "token": "token123",
        "authorization": "Bearer xyz",
        "safe_field": "visible",
    }

    sanitized = sanitize_metadata(metadata)

    assert sanitized["user_id"] == "user123"
    assert sanitized["safe_field"] == "visible"
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["API_KEY"] == "***REDACTED***"
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["token"] == "***REDACTED***"
    assert sanitized["authorization"] == "***REDACTED***"


def test_sanitize_metadata_nested_dict():
    """Test metadata sanitization handles nested dictionaries."""
    metadata = {
        "config": {
            "api_key": "secret",
            "endpoint": "https://api.example.com",
        },
        "user": {
            "name": "Alice",
            "password": "pass123",
        },
    }

    sanitized = sanitize_metadata(metadata)

    assert sanitized["config"]["api_key"] == "***REDACTED***"
    assert sanitized["config"]["endpoint"] == "https://api.example.com"
    assert sanitized["user"]["name"] == "Alice"
    assert sanitized["user"]["password"] == "***REDACTED***"


def test_trace_context_accumulates_spans():
    """Test that trace context correctly accumulates spans."""
    provider = LocalTracingProvider()
    ctx = provider.start_trace("multi_span_trace")

    # Add multiple spans
    for i in range(3):
        span = provider.start_span(ctx, f"span_{i}")
        provider.end_span(ctx, span)

    assert len(ctx.spans) == 3
    for i, span_data in enumerate(ctx.spans):
        assert span_data["step"] == f"span_{i}"


def test_set_and_get_tracing_provider():
    """Test global tracing provider getter and setter."""
    custom_provider = LocalTracingProvider()
    set_tracing_provider(custom_provider)

    retrieved = get_tracing_provider()
    assert retrieved is custom_provider
