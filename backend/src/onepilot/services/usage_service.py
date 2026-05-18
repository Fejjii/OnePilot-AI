"""Usage event service — records per-call AI / tool usage."""

from __future__ import annotations

from sqlalchemy.orm import Session

from onepilot.core.ids import new_id
from onepilot.repositories.models import UsageEvent
from onepilot.repositories.usage_events import UsageEventRepository


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
    estimated_cost: float = 0.0,
    fallback_used: bool = False,
    tool_calls: int = 0,
    latency_ms: int = 0,
    metadata: dict | None = None,
) -> UsageEvent:
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
        event_metadata=metadata or {},
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
