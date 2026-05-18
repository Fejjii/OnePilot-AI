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
