from __future__ import annotations

import pytest

from onepilot.core.config import (
    DEFAULT_CORS_ALLOWED_ORIGINS,
    Settings,
    get_settings,
    parse_comma_separated_list,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


class TestParseCommaSeparatedList:
    def test_parses_comma_separated_origins(self) -> None:
        value = "http://localhost:3000, https://app.example.azurecontainerapps.io"
        assert parse_comma_separated_list(value) == [
            "http://localhost:3000",
            "https://app.example.azurecontainerapps.io",
        ]

    def test_drops_empty_segments(self) -> None:
        assert parse_comma_separated_list("a,,b, ,c") == ["a", "b", "c"]


class TestCorsSettings:
    def test_default_local_origins(self) -> None:
        s = Settings()
        assert s.CORS_ALLOWED_ORIGINS == DEFAULT_CORS_ALLOWED_ORIGINS
        assert s.cors_allowed_origins_list == [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    def test_custom_azure_frontend_origin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000,https://onepilot-frontend.azurecontainerapps.io",
        )
        s = Settings()
        assert "https://onepilot-frontend.azurecontainerapps.io" in s.cors_allowed_origins_list
        assert "http://localhost:3000" in s.cors_allowed_origins_list

    def test_empty_cors_origins_falls_back_to_local_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "  ,  , ")
        s = Settings()
        assert s.cors_allowed_origins_list == [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    def test_cors_methods_and_headers_defaults(self) -> None:
        s = Settings()
        assert s.cors_allow_methods_list == ["*"]
        assert s.cors_allow_headers_list == ["*"]
        assert s.CORS_ALLOW_CREDENTIALS is True
