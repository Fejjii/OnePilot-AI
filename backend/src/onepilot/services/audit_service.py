"""Audit log service — records tamper-evident events for compliance."""

from __future__ import annotations

from sqlalchemy.orm import Session

from onepilot.core.ids import new_id
from onepilot.repositories.audit import AuditLogRepository
from onepilot.repositories.models import AuditLog


def record(
    session: Session,
    *,
    organization_id: str,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    detail: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    repo = AuditLogRepository(session)
    log = AuditLog(
        id=new_id("aud"),
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
    return repo.create(log)


def list_for_org(
    session: Session,
    organization_id: str,
    *,
    offset: int = 0,
    limit: int = 100,
    action: str | None = None,
) -> list[AuditLog]:
    repo = AuditLogRepository(session)
    return repo.list_for_org(organization_id, offset=offset, limit=limit, action=action)


def count_for_org(session: Session, organization_id: str) -> int:
    repo = AuditLogRepository(session)
    return repo.count(organization_id=organization_id)
