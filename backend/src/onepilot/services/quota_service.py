from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from onepilot.core.config import get_settings
from onepilot.core.constants import UsageFeature
from onepilot.core.errors import NotFoundError, QuotaExceededError
from onepilot.core.ids import new_id
from onepilot.repositories.models import UsageQuota
from onepilot.repositories.plans import PlanRepository, SubscriptionRepository
from onepilot.repositories.usage import UsageQuotaRepository


def _current_period() -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    return start, end


def _get_limit(session: Session, organization_id: str, feature: str) -> int:
    sub_repo = SubscriptionRepository(session)
    sub = sub_repo.get_active(organization_id)
    if not sub:
        raise NotFoundError("No active subscription")

    plan_repo = PlanRepository(session)
    plan = plan_repo.get_by_code(sub.plan_code)
    if not plan:
        raise NotFoundError("Plan not found")

    limits: dict = plan.limits or {}
    return limits.get(feature, 0)


def check(session: Session, organization_id: str, feature: str | UsageFeature) -> bool:
    settings = get_settings()
    if settings.DEV_BYPASS_QUOTAS:
        return True

    feature_str = str(feature)
    limit = _get_limit(session, organization_id, feature_str)
    if limit <= 0:
        return True

    period_start, _ = _current_period()
    quota_repo = UsageQuotaRepository(session)
    quota = quota_repo.get_for_period(organization_id, feature_str, period_start)

    used = quota.used if quota else 0
    return used < limit


def increment(
    session: Session,
    organization_id: str,
    feature: str | UsageFeature,
    amount: int = 1,
) -> int:
    feature_str = str(feature)
    period_start, period_end = _current_period()
    quota_repo = UsageQuotaRepository(session)
    quota = quota_repo.get_for_period(organization_id, feature_str, period_start)

    if not quota:
        quota = UsageQuota(
            id=new_id("uq"),
            organization_id=organization_id,
            feature=feature_str,
            used=0,
            period_start=period_start,
            period_end=period_end,
        )
        quota_repo.create(quota)

    quota.used += amount
    session.flush()
    return quota.used


def check_and_increment(
    session: Session,
    organization_id: str,
    feature: str | UsageFeature,
    amount: int = 1,
) -> int:
    if not check(session, organization_id, feature):
        raise QuotaExceededError(f"Quota exceeded for {feature}")
    return increment(session, organization_id, feature, amount)


def get_usage_summary(session: Session, organization_id: str) -> list[dict]:
    period_start, period_end = _current_period()
    quota_repo = UsageQuotaRepository(session)
    quotas = quota_repo.list_current(organization_id, period_start)

    sub_repo = SubscriptionRepository(session)
    sub = sub_repo.get_active(organization_id)
    plan_code = sub.plan_code if sub else "free"

    plan_repo = PlanRepository(session)
    plan = plan_repo.get_by_code(plan_code)
    limits: dict = plan.limits if plan else {}

    used_map = {q.feature: q.used for q in quotas}
    result = []
    for feature in UsageFeature:
        feat_str = str(feature)
        limit = limits.get(feat_str, 0)
        used = used_map.get(feat_str, 0)
        result.append({
            "feature": feat_str,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        })
    return result
