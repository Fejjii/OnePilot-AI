from __future__ import annotations

import pytest

from onepilot.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


class TestSettings:
    def test_default_settings(self) -> None:
        s = Settings()
        assert s.APP_NAME == "OnePilot AI"
        assert s.APP_VERSION == "0.1.0"
        assert s.APP_ENV == "test"
        assert s.JWT_ALGORITHM == "HS256"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-key-for-test")
        s = Settings()
        assert s.has_openai is True

    def test_is_dev_false_in_test(self) -> None:
        s = Settings()
        assert s.is_dev is False
        assert s.is_test is True

    def test_has_redis_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDIS_URL", "")
        s = Settings()
        assert s.has_redis is False

    def test_dev_auth_defaults_false_without_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEV_AUTH_ENABLED", raising=False)
        s = Settings(APP_ENV="dev")
        assert s.DEV_AUTH_ENABLED is False

    def test_production_rejects_dev_auth_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", "a" * 40)
        monkeypatch.setenv("CORS_ORIGINS", "https://demo.vercel.app")
        s = Settings(APP_ENV="production", DEV_AUTH_ENABLED=True)
        with pytest.raises(RuntimeError, match="DEV_AUTH_ENABLED"):
            s.validate_startup_config()

    def test_production_rejects_weak_jwt_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "https://demo.vercel.app")
        s = Settings(APP_ENV="production", DEV_AUTH_ENABLED=False, JWT_SECRET="change-me-in-production")
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            s.validate_startup_config()

    def test_production_rejects_short_jwt_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "https://demo.vercel.app")
        s = Settings(APP_ENV="production", DEV_AUTH_ENABLED=False, JWT_SECRET="short-secret")
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            s.validate_startup_config()

    def test_production_requires_cors_origins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = Settings(
            APP_ENV="production",
            DEV_AUTH_ENABLED=False,
            JWT_SECRET="a" * 40,
            CORS_ORIGINS="",
        )
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            s.validate_startup_config()

    def test_production_accepts_safe_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = Settings(
            APP_ENV="production",
            DEV_AUTH_ENABLED=False,
            JWT_SECRET="a" * 40,
            CORS_ORIGINS="https://demo.vercel.app",
        )
        assert s.validate_startup_config() == []


class TestCorsOrigins:
    def test_dev_includes_localhost(self) -> None:
        s = Settings(APP_ENV="dev")
        origins = s.cors_origins_list()
        assert "http://localhost:3000" in origins
        assert "http://127.0.0.1:3000" in origins

    def test_dev_merges_configured_origins(self) -> None:
        s = Settings(APP_ENV="dev", CORS_ORIGINS="https://preview.vercel.app")
        origins = s.cors_origins_list()
        assert "https://preview.vercel.app" in origins
        assert "http://localhost:3000" in origins

    def test_production_uses_only_configured_origins(self) -> None:
        s = Settings(
            APP_ENV="production",
            CORS_ORIGINS="https://demo.vercel.app,https://www.example.com",
        )
        origins = s.cors_origins_list()
        assert origins == ["https://demo.vercel.app", "https://www.example.com"]
        assert "http://localhost:3000" not in origins

    def test_production_rejects_wildcard(self) -> None:
        s = Settings(APP_ENV="production", CORS_ORIGINS="*")
        with pytest.raises(ValueError, match="Wildcard"):
            s.cors_origins_list()
