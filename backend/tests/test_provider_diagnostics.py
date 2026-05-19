"""Tests for provider diagnostics endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


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

    # In test mode (conftest.py sets OPENAI_API_KEY=""), these should be fallback
    assert provider_map["OpenAI LLM"]["mode"] == "fallback"
    assert provider_map["OpenAI LLM"]["configured"] is False
    assert provider_map["OpenAI LLM"]["active"] is False
    assert provider_map["OpenAI LLM"]["fallback_used"] is True
    
    assert provider_map["OpenAI Embeddings"]["mode"] == "fallback"
    assert provider_map["OpenAI Embeddings"]["configured"] is False
    
    assert provider_map["Qdrant"]["mode"] == "fallback"
    assert provider_map["Qdrant"]["configured"] is False
    
    assert provider_map["Redis"]["mode"] == "fallback"
    assert provider_map["Redis"]["configured"] is False
    
    # LangSmith defaults to local when not configured
    assert provider_map["LangSmith"]["mode"] == "local"
    assert provider_map["LangSmith"]["configured"] is False
    
    # SaaS providers default to mock
    assert provider_map["Serper"]["mode"] == "mock"
    assert provider_map["Serper"]["configured"] is False
    
    assert provider_map["Gmail"]["mode"] == "mock"
    assert provider_map["Gmail"]["configured"] is False
    
    assert provider_map["HubSpot"]["mode"] == "mock"
    assert provider_map["HubSpot"]["configured"] is False
    
    assert provider_map["Google Calendar"]["mode"] == "mock"
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
    
    for provider_name in ["Gmail", "HubSpot", "Google Calendar", "Stripe", "Serper"]:
        assert provider_map[provider_name]["mode"] == "mock"
        assert provider_map[provider_name]["active"] is False
        assert provider_map[provider_name]["details"]["mock"] is True


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
    assert provider_map["Serper"]["category"] == "search"
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
        assert provider["mode"] in ["live", "fallback", "mock", "local", "missing", "unhealthy"]


def test_provider_diagnostics_reasons_for_fallback(client: TestClient) -> None:
    """Test that fallback providers include a reason."""
    response = client.get("/providers")
    assert response.status_code == 200
    
    data = response.json()
    provider_map = {p["name"]: p for p in data["providers"]}
    
    # Fallback providers should have a reason
    for provider_name in ["OpenAI LLM", "OpenAI Embeddings", "Qdrant", "Redis"]:
        assert provider_map[provider_name]["reason"] is not None
        assert len(provider_map[provider_name]["reason"]) > 0
    
    # Mock providers should have a reason
    for provider_name in ["Gmail", "HubSpot", "Google Calendar", "Stripe", "Serper"]:
        assert provider_map[provider_name]["reason"] is not None
        assert "mock" in provider_map[provider_name]["reason"].lower() or "not set" in provider_map[provider_name]["reason"].lower()
