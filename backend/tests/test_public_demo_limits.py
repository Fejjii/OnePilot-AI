"""Public-demo abuse controls (OP-017)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import UsageFeature
from onepilot.core.errors import QuotaExceededError, RateLimitExceededError
from onepilot.repositories.models import Organization
from onepilot.security.rate_limit import (
    FEATURE_CHAT_IP,
    FEATURE_WEB_SEARCH,
    apply_feature_limit,
    enforce_public_demo_chat_limits,
    enforce_public_demo_web_search_limits,
    reset_rate_limiter,
)
from onepilot.services import quota_service, usage_service


def test_public_demo_chat_ip_limit_is_per_client() -> None:
    reset_rate_limiter()
    settings = Settings(PUBLIC_DEMO_ENABLED=True, PUBLIC_DEMO_CHAT_PER_IP_PER_MINUTE=2)
    apply_feature_limit(FEATURE_CHAT_IP, 2, 60)
    enforce_public_demo_chat_limits(client_ip="1.1.1.1", settings=settings)
    enforce_public_demo_chat_limits(client_ip="1.1.1.1", settings=settings)
    with pytest.raises(RateLimitExceededError):
        enforce_public_demo_chat_limits(client_ip="1.1.1.1", settings=settings)
    enforce_public_demo_chat_limits(client_ip="8.8.8.8", settings=settings)
    reset_rate_limiter()


def test_public_demo_web_search_ip_limit_is_per_client() -> None:
    reset_rate_limiter()
    settings = Settings(
        PUBLIC_DEMO_ENABLED=True, PUBLIC_DEMO_WEB_SEARCH_PER_IP_PER_MINUTE=2
    )
    apply_feature_limit(FEATURE_WEB_SEARCH, 2, 60)
    enforce_public_demo_web_search_limits(client_ip="1.1.1.1", settings=settings)
    enforce_public_demo_web_search_limits(client_ip="1.1.1.1", settings=settings)
    with pytest.raises(RateLimitExceededError):
        enforce_public_demo_web_search_limits(client_ip="1.1.1.1", settings=settings)
    enforce_public_demo_web_search_limits(client_ip="8.8.8.8", settings=settings)
    reset_rate_limiter()


def test_daily_token_budget_blocks_demo_org(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLIC_DEMO_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_DEMO_DAILY_TOKEN_BUDGET", "10")
    get_settings.cache_clear()
    settings = get_settings()
    org_id = settings.DEV_ORG_ID
    if db_session.get(Organization, org_id) is None:
        db_session.add(Organization(id=org_id, name="Demo", slug="demo-budget"))
        db_session.flush()
    usage_service.record(
        db_session,
        organization_id=org_id,
        user_id="usr_budget",
        feature=UsageFeature.CHAT_MESSAGES.value,
        input_tokens=8,
        output_tokens=8,
    )
    db_session.commit()
    with pytest.raises(QuotaExceededError, match="Daily demo usage budget"):
        quota_service.check_daily_token_budget(db_session, org_id, settings=settings)
    get_settings.cache_clear()
