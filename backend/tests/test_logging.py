from __future__ import annotations

from onepilot.core.logging import bind_request_id, redact_sensitive, request_id_ctx


class TestRedactSensitiveProcessor:
    def test_redact_sensitive_keys(self) -> None:
        event = {
            "event": "login",
            "password": "s3cret",
            "api_key": "sk-abc",
            "authorization": "Bearer tok",
        }
        result = redact_sensitive(None, "info", event)
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["authorization"] == "[REDACTED]"

    def test_preserves_non_sensitive(self) -> None:
        event = {"event": "signup", "username": "alice", "count": 42}
        result = redact_sensitive(None, "info", event)
        assert result["username"] == "alice"
        assert result["count"] == 42
        assert result["event"] == "signup"


class TestBindRequestId:
    def test_request_id_binding(self) -> None:
        token = request_id_ctx.set("req-abc-123")
        try:
            event: dict = {"event": "test"}
            result = bind_request_id(None, "info", event)
            assert result["request_id"] == "req-abc-123"
        finally:
            request_id_ctx.reset(token)

    def test_no_request_id_when_empty(self) -> None:
        token = request_id_ctx.set("")
        try:
            event: dict = {"event": "test"}
            result = bind_request_id(None, "info", event)
            assert "request_id" not in result
        finally:
            request_id_ctx.reset(token)
