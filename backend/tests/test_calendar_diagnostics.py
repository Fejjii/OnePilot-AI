"""Calendar provider diagnostics and unhealthy response semantics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from onepilot.core.config import Settings
from onepilot.providers import get_calendar_provider, reset_provider_cache
from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider
from onepilot.providers.calendar.scope_utils import missing_calendar_scopes
from onepilot.services.calendar_format import format_availability_response


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_provider_cache()
    yield
    reset_provider_cache()


class TestCalendarScopeDiagnostics:
    def test_missing_calendar_scope_detected(self) -> None:
        granted = {"https://www.googleapis.com/auth/gmail.compose"}
        missing = missing_calendar_scopes(granted)
        assert len(missing) == 2

    def test_unhealthy_does_not_say_no_open_slots(self) -> None:
        raw = {
            "mode": "unhealthy",
            "status": "error",
            "timezone": "Europe/Berlin",
            "error_code": "missing_calendar_scope",
        }
        text = format_availability_response(raw)
        assert "No open slots" not in text
        assert "couldn't check availability" in text.lower()
        assert "unhealthy" not in text.lower()
        assert "diagnostics" not in text.lower()


class TestGoogleCalendarProviderStatus:
    def test_403_maps_to_missing_scope_when_scopes_incomplete(self) -> None:
        settings = Settings(
            GOOGLE_CLIENT_ID="id",
            GOOGLE_CLIENT_SECRET="secret",
            GOOGLE_REFRESH_TOKEN="refresh",
            GOOGLE_CALENDAR_PROVIDER_MODE="auto",
        )
        provider = get_calendar_provider(settings)
        assert isinstance(provider, GoogleCalendarProvider)

        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {
            "scope": "https://www.googleapis.com/auth/gmail.compose",
        }

        mock_probe_resp = MagicMock()
        mock_probe_resp.status_code = 403

        with patch.object(provider._oauth, "get_access_token", return_value="access"):
            with patch("httpx.Client.get", side_effect=[mock_token_resp, mock_probe_resp]):
                status = provider.get_status()

        assert status.mode == "unhealthy"
        assert status.status_reason == "missing_calendar_scope"

    def test_invalid_refresh_token_reason(self) -> None:
        settings = Settings(
            GOOGLE_CLIENT_ID="id",
            GOOGLE_CLIENT_SECRET="secret",
            GOOGLE_REFRESH_TOKEN="refresh",
            GOOGLE_CALENDAR_PROVIDER_MODE="auto",
        )
        provider = get_calendar_provider(settings)
        assert isinstance(provider, GoogleCalendarProvider)

        with patch.object(
            provider._oauth,
            "get_access_token",
            side_effect=httpx.HTTPStatusError(
                "fail",
                request=MagicMock(),
                response=MagicMock(status_code=401),
            ),
        ):
            status = provider.get_status()

        assert status.mode == "unhealthy"
        assert status.status_reason == "token_refresh_failed"


class TestIntentionalCalendarMockDiagnostics:
    def test_forced_mock_omits_missing_oauth_reason(self) -> None:
        from onepilot.core.config import calendar_runtime_status

        settings = Settings(GOOGLE_CALENDAR_PROVIDER_MODE="mock")
        status = calendar_runtime_status(settings)
        assert status["calendar_mode"] == "mock"
        assert status["calendar_status_reason"] is None
        assert status["calendar_fallback_used"] is True

    def test_forced_mock_diagnostic_is_healthy_simulated(self) -> None:
        from datetime import datetime, timezone

        from onepilot.api.routers.health import _build_calendar_diagnostic

        settings = Settings(GOOGLE_CALENDAR_PROVIDER_MODE="mock")
        diag = _build_calendar_diagnostic(
            settings=settings,
            checked_at=datetime.now(timezone.utc),
        )
        assert diag.mode == "mock"
        assert diag.healthy is True
        assert diag.reason is not None
        assert "provider issue" not in diag.reason.lower()
        assert "missing_google" not in diag.reason.lower()
        assert "simulated" in diag.reason.lower()

    def test_public_demo_mock_copy_names_the_demo(self) -> None:
        from datetime import datetime, timezone

        from onepilot.api.routers.health import _build_calendar_diagnostic

        settings = Settings(
            GOOGLE_CALENDAR_PROVIDER_MODE="mock",
            PUBLIC_DEMO_ENABLED=True,
        )
        diag = _build_calendar_diagnostic(
            settings=settings,
            checked_at=datetime.now(timezone.utc),
        )
        assert diag.healthy is True
        assert diag.reason is not None
        assert "public demo" in diag.reason.lower()
        assert "provider issue" not in diag.reason.lower()

    def test_live_unhealthy_still_reports_provider_issue(self) -> None:
        from datetime import datetime, timezone

        from onepilot.api.routers.health import _build_calendar_diagnostic
        from onepilot.schemas.calendar import CalendarProviderStatus

        settings = Settings(
            GOOGLE_CLIENT_ID="id",
            GOOGLE_CLIENT_SECRET="secret",
            GOOGLE_REFRESH_TOKEN="refresh",
            GOOGLE_CALENDAR_PROVIDER_MODE="auto",
        )
        unhealthy = CalendarProviderStatus(
            configured=True,
            mode="unhealthy",
            active=False,
            fallback_used=False,
            calendar_id="primary",
            create_enabled=False,
            status_reason="missing_calendar_scope",
            scope_check_ok=False,
        )
        with patch(
            "onepilot.core.config.calendar_runtime_status",
            return_value={
                "calendar_configured": True,
                "calendar_mode": "unhealthy",
                "calendar_active": False,
                "calendar_fallback_used": False,
                "calendar_create_enabled": False,
                "calendar_status_reason": "missing_calendar_scope",
            },
        ), patch(
            "onepilot.api.routers.health.get_calendar_provider",
            return_value=MagicMock(get_status=MagicMock(return_value=unhealthy)),
        ):
            diag = _build_calendar_diagnostic(
                settings=settings,
                checked_at=datetime.now(timezone.utc),
            )
        assert diag.mode == "unhealthy"
        assert diag.healthy is False
        assert diag.reason is not None
        assert "provider issue" in diag.reason.lower()
        assert "missing_calendar_scope" in diag.reason
