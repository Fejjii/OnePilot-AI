"""Memory item repository (persistent key/value memory for agents)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import MemoryItem


class MemoryItemRepository(BaseRepository[MemoryItem]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, MemoryItem)

    def get_by_key(
        self,
        organization_id: str,
        *,
        scope: str,
        key: str,
        user_id: str | None = None,
    ) -> MemoryItem | None:
        stmt = select(MemoryItem).where(
            MemoryItem.organization_id == organization_id,
            MemoryItem.scope == scope,
            MemoryItem.key == key,
        )
        if user_id is None:
            stmt = stmt.where(MemoryItem.user_id.is_(None))
        else:
            stmt = stmt.where(MemoryItem.user_id == user_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def list_for_scope(
        self,
        organization_id: str,
        *,
        scope: str | None = None,
        user_id: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[MemoryItem]:
        stmt = select(MemoryItem).where(MemoryItem.organization_id == organization_id)
        if scope:
            stmt = stmt.where(MemoryItem.scope == scope)
        if user_id is not None:
            stmt = stmt.where(MemoryItem.user_id == user_id)
        stmt = stmt.order_by(MemoryItem.updated_at.desc()).offset(offset).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def delete_expired(self, organization_id: str) -> int:
        now = datetime.now(UTC)
        stmt = delete(MemoryItem).where(
            MemoryItem.organization_id == organization_id,
            MemoryItem.expires_at.is_not(None),
            MemoryItem.expires_at <= now,
        )
        result = self._session.execute(stmt)
        return result.rowcount or 0

    def delete_for_user(
        self,
        organization_id: str,
        *,
        user_id: str,
        scopes: list[str] | None = None,
    ) -> int:
        """Delete memory rows owned by a user (user/agent scopes)."""
        stmt = delete(MemoryItem).where(
            MemoryItem.organization_id == organization_id,
            MemoryItem.user_id == user_id,
        )
        if scopes:
            stmt = stmt.where(MemoryItem.scope.in_(scopes))
        result = self._session.execute(stmt)
        return result.rowcount or 0

    def list_for_agent_context(
        self,
        organization_id: str,
        *,
        user_id: str,
        scopes: list[str] | None = None,
        limit: int = 50,
    ) -> list[MemoryItem]:
        """List non-expired user/agent memories for prompt injection."""
        now = datetime.now(UTC)
        active_scopes = scopes or ["user", "agent"]
        stmt = (
            select(MemoryItem)
            .where(
                MemoryItem.organization_id == organization_id,
                MemoryItem.user_id == user_id,
                MemoryItem.scope.in_(active_scopes),
                (MemoryItem.expires_at.is_(None) | (MemoryItem.expires_at > now)),
            )
            .order_by(MemoryItem.updated_at.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())
