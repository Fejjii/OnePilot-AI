from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import UsageQuota


class UsageQuotaRepository(BaseRepository[UsageQuota]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UsageQuota)

    def get_for_period(
        self, organization_id: str, feature: str, period_start: datetime
    ) -> UsageQuota | None:
        stmt = select(UsageQuota).where(
            UsageQuota.organization_id == organization_id,
            UsageQuota.feature == feature,
            UsageQuota.period_start == period_start,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_current(self, organization_id: str, period_start: datetime) -> list[UsageQuota]:
        stmt = select(UsageQuota).where(
            UsageQuota.organization_id == organization_id,
            UsageQuota.period_start == period_start,
        )
        return list(self._session.execute(stmt).scalars().all())
