"""Billing aggregation and invoice preview (no real payments)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onepilot.core.pricing_config import PLAN_ENTITLEMENTS
from onepilot.providers import get_billing_provider
from onepilot.repositories.models import UsageEvent
from onepilot.repositories.plans import PlanRepository, SubscriptionRepository
from onepilot.services import quota_service


def _current_period() -> tuple[datetime, datetime]:
    return quota_service._current_period()  # noqa: SLF001


def _billing_provider_info() -> tuple[str, bool]:
    import os

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if stripe_key:
        return "stripe_configured_not_live", False
    return "mock", True


def _get_plan_code(session: Session, organization_id: str) -> str:
    sub_repo = SubscriptionRepository(session)
    sub = sub_repo.get_active(organization_id)
    return sub.plan_code if sub else "free"


def _events_in_period(
    session: Session,
    organization_id: str,
    period_start: datetime,
    period_end: datetime,
) -> list[UsageEvent]:
    stmt = (
        select(UsageEvent)
        .where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.created_at >= period_start,
            UsageEvent.created_at < period_end,
        )
        .order_by(UsageEvent.created_at.desc())
    )
    return list(session.execute(stmt).scalars().all())


def _aggregate_events(events: list[UsageEvent]) -> dict[str, Any]:
    by_feature: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"event_count": 0, "estimated_cost": 0.0, "input_tokens": 0, "output_tokens": 0}
    )
    by_model: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"event_count": 0, "estimated_cost": 0.0, "input_tokens": 0, "output_tokens": 0}
    )
    tokens_by_model: dict[str, dict[str, int]] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0}
    )
    by_user: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"estimated_cost": 0.0, "event_count": 0}
    )
    total_cost = 0.0

    for event in events:
        total_cost += float(event.estimated_cost or 0.0)
        feat = event.feature
        by_feature[feat]["event_count"] = int(by_feature[feat]["event_count"]) + 1
        by_feature[feat]["estimated_cost"] = float(by_feature[feat]["estimated_cost"]) + float(
            event.estimated_cost or 0.0
        )
        by_feature[feat]["input_tokens"] = int(by_feature[feat]["input_tokens"]) + event.input_tokens
        by_feature[feat]["output_tokens"] = int(by_feature[feat]["output_tokens"]) + event.output_tokens

        model_key = event.model or "unknown"
        by_model[model_key]["event_count"] = int(by_model[model_key]["event_count"]) + 1
        by_model[model_key]["estimated_cost"] = float(by_model[model_key]["estimated_cost"]) + float(
            event.estimated_cost or 0.0
        )
        by_model[model_key]["input_tokens"] = int(by_model[model_key]["input_tokens"]) + event.input_tokens
        by_model[model_key]["output_tokens"] = int(by_model[model_key]["output_tokens"]) + event.output_tokens

        tokens_by_model[model_key]["input_tokens"] += event.input_tokens
        tokens_by_model[model_key]["output_tokens"] += event.output_tokens

        if event.user_id:
            by_user[event.user_id]["estimated_cost"] = float(by_user[event.user_id]["estimated_cost"]) + float(
                event.estimated_cost or 0.0
            )
            by_user[event.user_id]["event_count"] = int(by_user[event.user_id]["event_count"]) + 1

    return {
        "total_cost": round(total_cost, 8),
        "by_feature": by_feature,
        "by_model": by_model,
        "tokens_by_model": tokens_by_model,
        "by_user": by_user,
    }


def _estimate_overage(session: Session, organization_id: str, plan_code: str) -> float:
    """Placeholder overage estimate — metered billing not enforced yet."""
    entitlement = PLAN_ENTITLEMENTS.get(plan_code)
    if not entitlement or entitlement.overage_policy == "block_at_limit":
        return 0.0
    return 0.0


def get_entitlement(plan_code: str) -> dict[str, Any]:
    ent = PLAN_ENTITLEMENTS.get(plan_code, PLAN_ENTITLEMENTS["free"])
    return {
        "plan_code": plan_code,
        "included_chat_messages": ent.included_chat_messages,
        "included_rag_queries": ent.included_rag_queries,
        "included_speech_minutes": ent.included_speech_minutes,
        "included_document_uploads": ent.included_document_uploads,
        "included_storage_mb": ent.included_storage_mb,
        "included_team_members": ent.included_team_members,
        "base_price_cents": ent.base_price_cents,
        "overage_policy": ent.overage_policy,
    }


def get_billing_summary(session: Session, organization_id: str) -> dict[str, Any]:
    period_start, period_end = _current_period()
    plan_code = _get_plan_code(session, organization_id)
    events = _events_in_period(session, organization_id, period_start, period_end)
    agg = _aggregate_events(events)
    quotas = quota_service.get_usage_summary(session, organization_id)
    provider_mode, mock_mode = _billing_provider_info()

    usage_by_feature = [
        {
            "feature": feat,
            "event_count": int(data["event_count"]),
            "estimated_cost": round(float(data["estimated_cost"]), 8),
            "input_tokens": int(data["input_tokens"]),
            "output_tokens": int(data["output_tokens"]),
        }
        for feat, data in sorted(agg["by_feature"].items(), key=lambda x: -float(x[1]["estimated_cost"]))
    ]
    usage_by_model = [
        {
            "model": model,
            "event_count": int(data["event_count"]),
            "estimated_cost": round(float(data["estimated_cost"]), 8),
            "input_tokens": int(data["input_tokens"]),
            "output_tokens": int(data["output_tokens"]),
        }
        for model, data in sorted(agg["by_model"].items(), key=lambda x: -float(x[1]["estimated_cost"]))
    ]
    tokens_by_model = [
        {
            "model": model,
            "input_tokens": data["input_tokens"],
            "output_tokens": data["output_tokens"],
            "total_tokens": data["input_tokens"] + data["output_tokens"],
        }
        for model, data in agg["tokens_by_model"].items()
    ]
    top_users = [
        {
            "user_id": uid,
            "estimated_cost": round(float(data["estimated_cost"]), 8),
            "event_count": int(data["event_count"]),
        }
        for uid, data in sorted(agg["by_user"].items(), key=lambda x: -float(x[1]["estimated_cost"]))[:10]
    ]

    return {
        "organization_id": organization_id,
        "current_plan": plan_code,
        "billing_period": {"start": period_start, "end": period_end},
        "total_estimated_cost": agg["total_cost"],
        "currency": "USD",
        "usage_by_feature": usage_by_feature,
        "usage_by_model": usage_by_model,
        "tokens_by_model": tokens_by_model,
        "remaining_quota": quotas,
        "overage_estimate": _estimate_overage(session, organization_id, plan_code),
        "top_users": top_users,
        "billing_provider_mode": provider_mode,
        "mock_mode": mock_mode,
    }


def get_billing_usage(
    session: Session,
    organization_id: str,
    *,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    period_start, period_end = _current_period()
    events = _events_in_period(session, organization_id, period_start, period_end)
    total_cost = sum(float(e.estimated_cost or 0.0) for e in events)
    page = events[offset : offset + limit]
    return {
        "organization_id": organization_id,
        "billing_period": {"start": period_start, "end": period_end},
        "events": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "feature": e.feature,
                "model": e.model,
                "provider": e.provider,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "estimated_cost": e.estimated_cost,
                "fallback_used": e.fallback_used,
                "tool_calls": e.tool_calls,
                "created_at": e.created_at,
                "metadata": e.event_metadata,
            }
            for e in page
        ],
        "total": len(events),
        "total_estimated_cost": round(total_cost, 8),
    }


def get_invoice_preview(session: Session, organization_id: str) -> dict[str, Any]:
    period_start, period_end = _current_period()
    plan_code = _get_plan_code(session, organization_id)
    entitlement = PLAN_ENTITLEMENTS.get(plan_code, PLAN_ENTITLEMENTS["free"])
    summary = get_billing_summary(session, organization_id)
    usage_cost = float(summary["total_estimated_cost"])
    overage_cost = float(summary["overage_estimate"])
    base_cents = entitlement.base_price_cents
    usage_cents = int(round(usage_cost * 100))
    overage_cents = int(round(overage_cost * 100))
    total_cents = base_cents + usage_cents + overage_cents

    line_items = [
        {
            "description": f"{plan_code.title()} plan (base)",
            "quantity": 1,
            "unit_amount_cents": base_cents,
            "amount_cents": base_cents,
            "metadata": {"type": "subscription"},
        },
        {
            "description": "Estimated AI usage (tokens, speech, tools)",
            "quantity": 1,
            "unit_amount_cents": usage_cents,
            "amount_cents": usage_cents,
            "metadata": {"type": "usage", "estimated": True},
        },
    ]
    if overage_cents > 0:
        line_items.append(
            {
                "description": "Estimated overage",
                "quantity": 1,
                "unit_amount_cents": overage_cents,
                "amount_cents": overage_cents,
                "metadata": {"type": "overage", "estimated": True},
            }
        )

    provider_mode, mock_mode = _billing_provider_info()
    billing_provider = get_billing_provider()
    stripe_preview = None
    if hasattr(billing_provider, "get_invoice_preview"):
        stripe_preview = billing_provider.get_invoice_preview(organization_id, plan_code)

    return {
        "organization_id": organization_id,
        "plan_code": plan_code,
        "billing_period": {"start": period_start, "end": period_end},
        "base_plan_price_cents": base_cents,
        "estimated_usage_cost": usage_cost,
        "estimated_overage_cost": overage_cost,
        "total_estimated_due_cents": total_cents,
        "currency": "USD",
        "line_items": line_items,
        "mock_stripe": mock_mode,
        "provider_status": provider_mode,
        "stripe_preview": stripe_preview,
    }


def list_billing_plans(session: Session, organization_id: str) -> dict[str, Any]:
    plan_code = _get_plan_code(session, organization_id)
    plan_repo = PlanRepository(session)
    plans = plan_repo.list_all_plans()
    return {
        "current_plan": plan_code,
        "entitlements": get_entitlement(plan_code),
        "available_plans": [
            {
                "code": p.code,
                "name": p.name,
                "monthly_price_cents": p.monthly_price_cents,
                "limits": p.limits,
                "entitlements": get_entitlement(p.code),
            }
            for p in plans
        ],
    }


def total_estimated_cost_for_org(
    session: Session,
    organization_id: str,
) -> float:
    period_start, period_end = _current_period()
    stmt = select(func.coalesce(func.sum(UsageEvent.estimated_cost), 0.0)).where(
        UsageEvent.organization_id == organization_id,
        UsageEvent.created_at >= period_start,
        UsageEvent.created_at < period_end,
    )
    result = session.execute(stmt).scalar()
    return round(float(result or 0.0), 8)
