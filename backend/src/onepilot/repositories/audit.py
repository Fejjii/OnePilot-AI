"""Audit log repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import AuditLog


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditLog)

    def list_for_org(
        self,
        organization_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
        action: str | None = None,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).where(AuditLog.organization_id == organization_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        return list(self._session.execute(stmt).scalars().all())
