"""Approval request repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onepilot.core.constants import ApprovalStatus
from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import ApprovalRequest


class ApprovalRequestRepository(BaseRepository[ApprovalRequest]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ApprovalRequest)

    def list_for_org(
        self,
        organization_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
        action_type: str | None = None,
    ) -> list[ApprovalRequest]:
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(ApprovalRequest.status == status)
        if action_type:
            stmt = stmt.where(ApprovalRequest.action_type == action_type)
        stmt = (
            stmt.order_by(ApprovalRequest.created_at.desc()).offset(offset).limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def count_for_org(self, organization_id: str, *, status: str | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(ApprovalRequest)
            .where(ApprovalRequest.organization_id == organization_id)
        )
        if status:
            stmt = stmt.where(ApprovalRequest.status == status)
        return self._session.execute(stmt).scalar() or 0

    def count_pending(self, organization_id: str) -> int:
        return self.count_for_org(
            organization_id, status=ApprovalStatus.PENDING.value
        )
