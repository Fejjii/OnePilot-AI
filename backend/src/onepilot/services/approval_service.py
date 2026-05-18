"""Approval-request service.

Creates and decides on approval requests. The agent workflow calls
:func:`create` whenever a proposed action requires human review (e.g.,
``send_email``, ``schedule_meeting``, ``update_crm``, ``external_action``,
``high_risk_tool_call``, ``low_confidence_action``). Decisions are restricted
to Owner/Admin roles by the router; this service stays role-agnostic for
testability.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from onepilot.core.constants import ApprovalStatus, Role
from onepilot.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from onepilot.core.ids import new_id
from onepilot.core.logging import get_logger
from onepilot.repositories.approvals import ApprovalRequestRepository
from onepilot.repositories.models import ApprovalRequest
from onepilot.security.auth import Principal
from onepilot.services import audit_service

logger = get_logger(__name__)


GATED_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "send_email",
        "schedule_meeting",
        "update_crm",
        "external_action",
        "high_risk_tool_call",
        "low_confidence_action",
    }
)


def requires_approval(action_type: str) -> bool:
    return action_type in GATED_ACTION_TYPES


def create(
    session: Session,
    *,
    principal: Principal,
    action_type: str,
    title: str,
    description: str = "",
    proposed_payload: dict | None = None,
    risk_level: str = "medium",
    reason: str = "",
) -> ApprovalRequest:
    if not action_type:
        raise ValidationError("action_type is required")
    if risk_level not in {"low", "medium", "high"}:
        raise ValidationError(f"Invalid risk_level '{risk_level}'")

    approval = ApprovalRequest(
        id=new_id("apv"),
        organization_id=principal.organization_id,
        action_type=action_type,
        title=title[:255],
        description=description,
        proposed_payload=proposed_payload or {},
        risk_level=risk_level,
        status=ApprovalStatus.PENDING.value,
        reason=reason,
        created_by=principal.user_id,
    )
    repo = ApprovalRequestRepository(session)
    repo.create(approval)

    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="approval.created",
        resource_type="approval_request",
        resource_id=approval.id,
        detail={
            "action_type": action_type,
            "risk_level": risk_level,
            "title": title,
        },
    )
    logger.info(
        "approval_created",
        organization_id=principal.organization_id,
        approval_id=approval.id,
        action_type=action_type,
    )
    return approval


def list_for_org(
    session: Session,
    *,
    principal: Principal,
    offset: int = 0,
    limit: int = 50,
    status: str | None = None,
    action_type: str | None = None,
) -> tuple[list[ApprovalRequest], int, int]:
    repo = ApprovalRequestRepository(session)
    items = repo.list_for_org(
        principal.organization_id,
        offset=offset,
        limit=min(limit, 100),
        status=status,
        action_type=action_type,
    )
    total = repo.count_for_org(principal.organization_id, status=status)
    pending = repo.count_pending(principal.organization_id)
    return items, total, pending


def get(
    session: Session, *, principal: Principal, approval_id: str
) -> ApprovalRequest:
    repo = ApprovalRequestRepository(session)
    approval = repo.get(approval_id, organization_id=principal.organization_id)
    if approval is None:
        raise NotFoundError(f"Approval '{approval_id}' not found")
    return approval


def decide(
    session: Session,
    *,
    principal: Principal,
    approval_id: str,
    status: ApprovalStatus,
    reason: str | None = None,
) -> ApprovalRequest:
    if Role(principal.role) not in {Role.OWNER, Role.ADMIN}:
        raise PermissionDeniedError("Only owners or admins can decide approvals")

    if status not in {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.NEEDS_MORE_INFO,
    }:
        raise ValidationError(f"Invalid decision status '{status}'")

    approval = get(session, principal=principal, approval_id=approval_id)
    if approval.status != ApprovalStatus.PENDING.value:
        raise ValidationError(
            f"Approval '{approval_id}' is already '{approval.status}'"
        )

    approval.status = status.value
    approval.reviewed_by = principal.user_id
    approval.reviewed_at = datetime.now(UTC)
    if reason:
        approval.reason = reason
    session.flush()

    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action=f"approval.{status.value}",
        resource_type="approval_request",
        resource_id=approval.id,
        detail={"action_type": approval.action_type, "reason": reason},
    )
    logger.info(
        "approval_decided",
        organization_id=principal.organization_id,
        approval_id=approval.id,
        status=status.value,
    )
    return approval
