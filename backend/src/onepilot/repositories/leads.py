"""Lead repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import Lead


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Lead)

    def list_for_org(
        self,
        organization_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> list[Lead]:
        stmt = select(Lead).where(Lead.organization_id == organization_id)
        if status:
            stmt = stmt.where(Lead.status == status)
        stmt = stmt.order_by(Lead.created_at.desc()).offset(offset).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def count_for_org(self, organization_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Lead)
            .where(Lead.organization_id == organization_id)
        )
        return self._session.execute(stmt).scalar() or 0

    def get_by_email(self, organization_id: str, email: str) -> Lead | None:
        stmt = select(Lead).where(
            Lead.organization_id == organization_id,
            Lead.email == email,
        )
        return self._session.execute(stmt).scalar_one_or_none()
