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
        assert "unhealthy" in text.lower()
        assert "diagnostics" in text.lower()


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
