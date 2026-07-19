"""Memory store HTTP endpoints (persistent agent memory)."""

from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession, SettingsDep
from onepilot.core.errors import NotFoundError
from onepilot.schemas.memory import (
    MemoryClearResponse,
    MemoryItemResponse,
    MemoryListResponse,
    MemoryPreferenceRequest,
    MemoryStatusResponse,
    MemoryWriteRequest,
)
from onepilot.security.permissions import require_member
from onepilot.services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=MemoryListResponse)
def list_memory(
    principal: CurrentPrincipal,
    session: DBSession,
    scope: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> MemoryListResponse:
    require_member(principal)
    items, total = memory_service.list_memory(
        session,
        principal=principal,
        scope=scope,
        offset=offset,
        limit=limit,
    )
    return MemoryListResponse(
        items=[MemoryItemResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/status", response_model=MemoryStatusResponse)
def get_memory_status(
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> MemoryStatusResponse:
    require_member(principal)
    status = memory_service.memory_status(
        session, principal=principal, settings=settings
    )
    return MemoryStatusResponse.model_validate(status)


@router.post("", response_model=MemoryItemResponse)
def write_memory(
    body: MemoryWriteRequest,
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> MemoryItemResponse:
    require_member(principal)
    item = memory_service.write_memory(
        session,
        principal=principal,
        scope=body.scope,
        key=body.key,
        value=body.value,
        ttl_seconds=body.ttl_seconds,
        settings=settings,
    )
    session.commit()
    return MemoryItemResponse.model_validate(item)


@router.post("/preferences", response_model=MemoryStatusResponse)
def set_memory_preferences(
    body: MemoryPreferenceRequest,
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> MemoryStatusResponse:
    """Enable or disable agent memory for the current user."""
    require_member(principal)
    memory_service.set_memory_disabled(
        session,
        principal=principal,
        disabled=body.disabled,
        settings=settings,
    )
    session.commit()
    status = memory_service.memory_status(
        session, principal=principal, settings=settings
    )
    return MemoryStatusResponse.model_validate(status)


@router.delete("", response_model=MemoryClearResponse)
def clear_memory(
    principal: CurrentPrincipal,
    session: DBSession,
) -> MemoryClearResponse:
    """Clear all user-owned memories (user + agent scopes)."""
    require_member(principal)
    deleted = memory_service.clear_user_memory(session, principal=principal)
    session.commit()
    return MemoryClearResponse(deleted_count=deleted)


@router.get("/{scope}/{key}", response_model=MemoryItemResponse)
def read_memory(
    scope: str,
    key: str,
    principal: CurrentPrincipal,
    session: DBSession,
) -> MemoryItemResponse:
    require_member(principal)
    item = memory_service.read_memory(
        session, principal=principal, scope=scope, key=key
    )
    if item is None:
        raise NotFoundError(f"Memory item '{key}' not found")
    return MemoryItemResponse.model_validate(item)


@router.delete("/{scope}/{key}", status_code=204)
def delete_memory(
    scope: str,
    key: str,
    principal: CurrentPrincipal,
    session: DBSession,
) -> None:
    require_member(principal)
    memory_service.delete_memory(
        session, principal=principal, scope=scope, key=key
    )
    session.commit()
