"""Google Calendar provider, schemas, and approval-gated execution tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError as PydanticValidationError

from onepilot.core.config import Settings
from onepilot.core.constants import ApprovalStatus, PlanCode, Role
from onepilot.core.ids import new_id
from onepilot.providers import get_calendar_provider, reset_provider_cache
from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider
from onepilot.providers.calendar.mock_calendar_provider import MockCalendarProvider
from onepilot.providers.email.gmail_auth import GoogleOAuthClient
from onepilot.repositories.models import ApprovalRequest, Organization, Subscription
from onepilot.schemas.calendar import CalendarCreateEventRequest
from onepilot.security.auth import Principal
from onepilot.services import approval_service, calendar_service


@pytest.fixture(autouse=True)
def _reset_calendar_provider() -> None:
    reset_provider_cache()
    yield
    reset_provider_cache()


class TestCalendarSchemas:
    def test_invalid_attendee_rejected(self) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        with pytest.raises(PydanticValidationError):
            CalendarCreateEventRequest(
                summary="Meeting",
                start_time=now,
                end_time=now + timedelta(minutes=30),
                attendees=["not-an-email"],
            )

    def test_end_before_start_rejected(self) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        with pytest.raises(PydanticValidationError):
            CalendarCreateEventRequest(
                summary="Meeting",
                start_time=now + timedelta(hours=1),
                end_time=now,
            )

    def test_empty_summary_rejected(self) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        with pytest.raises(PydanticValidationError):
            CalendarCreateEventRequest(
                summary="",
                start_time=now,
                end_time=now + timedelta(minutes=30),
            )

    def test_invalid_duration_rejected(self) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        with pytest.raises(PydanticValidationError):
            CalendarCreateEventRequest(
                summary="Meeting",
                start_time=now,
                end_time=now + timedelta(minutes=5),
            )


class TestGoogleCalendarEventTimeParsing:
    def test_datetime_with_offset_converts_to_utc_naive(self) -> None:
        parsed = GoogleCalendarProvider._parse_event_time(
            {"dateTime": "2026-05-22T11:00:00+02:00"},
            default_timezone="Europe/Berlin",
        )
        assert parsed.hour == 9
        assert parsed.minute == 0
        assert parsed.tzinfo is None

    def test_datetime_without_offset_uses_timezone(self) -> None:
        parsed = GoogleCalendarProvider._parse_event_time(
            {"dateTime": "2026-05-22T11:00:00", "timeZone": "Europe/Berlin"},
            default_timezone="Europe/Berlin",
        )
        assert parsed.hour == 9


class TestCalendarProviderSelection:
    def test_missing_credentials_returns_mock(self) -> None:
        settings = Settings(
            GOOGLE_CLIENT_ID="",
            GOOGLE_CLIENT_SECRET="",
            GOOGLE_REFRESH_TOKEN="",
            GOOGLE_CALENDAR_PROVIDER_MODE="auto",
        )
        provider = get_calendar_provider(settings)
        assert isinstance(provider, MockCalendarProvider)

    def test_mock_mode_explicit(self) -> None:
        settings = Settings(
            GOOGLE_CLIENT_ID="id",
            GOOGLE_CLIENT_SECRET="secret",
            GOOGLE_REFRESH_TOKEN="refresh",
            GOOGLE_CALENDAR_PROVIDER_MODE="mock",
        )
        provider = get_calendar_provider(settings)
        assert isinstance(provider, MockCalendarProvider)

    def test_live_mode_when_oauth_configured(self) -> None:
        settings = Settings(
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            GOOGLE_REFRESH_TOKEN="refresh-token",
            GOOGLE_CALENDAR_PROVIDER_MODE="auto",
        )
        provider = get_calendar_provider(settings)
        assert isinstance(provider, GoogleCalendarProvider)

    def test_mock_availability_is_deterministic(self) -> None:
        provider = MockCalendarProvider()
        start = datetime(2026, 5, 25, 0, 0)
        end = datetime(2026, 5, 30, 0, 0)
        first = provider.get_availability(
            start,
            end,
            timezone="Europe/Berlin",
            workday_start="09:00",
            workday_end="17:00",
            slot_duration_minutes=30,
        )
        second = provider.get_availability(
            start,
            end,
            timezone="Europe/Berlin",
            workday_start="09:00",
            workday_end="17:00",
            slot_duration_minutes=30,
        )
        assert first["available_slots"] == second["available_slots"]
        assert "access_token" not in str(first)
        assert "refresh_token" not in str(first)

    def test_mock_create_event_returns_id(self) -> None:
        provider = MockCalendarProvider()
        start = datetime(2026, 5, 26, 10, 0)
        end = start + timedelta(minutes=30)
        result = provider.create_event(
            "Demo meeting",
            start,
            end,
            timezone="Europe/Berlin",
        )
        assert result["status"] == "success"
        assert result.get("event_id")


class TestCalendarOAuth:
    def test_token_refresh_never_exposes_refresh_token(self) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "ya29.access",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        with patch("httpx.Client.post", return_value=mock_response):
            client = GoogleOAuthClient(
                client_id="id",
                client_secret="secret",
                refresh_token="refresh-token-value",
            )
            token = client.get_access_token()
        assert token == "ya29.access"
        assert "refresh-token-value" not in token


class TestCalendarApprovalExecution:
    def test_rejected_approval_does_not_create_event(self, db_session) -> None:
        org = Organization(id=new_id("org"), name="Cal Org", slug="cal-org")
        db_session.add(org)
        db_session.add(
            Subscription(
                id=new_id("sub"),
                organization_id=org.id,
                plan_code=PlanCode.FREE.value,
                status="active",
            )
        )
        approval = ApprovalRequest(
            id=new_id("apv"),
            organization_id=org.id,
            action_type="calendar_create_event",
            title="Schedule meeting",
            description="",
            proposed_payload=calendar_service.build_approval_payload(
                summary="Demo",
                start_time=datetime(2026, 5, 26, 10, 0),
                end_time=datetime(2026, 5, 26, 10, 30),
                timezone="Europe/Berlin",
            ),
            risk_level="medium",
            status=ApprovalStatus.PENDING.value,
            created_by="usr_admin",
        )
        db_session.add(approval)
        db_session.flush()

        principal = Principal(
            user_id="usr_admin",
            organization_id=org.id,
            role=Role.ADMIN,
            plan_code=PlanCode.FREE,
        )
        approval_service.decide(
            db_session,
            principal=principal,
            approval_id=approval.id,
            status=ApprovalStatus.REJECTED,
        )
        assert approval.proposed_payload.get("_execution") is None

    def test_approved_calendar_action_executes(self, db_session) -> None:
        org = Organization(id=new_id("org"), name="Cal Org 2", slug="cal-org-2")
        db_session.add(org)
        db_session.add(
            Subscription(
                id=new_id("sub"),
                organization_id=org.id,
                plan_code=PlanCode.FREE.value,
                status="active",
            )
        )
        payload = calendar_service.build_approval_payload(
            summary="Approved meeting",
            start_time=datetime(2026, 5, 27, 11, 0),
            end_time=datetime(2026, 5, 27, 11, 30),
            timezone="Europe/Berlin",
        )
        approval = ApprovalRequest(
            id=new_id("apv"),
            organization_id=org.id,
            action_type="calendar_create_event",
            title="Schedule meeting",
            description="",
            proposed_payload=payload,
            risk_level="medium",
            status=ApprovalStatus.PENDING.value,
            created_by="usr_admin",
        )
        db_session.add(approval)
        db_session.flush()

        principal = Principal(
            user_id="usr_admin",
            organization_id=org.id,
            role=Role.ADMIN,
            plan_code=PlanCode.FREE,
        )
        updated = approval_service.decide(
            db_session,
            principal=principal,
            approval_id=approval.id,
            status=ApprovalStatus.APPROVED,
        )
        execution = updated.proposed_payload.get("_execution") or {}
        assert execution.get("status") == "success"
        assert execution.get("event_id")
        assert "refresh_token" not in str(execution)
