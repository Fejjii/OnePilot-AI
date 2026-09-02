"""Usage event repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import UsageEvent


class UsageEventRepository(BaseRepository[UsageEvent]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UsageEvent)

    def list_for_org(
        self,
        organization_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
        feature: str | None = None,
    ) -> list[UsageEvent]:
        stmt = select(UsageEvent).where(UsageEvent.organization_id == organization_id)
        if feature:
            stmt = stmt.where(UsageEvent.feature == feature)
        stmt = stmt.order_by(UsageEvent.created_at.desc()).offset(offset).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def sum_tokens_since(self, organization_id: str, since: datetime) -> int:
        stmt = select(
            func.coalesce(
                func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens),
                0,
            )
        ).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.created_at >= since,
        )
        return int(self._session.execute(stmt).scalar_one() or 0)
