"""Private live-Google track: fail-closed config, org isolation, HITL, diagnostics."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from onepilot.core.config import (
    Settings,
    calendar_runtime_status,
    get_settings,
    gmail_runtime_status,
)
from onepilot.core.constants import ApprovalStatus, PlanCode, Role
from onepilot.core.errors import ProviderUnavailableError
from onepilot.core.ids import new_id
from onepilot.providers import (
    get_calendar_provider,
    get_email_provider,
    reset_provider_cache,
    resolve_calendar_provider_for_org,
    resolve_email_provider_for_org,
)
from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider
from onepilot.providers.calendar.mock_calendar_provider import MockCalendarProvider
from onepilot.providers.email.gmail_provider import GmailProvider
from onepilot.providers.email.mock_email_provider import MockEmailProvider
from onepilot.repositories.models import Organization, Subscription
from onepilot.security.auth import Principal
from onepilot.services import approval_service, calendar_service, gmail_service


_OAUTH = {
    "GOOGLE_CLIENT_ID": "private-client-id",
    "GOOGLE_CLIENT_SECRET": "private-client-secret",
    "GOOGLE_REFRESH_TOKEN": "private-refresh-token",
}


@pytest.fixture(autouse=True)
def _reset_providers() -> None:
    reset_provider_cache()
    get_settings.cache_clear()
    yield
    reset_provider_cache()
    get_settings.cache_clear()


def _private_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        **_OAUTH,
        "PRIVATE_LIVE_GOOGLE_ENABLED": True,
        "PRIVATE_LIVE_GOOGLE_ORG_ID": "org_private_demo",
        "PUBLIC_DEMO_ENABLED": False,
        "DEV_AUTH_ENABLED": False,
        "GMAIL_PROVIDER_MODE": "live",
        "GOOGLE_CALENDAR_PROVIDER_MODE": "live",
        "GMAIL_SEND_ENABLED": False,
        "GOOGLE_CALENDAR_CREATE_ENABLED": True,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def _principal(session, org_id: str | None = None) -> Principal:
    resolved_org = org_id or new_id("org")
    if session.get(Organization, resolved_org) is None:
        session.add(
            Organization(
                id=resolved_org,
                name=f"Org {resolved_org[-6:]}",
                slug=f"org-{resolved_org[-8:]}",
            )
        )
        session.add(
            Subscription(
                id=new_id("sub"),
                organization_id=resolved_org,
                plan_code=PlanCode.FREE,
                status="active",
            )
        )
        session.flush()
    return Principal(
        user_id=new_id("usr"),
        organization_id=resolved_org,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestPublicDemoRemainsMock:
    def test_public_demo_factory_stays_mock_even_with_oauth(self) -> None:
        settings = Settings(
            PUBLIC_DEMO_ENABLED=True,
            PRIVATE_LIVE_GOOGLE_ENABLED=False,
            GMAIL_PROVIDER_MODE="auto",
            GOOGLE_CALENDAR_PROVIDER_MODE="auto",
            **_OAUTH,
        )
        assert isinstance(get_email_provider(settings), MockEmailProvider)
        assert isinstance(get_calendar_provider(settings), MockCalendarProvider)
        assert gmail_runtime_status(settings)["gmail_mode"] == "mock"
        assert calendar_runtime_status(settings)["calendar_mode"] == "mock"
        assert settings.GMAIL_SEND_ENABLED is False

    def test_public_demo_start_still_issues_simulated_session(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PUBLIC_DEMO_ENABLED", "true")
        get_settings.cache_clear()
        resp = client.post("/demo/start")
        assert resp.status_code == 200
        body = resp.json()
        assert body["demo_mode"] is True
        assert body["simulated_providers"] is True

        health = client.get("/health").json()
        assert health["providers"]["gmail_mode"] == "mock"
        assert health["providers"]["calendar_mode"] == "mock"
        assert health["providers"]["gmail_send_enabled"] is False
        assert health["providers"]["public_demo_enabled"] is True
        assert health["providers"]["private_live_google_enabled"] is False
        assert health["providers"]["demo_track"] == "public"

    def test_public_and_private_tracks_cannot_combine(self) -> None:
        settings = _private_settings(PUBLIC_DEMO_ENABLED=True)
        with pytest.raises(RuntimeError, match="cannot both be true"):
            settings.validate_startup_config()

    def test_production_public_demo_still_requires_mock(self) -> None:
        settings = Settings(
            APP_ENV="production",
            DEV_AUTH_ENABLED=False,
            JWT_SECRET="a" * 40,
            CORS_ORIGINS="https://demo.vercel.app",
            PUBLIC_DEMO_ENABLED=True,
            GMAIL_PROVIDER_MODE="live",
            GOOGLE_CALENDAR_PROVIDER_MODE="mock",
            **_OAUTH,
        )
        with pytest.raises(RuntimeError, match="GMAIL_PROVIDER_MODE=mock"):
            settings.validate_startup_config()


class TestPrivateLiveModeSelection:
    def test_private_live_selects_google_providers(self) -> None:
        settings = _private_settings()
        settings.validate_startup_config()
        assert isinstance(get_email_provider(settings), GmailProvider)
        assert isinstance(get_calendar_provider(settings), GoogleCalendarProvider)
        assert gmail_runtime_status(settings)["gmail_mode"] == "live"
        assert settings.has_calendar_oauth is True
        assert settings.demo_track == "private_live_google"

    def test_auto_with_oauth_still_selects_live(self) -> None:
        settings = _private_settings(
            GMAIL_PROVIDER_MODE="auto",
            GOOGLE_CALENDAR_PROVIDER_MODE="auto",
        )
        settings.validate_startup_config()
        assert isinstance(get_email_provider(settings), GmailProvider)
        assert isinstance(get_calendar_provider(settings), GoogleCalendarProvider)

    def test_mock_mode_still_works_without_private_flag(self) -> None:
        settings = Settings(
            GMAIL_PROVIDER_MODE="mock",
            GOOGLE_CALENDAR_PROVIDER_MODE="mock",
            **_OAUTH,
        )
        assert isinstance(get_email_provider(settings), MockEmailProvider)
        assert isinstance(get_calendar_provider(settings), MockCalendarProvider)
        assert gmail_runtime_status(settings)["gmail_mode"] == "mock"
        assert calendar_runtime_status(settings)["calendar_mode"] == "mock"


class TestFailClosedMissingCredentials:
    def test_explicit_live_gmail_without_oauth_fails_startup(self) -> None:
        settings = Settings(
            GMAIL_PROVIDER_MODE="live",
            GOOGLE_CLIENT_ID="",
            GOOGLE_CLIENT_SECRET="",
            GOOGLE_REFRESH_TOKEN="",
        )
        with pytest.raises(RuntimeError, match="GMAIL_PROVIDER_MODE=live"):
            settings.validate_startup_config()

    def test_explicit_live_calendar_without_oauth_fails_startup(self) -> None:
        settings = Settings(
            GOOGLE_CALENDAR_PROVIDER_MODE="live",
            GOOGLE_CLIENT_ID="",
            GOOGLE_CLIENT_SECRET="",
            GOOGLE_REFRESH_TOKEN="",
        )
        with pytest.raises(RuntimeError, match="GOOGLE_CALENDAR_PROVIDER_MODE=live"):
            settings.validate_startup_config()

    def test_private_track_without_oauth_fails_startup(self) -> None:
        settings = Settings(
            PRIVATE_LIVE_GOOGLE_ENABLED=True,
            PRIVATE_LIVE_GOOGLE_ORG_ID="org_private_demo",
            GMAIL_PROVIDER_MODE="live",
            GOOGLE_CALENDAR_PROVIDER_MODE="live",
            DEV_AUTH_ENABLED=False,
        )
        with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
            settings.validate_startup_config()

    def test_private_track_without_org_id_fails_startup(self) -> None:
        settings = _private_settings(PRIVATE_LIVE_GOOGLE_ORG_ID="")
        with pytest.raises(RuntimeError, match="PRIVATE_LIVE_GOOGLE_ORG_ID"):
            settings.validate_startup_config()

    def test_private_track_rejects_dev_auth(self) -> None:
        settings = _private_settings(DEV_AUTH_ENABLED=True)
        with pytest.raises(RuntimeError, match="DEV_AUTH_ENABLED"):
            settings.validate_startup_config()

    def test_live_mode_factory_raises_without_credentials(self) -> None:
        settings = Settings(GMAIL_PROVIDER_MODE="live")
        with pytest.raises(ProviderUnavailableError, match="GMAIL_PROVIDER_MODE=live"):
            get_email_provider(settings)

        cal = Settings(GOOGLE_CALENDAR_PROVIDER_MODE="live")
        with pytest.raises(ProviderUnavailableError, match="GOOGLE_CALENDAR_PROVIDER_MODE=live"):
            get_calendar_provider(cal)

    def test_auto_without_credentials_still_mocks(self) -> None:
        settings = Settings(
            GMAIL_PROVIDER_MODE="auto",
            GOOGLE_CALENDAR_PROVIDER_MODE="auto",
        )
        assert isinstance(get_email_provider(settings), MockEmailProvider)
        assert isinstance(get_calendar_provider(settings), MockCalendarProvider)


class TestApprovalGates:
    def test_gmail_send_and_draft_remain_approval_gated(self, db_session) -> None:
        settings = _private_settings()
        principal = _principal(db_session, "org_private_demo")
        apv = approval_service.create(
            db_session,
            principal=principal,
            action_type="gmail_create_draft",
            title="Private draft",
            proposed_payload={
                "to": ["lead@example.com"],
                "subject": "Hello",
                "body": "Body text",
            },
        )
        assert apv.status == ApprovalStatus.PENDING.value
        assert approval_service.requires_approval("gmail_create_draft")
        assert approval_service.requires_approval("gmail_send_email")

        executed = {"called": False}

        def _fake_execute(*_args: object, **_kwargs: object) -> dict:
            executed["called"] = True
            return {"status": "success", "action": "create_draft", "mode": "live"}

        original = gmail_service.execute_approval_action
        gmail_service.execute_approval_action = _fake_execute  # type: ignore[assignment]
        try:
            approval_service.decide(
                db_session,
                principal=principal,
                approval_id=apv.id,
                status=ApprovalStatus.REJECTED,
            )
            assert executed["called"] is False
            assert "_execution" not in (apv.proposed_payload or {})
        finally:
            gmail_service.execute_approval_action = original  # type: ignore[assignment]

        assert settings.GMAIL_SEND_ENABLED is False

    def test_calendar_write_remains_approval_gated(self, db_session) -> None:
        principal = _principal(db_session, "org_private_demo")
        start = datetime(2026, 9, 8, 10, 0)
        apv = approval_service.create(
            db_session,
            principal=principal,
            action_type="calendar_create_event",
            title="Private meeting",
            proposed_payload=calendar_service.build_approval_payload(
                summary="Demo",
                start_time=start,
                end_time=start + timedelta(minutes=30),
                timezone="Europe/Berlin",
            ),
        )
        assert apv.status == ApprovalStatus.PENDING.value
        assert approval_service.requires_approval("calendar_create_event")
        assert approval_service.requires_approval("google_calendar_create_event")

        executed = {"called": False}

        def _fake_execute(*_args: object, **_kwargs: object) -> dict:
            executed["called"] = True
            return {"status": "success", "action": "create_event", "mode": "live"}

        original = calendar_service.execute_approval_action
        calendar_service.execute_approval_action = _fake_execute  # type: ignore[assignment]
        try:
            approval_service.decide(
                db_session,
                principal=principal,
                approval_id=apv.id,
                status=ApprovalStatus.REJECTED,
            )
            assert executed["called"] is False
        finally:
            calendar_service.execute_approval_action = original  # type: ignore[assignment]


class TestTenantAndAuthIsolation:
    def test_other_org_cannot_use_live_google_providers(self) -> None:
        settings = _private_settings()
        allowed = resolve_email_provider_for_org(settings, "org_private_demo")
        denied = resolve_email_provider_for_org(settings, "org_other_tenant")
        assert isinstance(allowed, GmailProvider)
        assert isinstance(denied, MockEmailProvider)

        allowed_cal = resolve_calendar_provider_for_org(settings, "org_private_demo")
        denied_cal = resolve_calendar_provider_for_org(settings, "org_other_tenant")
        assert isinstance(allowed_cal, GoogleCalendarProvider)
        assert isinstance(denied_cal, MockCalendarProvider)

    def test_other_org_calendar_reads_stay_on_mock(self, db_session) -> None:
        settings = _private_settings()
        other = _principal(db_session, "org_other_tenant")
        result = calendar_service.list_events(
            db_session,
            principal=other,
            message="Show my upcoming meetings",
            settings=settings,
        )
        assert result["mode"] == "mock"
        assert result["fallback_used"] is True

    def test_other_org_cannot_see_private_org_approvals(
        self, client: TestClient, db_session
    ) -> None:
        private = _principal(db_session, "org_private_demo")
        approval_service.create(
            db_session,
            principal=private,
            action_type="gmail_create_draft",
            title="Secret live draft",
            proposed_payload={
                "to": ["lead@example.com"],
                "subject": "Hello",
                "body": "Body",
            },
        )
        db_session.commit()

        other_reg = client.post(
            "/auth/register",
            json={
                "email": "other-tenant@example.com",
                "password": "strongpass123",
                "full_name": "Other User",
                "organization_name": "OtherTenant",
            },
        )
        assert other_reg.status_code == 200
        other_token = other_reg.json()["access_token"]
        listed = client.get("/approvals", headers=_h(other_token))
        assert listed.status_code == 200
        titles = [item["title"] for item in listed.json()["items"]]
        assert "Secret live draft" not in titles

    def test_unauthenticated_chat_and_approvals_are_rejected(
        self, client: TestClient
    ) -> None:
        assert client.get("/approvals").status_code == 401
        assert client.post("/chat", json={"message": "Check my calendar"}).status_code == 401

    def test_private_host_rejects_anonymous_demo_start(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PRIVATE_LIVE_GOOGLE_ENABLED", "true")
        monkeypatch.setenv("PUBLIC_DEMO_ENABLED", "true")
        get_settings.cache_clear()
        resp = client.post("/demo/start")
        assert resp.status_code == 403


class TestDiagnostics:
    def test_health_reports_live_and_mock_tracks(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        health = client.get("/health").json()
        providers = health["providers"]
        assert providers["gmail_mode"] == "mock"
        assert providers["calendar_mode"] in {"mock", "missing"}
        assert providers["demo_track"] == "standard"
        assert providers["private_live_google_enabled"] is False
        assert "refresh_token" not in str(health).lower()
        assert "client_secret" not in str(health).lower()

        diag = client.get("/providers").json()
        by_name = {item["name"]: item for item in diag["providers"]}
        assert by_name["Gmail"]["mode"] == "mock"
        assert by_name["Gmail"]["details"]["requires_approval"] is True
        assert by_name["Google Calendar"]["details"]["requires_approval_for_create"] is True
        assert by_name["Gmail"]["details"]["demo_track"] == "standard"
        blob = str(diag).lower()
        assert "refresh_token" not in blob
        assert "ya29." not in blob

    def test_runtime_status_labels_private_live(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = _private_settings()
        gmail = gmail_runtime_status(settings)
        assert gmail["gmail_mode"] == "live"
        assert gmail["gmail_active"] is True
        assert gmail["gmail_fallback_used"] is False
        assert settings.demo_track == "private_live_google"

        from onepilot.schemas.calendar import CalendarProviderStatus

        live_status = CalendarProviderStatus(
            configured=True,
            mode="live",
            active=True,
            fallback_used=False,
            calendar_id="primary",
            create_enabled=True,
        )
        monkeypatch.setattr(
            GoogleCalendarProvider,
            "get_status",
            lambda self: live_status,
        )
        reset_provider_cache()
        calendar = calendar_runtime_status(settings)
        assert calendar["calendar_mode"] == "live"
        assert calendar["calendar_active"] is True
        assert calendar["calendar_fallback_used"] is False

    def test_public_demo_diagnostics_name_simulated_gmail(self) -> None:
        settings = Settings(
            PUBLIC_DEMO_ENABLED=True,
            GMAIL_PROVIDER_MODE="mock",
            GOOGLE_CALENDAR_PROVIDER_MODE="mock",
        )
        gmail = gmail_runtime_status(settings)
        calendar = calendar_runtime_status(settings)
        assert gmail["gmail_mode"] == "mock"
        assert gmail["gmail_active"] is False
        assert calendar["calendar_mode"] == "mock"
        assert calendar["calendar_active"] is False
        assert settings.demo_track == "public"

    def test_is_live_gmail_is_org_scoped(self) -> None:
        settings = _private_settings()
        assert gmail_service.is_live_gmail_provider(
            settings, organization_id="org_private_demo"
        )
        assert not gmail_service.is_live_gmail_provider(
            settings, organization_id="org_other_tenant"
        )
