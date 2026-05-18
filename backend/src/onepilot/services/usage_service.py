"""Usage event service — records per-call AI / tool usage with cost enrichment."""

from __future__ import annotations

from sqlalchemy.orm import Session

from onepilot.core.ids import new_id
from onepilot.repositories.models import UsageEvent
from onepilot.repositories.usage_events import UsageEventRepository
from onepilot.services.cost_calculator import calculate_usage_cost


def record(
    session: Session,
    *,
    organization_id: str,
    user_id: str | None,
    feature: str,
    model: str | None = None,
    provider: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    embedding_tokens: int = 0,
    audio_seconds: float = 0.0,
    estimated_cost: float | None = None,
    fallback_used: bool = False,
    tool_calls: int = 0,
    latency_ms: int = 0,
    metadata: dict | None = None,
) -> UsageEvent:
    event_metadata = dict(metadata or {})

    if estimated_cost is None:
        cost_estimate = calculate_usage_cost(
            feature=feature,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            embedding_tokens=embedding_tokens,
            audio_seconds=audio_seconds,
            tool_calls=tool_calls,
            fallback_used=fallback_used,
        )
        estimated_cost = cost_estimate.estimated_cost
        event_metadata["cost_breakdown"] = cost_estimate.calculation_breakdown
        event_metadata["price_source"] = cost_estimate.price_source
        event_metadata["currency"] = cost_estimate.currency
    elif "cost_breakdown" not in event_metadata:
        cost_estimate = calculate_usage_cost(
            feature=feature,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            embedding_tokens=embedding_tokens,
            audio_seconds=audio_seconds,
            tool_calls=tool_calls,
            fallback_used=fallback_used,
        )
        event_metadata.setdefault("cost_breakdown", cost_estimate.calculation_breakdown)
        event_metadata.setdefault("price_source", cost_estimate.price_source)
        event_metadata.setdefault("currency", cost_estimate.currency)

    if embedding_tokens > 0:
        event_metadata.setdefault("embedding_tokens", embedding_tokens)
    if audio_seconds > 0:
        event_metadata.setdefault("audio_seconds", audio_seconds)

    event_metadata.setdefault("feature_category", feature)

    repo = UsageEventRepository(session)
    event = UsageEvent(
        id=new_id("uev"),
        organization_id=organization_id,
        user_id=user_id,
        feature=feature,
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=estimated_cost,
        fallback_used=fallback_used,
        tool_calls=tool_calls,
        latency_ms=latency_ms,
        event_metadata=event_metadata,
    )
    return repo.create(event)


def list_for_org(
    session: Session,
    organization_id: str,
    *,
    offset: int = 0,
    limit: int = 100,
    feature: str | None = None,
) -> list[UsageEvent]:
    repo = UsageEventRepository(session)
    return repo.list_for_org(organization_id, offset=offset, limit=limit, feature=feature)


def count_for_org(session: Session, organization_id: str) -> int:
    repo = UsageEventRepository(session)
    return repo.count(organization_id=organization_id)
