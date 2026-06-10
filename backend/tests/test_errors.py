from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from onepilot.core.errors import (
    AuthenticationError,
    ConflictError,
    GuardrailBlockedError,
    NotFoundError,
    OnePilotError,
    PermissionDeniedError,
    ProviderUnavailableError,
    QuotaExceededError,
    RateLimitExceededError,
    ValidationError,
)


class TestErrorHandlers:
    def test_onepilot_error_returns_json(self, app: FastAPI, client: TestClient) -> None:
        @app.get("/test-not-found")
        def _raise_not_found() -> None:
            raise NotFoundError("item gone")

        resp = client.get("/test-not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "NOT_FOUND"
        assert body["message"] == "item gone"

    def test_unhandled_error_hidden(self, app: FastAPI) -> None:
        @app.get("/test-runtime-error")
        def _raise_runtime() -> None:
            raise RuntimeError("unexpected internal detail")

        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/test-runtime-error")
        assert resp.status_code == 500
        body = resp.json()
        assert "unexpected internal detail" not in body["message"]
        assert body["error"] == "INTERNAL_ERROR"


_ERROR_CLASSES: list[tuple[type[OnePilotError], int]] = [
    (OnePilotError, 500),
    (NotFoundError, 404),
    (PermissionDeniedError, 403),
    (AuthenticationError, 401),
    (QuotaExceededError, 429),
    (RateLimitExceededError, 429),
    (ValidationError, 422),
    (ProviderUnavailableError, 503),
    (GuardrailBlockedError, 400),
    (ConflictError, 409),
]


class TestErrorHierarchy:
    @pytest.mark.parametrize("cls,expected_code", _ERROR_CLASSES)
    def test_inherits_from_onepilot_error(
        self, cls: type[OnePilotError], expected_code: int
    ) -> None:
        err = cls()
        assert isinstance(err, OnePilotError)
        assert err.status_code == expected_code
