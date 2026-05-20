"""Tests for Serper environment loading and safe diagnostics."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from onepilot.core.config import Settings, get_settings, resolve_env_files, serper_runtime_status
from onepilot.providers.search.serper_provider import SerperSearchProvider


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_resolve_env_files_skips_dotenv_in_test_mode() -> None:
    assert resolve_env_files() == tuple()


def test_resolve_env_files_loads_when_not_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    files = resolve_env_files()
    assert isinstance(files, tuple)
    assert len(files) >= 1
    for path in files:
        assert path.endswith(".env")


def test_settings_detects_serper_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERPER_API_KEY", "test-serper-key-not-real")
    settings = Settings()
    assert settings.has_serper is True
    assert settings.SERPER_API_KEY == "test-serper-key-not-real"


def test_serper_key_never_in_health_or_providers(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "super-secret-serper-key-xyz"
    monkeypatch.setenv("SERPER_API_KEY", secret)
    get_settings.cache_clear()

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["providers"]["serper_configured"] is True
    assert body["providers"]["serper_mode"] == "live"
    assert secret not in health.text

    providers = client.get("/providers")
    assert providers.status_code == 200
    assert secret not in providers.text
    serper = next(p for p in providers.json()["providers"] if p["name"] == "Serper Web Search")
    assert serper["configured"] is True
    assert serper["mode"] == "live"


def test_serper_runtime_status_missing_without_key() -> None:
    settings = Settings(SERPER_API_KEY="")
    status = serper_runtime_status(settings)
    assert status["serper_configured"] is False
    assert status["serper_mode"] == "missing"


def test_get_search_provider_uses_serper_without_exposing_key() -> None:
    from onepilot.providers import get_search_provider

    settings = Settings(SERPER_API_KEY="hidden-key-value")
    provider = get_search_provider(settings)
    assert isinstance(provider, SerperSearchProvider)
    assert "hidden-key-value" not in repr(provider)
