from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.core.constants import Role
from onepilot.security.permissions import require_admin, require_viewer
from onepilot.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


class AddMemberRequest(BaseModel):
    email: str
    role: Role = Role.MEMBER


@router.get("/current")
def get_current_organization(
    principal: CurrentPrincipal,
    session: DBSession,
) -> dict:
    require_viewer(principal)
    return organization_service.get_organization(session, principal)


@router.get("/current/members")
def list_members(
    principal: CurrentPrincipal,
    session: DBSession,
) -> list[dict]:
    require_admin(principal)
    return organization_service.list_members(session, principal)


@router.post("/current/members")
def add_member(
    body: AddMemberRequest,
    principal: CurrentPrincipal,
    session: DBSession,
) -> dict:
    require_admin(principal)
    return organization_service.add_member(
        session=session,
        principal=principal,
        email=body.email,
        role=body.role,
    )
