"""Admin endpoints: audit logs and usage events.

Both endpoints are tenant-scoped and require Owner/Admin. Implementation is
deliberately thin — paginate and project models to response schemas. Business
logic lives in services.
"""

from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.schemas.audit import (
    AuditListResponse,
    AuditLogResponse,
    UsageEventListResponse,
    UsageEventResponse,
)
from onepilot.security.permissions import require_admin
from onepilot.services import audit_service, usage_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs", response_model=AuditListResponse)
def list_audit_logs(
    principal: CurrentPrincipal,
    session: DBSession,
    offset: int = 0,
    limit: int = 50,
    action: str | None = None,
) -> AuditListResponse:
    require_admin(principal)
    items = audit_service.list_for_org(
        session,
        principal.organization_id,
        offset=offset,
        limit=min(limit, 200),
        action=action,
    )
    total = audit_service.count_for_org(session, principal.organization_id)
    return AuditListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/usage-events", response_model=UsageEventListResponse)
def list_usage_events(
    principal: CurrentPrincipal,
    session: DBSession,
    offset: int = 0,
    limit: int = 50,
    feature: str | None = None,
) -> UsageEventListResponse:
    require_admin(principal)
    items = usage_service.list_for_org(
        session,
        principal.organization_id,
        offset=offset,
        limit=min(limit, 200),
        feature=feature,
    )
    total = usage_service.count_for_org(session, principal.organization_id)
    return UsageEventListResponse(
        items=[UsageEventResponse.model_validate(item) for item in items],
        total=total,
    )
