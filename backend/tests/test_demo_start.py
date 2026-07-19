"""Tests for the one-click public demo entry endpoint (OP-006).

POST /demo/start must:
- be rejected unless PUBLIC_DEMO_ENABLED=true (including in production),
- idempotently seed the demo org and return a working short-lived token,
- preserve tenant isolation between the demo org and real orgs,
- stay on simulated (mock) Gmail/Calendar providers,
- be rate limited per client, and
- fail gracefully (401) for expired demo sessions.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from onepilot.core.config import Settings, get_settings


def _enable_public_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_DEMO_ENABLED", "true")
    get_settings.cache_clear()


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestDemoStartGating:
    def test_start_disabled_by_default(self, client: TestClient) -> None:
        """Without explicit public-demo mode, unauthenticated token minting is rejected."""
        resp = client.post("/demo/start")
        assert resp.status_code == 403

    def test_start_rejected_in_production_without_flag(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        get_settings.cache_clear()
        try:
            resp = client.post("/demo/start")
            assert resp.status_code == 403
        finally:
            monkeypatch.setenv("APP_ENV", "test")
            get_settings.cache_clear()


class TestDemoStartSuccess:
    def test_start_returns_working_token_and_seeded_workspace(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _enable_public_demo(monkeypatch)

        resp = client.post("/demo/start")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["access_token"]
        assert body["demo_mode"] is True
        assert body["simulated_providers"] is True
        assert body["expires_at"]

        token = body["access_token"]

        me = client.get("/me", headers=_h(token))
        assert me.status_code == 200, me.text
        assert me.json()["organization"]["id"] == "org_demo_onepilot"

        docs = client.get("/documents", headers=_h(token))
        assert docs.status_code == 200
        assert docs.json()["total"] == 19

        leads = client.get("/leads", headers=_h(token))
        assert leads.status_code == 200
        assert leads.json()["total"] > 0

    def test_start_is_idempotent(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _enable_public_demo(monkeypatch)

        first = client.post("/demo/start")
        second = client.post("/demo/start")
        assert first.status_code == 200
        assert second.status_code == 200

        token = second.json()["access_token"]
        docs = client.get("/documents", headers=_h(token))
        assert docs.json()["total"] == 19  # no duplicates

    def test_demo_session_expiry_is_short_lived(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PUBLIC_DEMO_SESSION_MINUTES", "5")
        _enable_public_demo(monkeypatch)

        from datetime import UTC, datetime

        resp = client.post("/demo/start")
        assert resp.status_code == 200
        expires_at = datetime.fromisoformat(resp.json()["expires_at"])
        remaining = expires_at - datetime.now(UTC)
        assert remaining <= timedelta(minutes=6)


class TestDemoStartTenantIsolation:
    def test_demo_token_cannot_see_other_org_data(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _enable_public_demo(monkeypatch)

        # Real, self-registered org with no seeded data.
        reg = client.post(
            "/auth/register",
            json={
                "email": "isolated@example.com",
                "password": "strongpass123",
                "full_name": "Isolated User",
                "organization_name": "IsolatedOrg",
            },
        )
        assert reg.status_code == 200
        other_token = reg.json()["access_token"]

        demo_token = client.post("/demo/start").json()["access_token"]

        # Demo org sees its seeded docs; the real org must see none of them.
        demo_docs = client.get("/documents", headers=_h(demo_token)).json()
        other_docs = client.get("/documents", headers=_h(other_token)).json()
        assert demo_docs["total"] == 19
        assert other_docs["total"] == 0

        # And the real org's leads are invisible to the demo org and vice versa.
        other_leads = client.get("/leads", headers=_h(other_token)).json()
        assert other_leads["total"] == 0


class TestDemoStartSimulatedProviders:
    def test_demo_mode_uses_mock_email_and_calendar_providers(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """In public-demo mode without Google credentials, providers must be mocks."""
        _enable_public_demo(monkeypatch)
        client.post("/demo/start")

        from onepilot.providers import get_calendar_provider, get_email_provider
        from onepilot.providers.calendar.mock_calendar_provider import MockCalendarProvider
        from onepilot.providers.email.mock_email_provider import MockEmailProvider

        settings = get_settings()
        assert isinstance(get_email_provider(settings), MockEmailProvider)
        assert isinstance(get_calendar_provider(settings), MockCalendarProvider)
        assert settings.GMAIL_SEND_ENABLED is False

    def test_production_public_demo_requires_mock_providers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "https://demo.vercel.app")
        s = Settings(
            APP_ENV="production",
            DEV_AUTH_ENABLED=False,
            JWT_SECRET="a" * 40,
            PUBLIC_DEMO_ENABLED=True,
            GMAIL_PROVIDER_MODE="auto",
            GOOGLE_CALENDAR_PROVIDER_MODE="mock",
        )
        with pytest.raises(RuntimeError, match="GMAIL_PROVIDER_MODE=mock"):
            s.validate_startup_config()

    def test_production_public_demo_rejects_live_send(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "https://demo.vercel.app")
        s = Settings(
            APP_ENV="production",
            DEV_AUTH_ENABLED=False,
            JWT_SECRET="a" * 40,
            PUBLIC_DEMO_ENABLED=True,
            GMAIL_PROVIDER_MODE="mock",
            GOOGLE_CALENDAR_PROVIDER_MODE="mock",
            GMAIL_SEND_ENABLED=True,
        )
        with pytest.raises(RuntimeError, match="GMAIL_SEND_ENABLED=false"):
            s.validate_startup_config()

    def test_production_public_demo_valid_mock_config_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "https://demo.vercel.app")
        s = Settings(
            APP_ENV="production",
            DEV_AUTH_ENABLED=False,
            JWT_SECRET="a" * 40,
            PUBLIC_DEMO_ENABLED=True,
            GMAIL_PROVIDER_MODE="mock",
            GOOGLE_CALENDAR_PROVIDER_MODE="mock",
            GMAIL_SEND_ENABLED=False,
        )
        assert s.validate_startup_config() == []


class TestDemoStartAbuseProtection:
    def test_start_is_rate_limited_per_client(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from onepilot.security import rate_limit as rl

        _enable_public_demo(monkeypatch)
        monkeypatch.setitem(rl._FEATURE_LIMITS, rl.FEATURE_DEMO_START, (2, 3600))

        assert client.post("/demo/start").status_code == 200
        assert client.post("/demo/start").status_code == 200
        limited = client.post("/demo/start")
        assert limited.status_code == 429
        assert limited.json()["error"] == "RATE_LIMIT_EXCEEDED"


class TestDemoSessionFailureStates:
    def test_expired_demo_session_is_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _enable_public_demo(monkeypatch)
        client.post("/demo/start")  # ensure demo user exists

        from onepilot.security.auth import create_access_token

        expired_token, _ = create_access_token(
            user_id="usr_demo_admin",
            organization_id="org_demo_onepilot",
            role="owner",
            plan_code="business",
            expires_delta=timedelta(minutes=-5),
        )
        resp = client.get("/me", headers=_h(expired_token))
        assert resp.status_code == 401

    def test_garbage_token_is_rejected(self, client: TestClient) -> None:
        resp = client.get("/me", headers=_h("not-a-real-token"))
        assert resp.status_code == 401
