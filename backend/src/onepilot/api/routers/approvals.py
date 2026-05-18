"""Approval workflow HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.schemas.approvals import (
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalResponse,
)
from onepilot.security.permissions import require_admin, require_member
from onepilot.services import approval_service

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=ApprovalListResponse)
def list_approvals(
    principal: CurrentPrincipal,
    session: DBSession,
    offset: int = 0,
    limit: int = 50,
    status: str | None = None,
    action_type: str | None = None,
) -> ApprovalListResponse:
    require_member(principal)
    items, total, pending = approval_service.list_for_org(
        session,
        principal=principal,
        offset=offset,
        limit=limit,
        status=status,
        action_type=action_type,
    )
    return ApprovalListResponse(
        items=[ApprovalResponse.model_validate(a) for a in items],
        total=total,
        pending_count=pending,
    )


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: str,
    principal: CurrentPrincipal,
    session: DBSession,
) -> ApprovalResponse:
    require_member(principal)
    approval = approval_service.get(
        session, principal=principal, approval_id=approval_id
    )
    return ApprovalResponse.model_validate(approval)


@router.post("/{approval_id}/decision", response_model=ApprovalResponse)
def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
    principal: CurrentPrincipal,
    session: DBSession,
) -> ApprovalResponse:
    require_admin(principal)
    approval = approval_service.decide(
        session,
        principal=principal,
        approval_id=approval_id,
        status=body.status,
        reason=body.reason,
    )
    session.commit()
    return ApprovalResponse.model_validate(approval)
