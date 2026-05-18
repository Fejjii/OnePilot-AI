"""Persistent memory service for agent state.

Stores tenant-scoped key/value pairs that the agent (or user) can read across
conversations. Memory is always scoped by ``organization_id``; ``user_id`` is
optional for org-wide scopes. Each item supports a TTL.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from onepilot.core.errors import NotFoundError, ValidationError
from onepilot.core.ids import new_id
from onepilot.core.logging import get_logger
from onepilot.repositories.memory import MemoryItemRepository
from onepilot.repositories.models import MemoryItem
from onepilot.security.auth import Principal

logger = get_logger(__name__)

VALID_SCOPES: frozenset[str] = frozenset({"user", "organization", "agent"})


def _now() -> datetime:
    return datetime.now(UTC)


def _resolve_user_id(principal: Principal, scope: str) -> str | None:
    if scope == "organization":
        return None
    return principal.user_id


def write_memory(
    session: Session,
    *,
    principal: Principal,
    scope: str,
    key: str,
    value: str,
    ttl_seconds: int | None = None,
) -> MemoryItem:
    if scope not in VALID_SCOPES:
        raise ValidationError(f"Invalid memory scope '{scope}'")
    if not key or not key.strip():
        raise ValidationError("Memory key is required")

    user_id = _resolve_user_id(principal, scope)
    repo = MemoryItemRepository(session)
    existing = repo.get_by_key(
        principal.organization_id, scope=scope, key=key, user_id=user_id
    )

    expires_at = (
        _now() + timedelta(seconds=ttl_seconds) if ttl_seconds and ttl_seconds > 0 else None
    )

    if existing is not None:
        existing.value = value
        existing.ttl_seconds = ttl_seconds
        existing.expires_at = expires_at
        session.flush()
        return existing

    item = MemoryItem(
        id=new_id("mem"),
        organization_id=principal.organization_id,
        user_id=user_id,
        scope=scope,
        key=key.strip()[:255],
        value=value,
        ttl_seconds=ttl_seconds,
        expires_at=expires_at,
    )
    repo.create(item)
    logger.info(
        "memory_written",
        organization_id=principal.organization_id,
        scope=scope,
        key=item.key,
    )
    return item


def read_memory(
    session: Session,
    *,
    principal: Principal,
    scope: str,
    key: str,
) -> MemoryItem | None:
    if scope not in VALID_SCOPES:
        raise ValidationError(f"Invalid memory scope '{scope}'")
    user_id = _resolve_user_id(principal, scope)
    repo = MemoryItemRepository(session)
    item = repo.get_by_key(
        principal.organization_id, scope=scope, key=key, user_id=user_id
    )
    if item is None:
        return None
    if item.expires_at and item.expires_at <= _now():
        repo.delete(item)
        return None
    return item


def delete_memory(
    session: Session,
    *,
    principal: Principal,
    scope: str,
    key: str,
) -> None:
    if scope not in VALID_SCOPES:
        raise ValidationError(f"Invalid memory scope '{scope}'")
    user_id = _resolve_user_id(principal, scope)
    repo = MemoryItemRepository(session)
    item = repo.get_by_key(
        principal.organization_id, scope=scope, key=key, user_id=user_id
    )
    if item is None:
        raise NotFoundError(f"Memory item '{key}' not found")
    repo.delete(item)


def list_memory(
    session: Session,
    *,
    principal: Principal,
    scope: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[MemoryItem], int]:
    repo = MemoryItemRepository(session)
    repo.delete_expired(principal.organization_id)
    user_id = _resolve_user_id(principal, scope or "user") if scope else principal.user_id
    items = repo.list_for_scope(
        principal.organization_id,
        scope=scope,
        user_id=user_id,
        offset=offset,
        limit=min(limit, 200),
    )
    return items, len(items)
