"""Usage event repository."""

from __future__ import annotations

from sqlalchemy import select
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
