import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/onepilot/core/config.py -> repo root is four parents up
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_PROJECT_ROOT = _BACKEND_ROOT.parent

# Default CORS origins for local frontend (Docker Compose and pnpm dev).
DEFAULT_CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def parse_comma_separated_list(value: str) -> list[str]:
    """Parse a comma-separated env string into a trimmed list (empty entries dropped)."""
    return [item.strip() for item in value.split(",") if item.strip()]


def resolve_env_files() -> tuple[str, ...]:
    """Load dotenv files from repo root and backend/ (root wins on conflicts).

    Docker Compose injects process env from the project-root ``.env`` via
    ``env_file``. Local ``uv run`` from ``backend/`` only saw ``backend/.env``
    before this helper existed.

    Tests use ``APP_ENV=test`` and must rely on explicit ``os.environ`` only so
    developer ``.env`` files are never loaded during pytest.
    """
    if os.environ.get("APP_ENV") == "test":
        return tuple()

    paths: list[Path] = []
    for candidate in (_BACKEND_ROOT / ".env", _PROJECT_ROOT / ".env"):
        if candidate.is_file():
            paths.append(candidate.resolve())
    if not paths:
        return (".env",)
    return tuple(str(p) for p in paths)


class Settings(BaseSettings):
    APP_ENV: str = "dev"
    APP_NAME: str = "OnePilot AI"
    APP_VERSION: str = "0.1.0"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_SPEECH_MODEL: str = "whisper-1"

    DATABASE_URL: str = "sqlite:///./onepilot_dev.db"
    REDIS_URL: str = ""
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    LANGSMITH_API_KEY: str = ""
    LANGSMITH_TRACING: bool = False
    LANGSMITH_PROJECT: str = "onepilot-ai"
    LANGSMITH_ENDPOINT: str = ""
    SERPER_API_KEY: str = ""
    SERPER_BASE_URL: str = "https://google.serper.dev/search"
    SERPER_TIMEOUT_SECONDS: int = 10
    SERPER_MAX_RESULTS: int = 5

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    GOOGLE_REFRESH_TOKEN: str = ""
    GMAIL_PROVIDER_MODE: str = "auto"
    GMAIL_SEND_ENABLED: bool = False
    GMAIL_CREDENTIALS_JSON: str = ""

    GOOGLE_CALENDAR_ID: str = "primary"
    GOOGLE_CALENDAR_IDS: str = ""
    GOOGLE_CALENDAR_AGGREGATE_SELECTED: bool = True
    GOOGLE_CALENDAR_PROVIDER_MODE: str = "auto"
    GOOGLE_CALENDAR_CREATE_ENABLED: bool = True
    GOOGLE_CALENDAR_DEFAULT_TIMEZONE: str = "Europe/Berlin"
    GOOGLE_CALENDAR_LOOKAHEAD_DAYS: int = 14
    GOOGLE_CALENDAR_SLOT_DURATION_MINUTES: int = 30
    GOOGLE_CALENDAR_WORKDAY_START: str = "09:00"
    GOOGLE_CALENDAR_WORKDAY_END: str = "17:00"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    DEV_AUTH_ENABLED: bool = True
    DEV_ORG_ID: str = "org_demo_onepilot"
    DEV_USER_ID: str = "usr_demo_admin"
    DEV_BYPASS_QUOTAS: bool = False

    CORS_ALLOWED_ORIGINS: str = DEFAULT_CORS_ALLOWED_ORIGINS
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    model_config = SettingsConfigDict(
        env_file=resolve_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("SERPER_API_KEY", mode="before")
    @classmethod
    def _strip_serper_key(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        origins = parse_comma_separated_list(self.CORS_ALLOWED_ORIGINS)
        return origins if origins else parse_comma_separated_list(DEFAULT_CORS_ALLOWED_ORIGINS)

    @property
    def cors_allow_methods_list(self) -> list[str]:
        methods = parse_comma_separated_list(self.CORS_ALLOW_METHODS)
        return methods if methods else ["*"]

    @property
    def cors_allow_headers_list(self) -> list[str]:
        headers = parse_comma_separated_list(self.CORS_ALLOW_HEADERS)
        return headers if headers else ["*"]

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "dev"

    @property
    def is_test(self) -> bool:
        return self.APP_ENV == "test"

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def has_qdrant(self) -> bool:
        return bool(self.QDRANT_URL)

    @property
    def has_redis(self) -> bool:
        return bool(self.REDIS_URL)

    @property
    def has_langsmith(self) -> bool:
        return bool(self.LANGSMITH_API_KEY) and self.LANGSMITH_TRACING

    @property
    def has_serper(self) -> bool:
        return bool(self.SERPER_API_KEY)

    @property
    def has_gmail_oauth(self) -> bool:
        return bool(
            self.GOOGLE_CLIENT_ID
            and self.GOOGLE_CLIENT_SECRET
            and self.GOOGLE_REFRESH_TOKEN
        )

    @property
    def has_gmail_legacy_credentials(self) -> bool:
        return bool(self.GMAIL_CREDENTIALS_JSON.strip())

    @property
    def has_calendar_oauth(self) -> bool:
        return self.has_gmail_oauth


def serper_runtime_status(settings: Settings) -> dict[str, bool | str]:
    """Safe Serper status for health/diagnostics (never exposes the API key)."""
    from onepilot.providers import get_search_provider
    from onepilot.providers.search.mock_search_provider import MockSearchProvider

    configured = settings.has_serper
    provider = get_search_provider(settings)
    is_mock = isinstance(provider, MockSearchProvider)

    if configured and not is_mock:
        mode = "live"
    elif configured and is_mock:
        mode = "mock"
    elif not configured:
        mode = "missing"
    else:
        mode = "fallback"

    return {
        "serper_configured": configured,
        "serper_mode": mode,
        "serper_active": configured and not is_mock,
        "serper_fallback_used": is_mock,
    }


def gmail_runtime_status(settings: Settings) -> dict[str, bool | str]:
    """Safe Gmail status for health/diagnostics (never exposes tokens)."""
    from onepilot.providers import get_email_provider
    from onepilot.providers.email.gmail_provider import GmailProvider
    from onepilot.providers.email.mock_email_provider import MockEmailProvider

    mode_setting = (settings.GMAIL_PROVIDER_MODE or "auto").strip().lower()
    configured = settings.has_gmail_oauth or settings.has_gmail_legacy_credentials

    if mode_setting == "mock":
        return {
            "gmail_configured": configured,
            "gmail_mode": "mock",
            "gmail_active": False,
            "gmail_fallback_used": True,
        }

    if mode_setting == "missing":
        return {
            "gmail_configured": False,
            "gmail_mode": "missing",
            "gmail_active": False,
            "gmail_fallback_used": True,
        }

    provider = get_email_provider(settings)
    is_mock = isinstance(provider, MockEmailProvider)
    is_live = isinstance(provider, GmailProvider)

    if is_live:
        mode = "live"
    elif configured and is_mock:
        mode = "mock"
    elif not configured:
        mode = "mock"
    else:
        mode = "mock"

    return {
        "gmail_configured": configured,
        "gmail_mode": mode,
        "gmail_active": is_live,
        "gmail_fallback_used": is_mock,
    }


def _calendar_config_reason(settings: Settings) -> str | None:
    if not settings.GOOGLE_CLIENT_ID.strip():
        return "missing_google_client_id"
    if not settings.GOOGLE_CLIENT_SECRET.strip():
        return "missing_google_client_secret"
    if not settings.GOOGLE_REFRESH_TOKEN.strip():
        return "missing_refresh_token"
    return None


def calendar_runtime_status(settings: Settings) -> dict[str, bool | str | None]:
    """Safe Google Calendar status for health/diagnostics (never exposes tokens)."""
    from onepilot.providers import get_calendar_provider
    from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider
    from onepilot.providers.calendar.mock_calendar_provider import MockCalendarProvider

    mode_setting = (settings.GOOGLE_CALENDAR_PROVIDER_MODE or "auto").strip().lower()
    configured = settings.has_calendar_oauth
    config_reason = _calendar_config_reason(settings)

    base: dict[str, bool | str | None] = {
        "calendar_configured": configured,
        "calendar_create_enabled": settings.GOOGLE_CALENDAR_CREATE_ENABLED,
        "calendar_status_reason": config_reason,
    }

    if mode_setting == "mock":
        return {
            **base,
            "calendar_mode": "mock",
            "calendar_active": False,
            "calendar_fallback_used": True,
        }

    if mode_setting == "missing":
        return {
            **base,
            "calendar_configured": False,
            "calendar_mode": "missing",
            "calendar_active": False,
            "calendar_fallback_used": True,
            "calendar_status_reason": config_reason or "missing_refresh_token",
        }

    if config_reason:
        return {
            **base,
            "calendar_mode": "missing",
            "calendar_active": False,
            "calendar_fallback_used": True,
        }

    provider = get_calendar_provider(settings)
    is_mock = isinstance(provider, MockCalendarProvider)
    status = provider.get_status()
    mode = status.mode
    reason = status.status_reason or config_reason

    return {
        **base,
        "calendar_mode": mode,
        "calendar_active": status.active and mode == "live",
        "calendar_fallback_used": is_mock or mode != "live",
        "calendar_status_reason": reason,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
