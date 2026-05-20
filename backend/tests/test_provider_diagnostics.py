"""Tests for provider diagnostics endpoint."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from onepilot.api.routers import health as health_router
from onepilot.core.config import Settings
from onepilot.providers import reset_provider_cache
from onepilot.schemas.calendar import CalendarProviderStatus
from onepilot.schemas.runtime import ProviderMode


def test_provider_diagnostics_no_keys(client: TestClient) -> None:
    """Test provider diagnostics with no API keys configured (default test environment)."""
    response = client.get("/providers")
    assert response.status_code == 200

    data = response.json()
    assert "providers" in data
    assert "checked_at" in data
    assert len(data["providers"]) == 14  # includes speech + multilingual application capability
    
    provider_map = {p["name"]: p for p in data["providers"]}

    assert provider_map["Multilingual Support"]["category"] == "application"
    assert provider_map["Multilingual Support"]["active"] is True

    # In test mode (conftest.py sets OPENAI_API_KEY=""), these should be missing
    assert provider_map["OpenAI LLM"]["mode"] == "missing"
    assert provider_map["OpenAI LLM"]["configured"] is False
    assert provider_map["OpenAI LLM"]["active"] is False
    assert provider_map["OpenAI LLM"]["fallback_used"] is True

    assert provider_map["OpenAI Embeddings"]["mode"] == "missing"
    assert provider_map["OpenAI Embeddings"]["configured"] is False

    assert provider_map["OpenAI Speech"]["mode"] == "missing"
    assert provider_map["OpenAI Speech"]["configured"] is False

    assert provider_map["Qdrant"]["mode"] == "missing"
    assert provider_map["Qdrant"]["configured"] is False

    assert provider_map["Redis"]["mode"] == "missing"
    assert provider_map["Redis"]["configured"] is False

    # LangSmith without API key
    assert provider_map["LangSmith"]["mode"] == "missing"
    assert provider_map["LangSmith"]["configured"] is False

    # Serper is optional when not configured
    assert provider_map["Serper Web Search"]["mode"] == "optional"
    assert provider_map["Serper Web Search"]["configured"] is False
    
    assert provider_map["Gmail"]["mode"] == "mock"
    assert provider_map["Gmail"]["configured"] is False
    assert provider_map["Gmail"]["details"]["gmail_send_enabled"] is False
    assert provider_map["Gmail"]["details"]["capability_send_email"] is False
    
    assert provider_map["HubSpot"]["mode"] == "mock"
    assert provider_map["HubSpot"]["configured"] is False
    
    assert provider_map["Google Calendar"]["mode"] in {"mock", "missing"}
    assert provider_map["Google Calendar"]["configured"] is False
    
    assert provider_map["Twilio"]["mode"] == "mock"
    assert provider_map["Twilio"]["configured"] is False
    
    assert provider_map["Stripe"]["mode"] == "mock"
    assert provider_map["Stripe"]["configured"] is False


def test_provider_diagnostics_saas_providers_mock(client: TestClient) -> None:
    """Test that SaaS providers are in mock mode without credentials."""
    response = client.get("/providers")
    assert response.status_code == 200
    
    data = response.json()
    provider_map = {p["name"]: p for p in data["providers"]}
    
    for provider_name in ["Gmail", "HubSpot", "Stripe", "Twilio"]:
        assert provider_map[provider_name]["mode"] == "mock"
        assert provider_map[provider_name]["active"] is False
        assert provider_map[provider_name]["details"]["mock"] is True

    calendar = provider_map["Google Calendar"]
    assert calendar["mode"] in {"mock", "missing"}
    assert calendar["active"] is False

    assert provider_map["Serper Web Search"]["mode"] == "optional"


def test_provider_diagnostics_postgres_healthy(client: TestClient) -> None:
    """Test that Postgres is reported as healthy."""
    response = client.get("/providers")
    assert response.status_code == 200
    
    data = response.json()
    provider_map = {p["name"]: p for p in data["providers"]}
    
    assert provider_map["Postgres"]["configured"] is True
    assert provider_map["Postgres"]["healthy"] is True
    assert provider_map["Postgres"]["active"] is True
    assert provider_map["Postgres"]["mode"] == "live"


def test_provider_diagnostics_categories(client: TestClient) -> None:
    """Test that providers have correct categories."""
    response = client.get("/providers")
    assert response.status_code == 200
    
    data = response.json()
    provider_map = {p["name"]: p for p in data["providers"]}
    
    assert provider_map["OpenAI LLM"]["category"] == "llm"
    assert provider_map["OpenAI Embeddings"]["category"] == "embeddings"
    assert provider_map["Qdrant"]["category"] == "vector"
    assert provider_map["Redis"]["category"] == "cache"
    assert provider_map["Postgres"]["category"] == "database"
    assert provider_map["LangSmith"]["category"] == "observability"
    assert provider_map["Serper Web Search"]["category"] == "search"
    assert provider_map["Gmail"]["category"] == "email"
    assert provider_map["HubSpot"]["category"] == "crm"
    assert provider_map["Google Calendar"]["category"] == "calendar"
    assert provider_map["Twilio"]["category"] == "sms"
    assert provider_map["Stripe"]["category"] == "billing"


def test_provider_diagnostics_response_structure(client: TestClient) -> None:
    """Test that provider diagnostics response has the correct structure."""
    response = client.get("/providers")
    assert response.status_code == 200
    
    data = response.json()
    assert "providers" in data
    assert "checked_at" in data
    assert isinstance(data["providers"], list)
    
    for provider in data["providers"]:
        assert "name" in provider
        assert "category" in provider
        assert "configured" in provider
        assert "healthy" in provider
        assert "active" in provider
        assert "fallback_used" in provider
        assert "mode" in provider
        assert "last_checked_at" in provider
        assert provider["mode"] in [
            "live",
            "fallback",
            "mock",
            "local",
            "missing",
            "optional",
            "unhealthy",
        ]


def test_provider_diagnostics_reasons_for_fallback(client: TestClient) -> None:
    """Test that fallback providers include a reason."""
    response = client.get("/providers")
    assert response.status_code == 200
    
    data = response.json()
    provider_map = {p["name"]: p for p in data["providers"]}
    
    # Missing / fallback providers should have a reason
    for provider_name in ["OpenAI LLM", "OpenAI Embeddings", "Qdrant", "Redis"]:
        assert provider_map[provider_name]["reason"] is not None
        assert len(provider_map[provider_name]["reason"]) > 0

    # Mock / optional providers should have a reason
    for provider_name in ["Gmail", "HubSpot", "Google Calendar", "Stripe", "Serper Web Search"]:
        assert provider_map[provider_name]["reason"] is not None
        reason = provider_map[provider_name]["reason"].lower()
        assert (
            "mock" in reason
            or "optional" in reason
            or "not set" in reason
            or "capstone" in reason
            or "missing" in reason
            or "provider issue" in reason
        )


@pytest.fixture(autouse=True)
def _reset_provider_cache() -> None:
    reset_provider_cache()
    yield
    reset_provider_cache()


def test_provider_diagnostics_json_serializable(client: TestClient) -> None:
    response = client.get("/providers")
    assert response.status_code == 200
    json.dumps(response.json())


def test_provider_diagnostics_no_secrets_in_response(client: TestClient) -> None:
    response = client.get("/providers")
    assert response.status_code == 200
    for provider in response.json()["providers"]:
        details_blob = json.dumps(provider.get("details") or {}).lower()
        for secret_marker in (
            "refresh_token",
            "client_secret",
            "credentials.json",
            "-----begin",
            "ya29.",
        ):
            assert secret_marker not in details_blob
        assert "@" not in details_blob or "configured" in details_blob


def test_calendar_live_null_status_reason_returns_200(client: TestClient) -> None:
    live_status = CalendarProviderStatus(
        configured=True,
        mode="live",
        active=True,
        fallback_used=False,
        calendar_id="primary",
        create_enabled=True,
        status_reason=None,
        scope_check_ok=True,
    )
    with patch(
        "onepilot.core.config.calendar_runtime_status",
        return_value={
            "calendar_configured": True,
            "calendar_mode": "live",
            "calendar_active": True,
            "calendar_fallback_used": False,
            "calendar_create_enabled": True,
            "calendar_status_reason": None,
        },
    ):
        with patch(
            "onepilot.api.routers.health.get_calendar_provider",
            return_value=MagicMock(get_status=MagicMock(return_value=live_status)),
        ):
            response = client.get("/providers")

    assert response.status_code == 200
    calendar = next(p for p in response.json()["providers"] if p["name"] == "Google Calendar")
    assert calendar["mode"] == "live"
    assert "calendar_status_reason" not in (calendar.get("details") or {})


def test_calendar_unhealthy_returns_200(client: TestClient) -> None:
    unhealthy_status = CalendarProviderStatus(
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
    ):
        with patch(
            "onepilot.api.routers.health.get_calendar_provider",
            return_value=MagicMock(get_status=MagicMock(return_value=unhealthy_status)),
        ):
            response = client.get("/providers")

    assert response.status_code == 200
    calendar = next(p for p in response.json()["providers"] if p["name"] == "Google Calendar")
    assert calendar["mode"] == "unhealthy"
    assert calendar["details"]["calendar_status_reason"] == "missing_calendar_scope"


def test_calendar_get_status_failure_returns_200(client: TestClient) -> None:
    with patch(
        "onepilot.core.config.calendar_runtime_status",
        return_value={
            "calendar_configured": True,
            "calendar_mode": "live",
            "calendar_active": True,
            "calendar_fallback_used": False,
            "calendar_create_enabled": True,
            "calendar_status_reason": None,
        },
    ):
        with patch(
            "onepilot.api.routers.health.get_calendar_provider",
            side_effect=RuntimeError("probe failed"),
        ):
            response = client.get("/providers")

    assert response.status_code == 200
    calendar = next(p for p in response.json()["providers"] if p["name"] == "Google Calendar")
    assert calendar["mode"] == "unhealthy"
    assert calendar["details"]["calendar_status_reason"] == "unknown"


def test_sanitize_provider_details_drops_nulls() -> None:
    assert health_router._sanitize_provider_details(
        {"ok": True, "skip": None, "count": 2, "label": "live"}
    ) == {"ok": True, "count": 2, "label": "live"}


def test_build_calendar_diagnostic_never_raises() -> None:
    from datetime import datetime, timezone

    settings = Settings()
    with patch(
        "onepilot.api.routers.health.get_calendar_provider",
        side_effect=ValueError("boom"),
    ):
        diag = health_router._build_calendar_diagnostic(
            settings=settings,
            checked_at=datetime.now(timezone.utc),
        )
    assert diag.name == "Google Calendar"
    assert diag.mode in {ProviderMode.MOCK, ProviderMode.MISSING, ProviderMode.UNHEALTHY}
