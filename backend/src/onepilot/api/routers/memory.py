"""Memory store HTTP endpoints (persistent agent memory)."""

from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.schemas.memory import (
    MemoryItemResponse,
    MemoryListResponse,
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


@router.post("", response_model=MemoryItemResponse)
def write_memory(
    body: MemoryWriteRequest,
    principal: CurrentPrincipal,
    session: DBSession,
) -> MemoryItemResponse:
    require_member(principal)
    item = memory_service.write_memory(
        session,
        principal=principal,
        scope=body.scope,
        key=body.key,
        value=body.value,
        ttl_seconds=body.ttl_seconds,
    )
    session.commit()
    return MemoryItemResponse.model_validate(item)


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
        from onepilot.core.errors import NotFoundError

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
