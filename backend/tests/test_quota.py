"""Tests for quota service (direct service-layer tests)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy.orm import Session

from onepilot.core.config import get_settings
from onepilot.core.constants import PlanCode, UsageFeature
from onepilot.core.errors import QuotaExceededError
from onepilot.core.ids import new_id
from onepilot.repositories.models import Organization, Subscription
from onepilot.services import quota_service


def _create_org_with_subscription(
    session: Session,
    plan_code: str = PlanCode.FREE,
) -> str:
    """Create an org and active subscription, returning the org_id."""
    org_id = new_id("org")
    org = Organization(id=org_id, name="QuotaTestOrg", slug=f"quota-test-{org_id[:8]}")
    session.add(org)
    session.flush()

    sub = Subscription(
        id=new_id("sub"),
        organization_id=org_id,
        plan_code=plan_code,
        status="active",
    )
    session.add(sub)
    session.flush()
    return org_id


class TestQuotaCheck:
    def test_check_under_limit(self, db_session: Session):
        org_id = _create_org_with_subscription(db_session)
        result = quota_service.check(db_session, org_id, UsageFeature.CHAT_MESSAGES)
        assert result is True

    def test_check_at_limit(self, db_session: Session):
        org_id = _create_org_with_subscription(db_session)
        limit = 50  # free plan chat_messages limit
        for _ in range(limit):
            quota_service.increment(db_session, org_id, UsageFeature.CHAT_MESSAGES)
        result = quota_service.check(db_session, org_id, UsageFeature.CHAT_MESSAGES)
        assert result is False


class TestQuotaIncrement:
    def test_increment(self, db_session: Session):
        org_id = _create_org_with_subscription(db_session)
        used = quota_service.increment(db_session, org_id, UsageFeature.RAG_QUERIES)
        assert used == 1
        used = quota_service.increment(db_session, org_id, UsageFeature.RAG_QUERIES)
        assert used == 2

    def test_check_and_increment_blocks(self, db_session: Session):
        org_id = _create_org_with_subscription(db_session)
        limit = 20  # free plan rag_queries limit
        for _ in range(limit):
            quota_service.increment(db_session, org_id, UsageFeature.RAG_QUERIES)
        with pytest.raises(QuotaExceededError):
            quota_service.check_and_increment(db_session, org_id, UsageFeature.RAG_QUERIES)


class TestQuotaBypass:
    def test_dev_bypass_quotas(self, db_session: Session):
        org_id = _create_org_with_subscription(db_session)
        limit = 50
        for _ in range(limit):
            quota_service.increment(db_session, org_id, UsageFeature.CHAT_MESSAGES)

        os.environ["DEV_BYPASS_QUOTAS"] = "true"
        get_settings.cache_clear()
        try:
            result = quota_service.check(db_session, org_id, UsageFeature.CHAT_MESSAGES)
            assert result is True
        finally:
            os.environ["DEV_BYPASS_QUOTAS"] = "false"
            get_settings.cache_clear()


class TestUsageSummary:
    def test_usage_summary_shape(self, db_session: Session):
        org_id = _create_org_with_subscription(db_session)
        summary = quota_service.get_usage_summary(db_session, org_id)
        assert isinstance(summary, list)
        assert len(summary) == len(UsageFeature)
        for entry in summary:
            assert "feature" in entry
            assert "used" in entry
            assert "limit" in entry
            assert "remaining" in entry
            assert "period_start" in entry
            assert "period_end" in entry
