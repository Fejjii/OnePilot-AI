from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import Plan, Subscription


class PlanRepository(BaseRepository[Plan]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Plan)

    def get_by_code(self, code: str) -> Plan | None:
        stmt = select(Plan).where(Plan.code == code)
        return self._session.execute(stmt).scalar_one_or_none()

    def list_all_plans(self) -> list[Plan]:
        stmt = select(Plan).order_by(Plan.monthly_price_cents)
        return list(self._session.execute(stmt).scalars().all())


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Subscription)

    def get_active(self, organization_id: str) -> Subscription | None:
        stmt = select(Subscription).where(
            Subscription.organization_id == organization_id,
            Subscription.status == "active",
        )
        return self._session.execute(stmt).scalar_one_or_none()
