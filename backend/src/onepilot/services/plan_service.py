from __future__ import annotations

from sqlalchemy.orm import Session

from onepilot.core.errors import NotFoundError
from onepilot.repositories.plans import PlanRepository, SubscriptionRepository
from onepilot.security.auth import Principal


def list_plans(session: Session) -> list[dict]:
    repo = PlanRepository(session)
    plans = repo.list_all_plans()
    return [
        {
            "code": p.code,
            "name": p.name,
            "monthly_price_cents": p.monthly_price_cents,
            "limits": p.limits,
        }
        for p in plans
    ]


def get_plan(session: Session, code: str) -> dict:
    repo = PlanRepository(session)
    plan = repo.get_by_code(code)
    if not plan:
        raise NotFoundError(f"Plan '{code}' not found")
    return {
        "code": plan.code,
        "name": plan.name,
        "monthly_price_cents": plan.monthly_price_cents,
        "limits": plan.limits,
    }


def get_current_plan(session: Session, principal: Principal) -> dict:
    sub_repo = SubscriptionRepository(session)
    sub = sub_repo.get_active(principal.organization_id)
    if not sub:
        raise NotFoundError("No active subscription")

    plan_repo = PlanRepository(session)
    plan = plan_repo.get_by_code(sub.plan_code)
    if not plan:
        raise NotFoundError("Plan not found for subscription")

    return {
        "plan": {
            "code": plan.code,
            "name": plan.name,
            "monthly_price_cents": plan.monthly_price_cents,
            "limits": plan.limits,
        },
        "subscription": {
            "id": sub.id,
            "organization_id": sub.organization_id,
            "plan_code": sub.plan_code,
            "status": sub.status,
            "started_at": sub.started_at,
            "renews_at": sub.renews_at,
        },
    }
