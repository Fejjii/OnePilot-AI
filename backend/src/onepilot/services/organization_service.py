from __future__ import annotations

from sqlalchemy.orm import Session

from onepilot.core.constants import Role
from onepilot.core.errors import ConflictError, NotFoundError
from onepilot.core.ids import new_id
from onepilot.repositories.models import OrganizationMember
from onepilot.repositories.organizations import OrganizationMemberRepository, OrganizationRepository
from onepilot.repositories.users import UserRepository
from onepilot.security.auth import Principal


def get_organization(session: Session, principal: Principal) -> dict:
    org_repo = OrganizationRepository(session)
    org = org_repo.get(principal.organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    return {"id": org.id, "name": org.name, "slug": org.slug, "created_at": org.created_at, "updated_at": org.updated_at}


def list_members(session: Session, principal: Principal) -> list[dict]:
    member_repo = OrganizationMemberRepository(session)
    members = member_repo.list_by_org(principal.organization_id)
    result = []
    user_repo = UserRepository(session)
    for m in members:
        user = user_repo.get(m.user_id)
        if user:
            result.append({
                "id": m.id,
                "user_id": m.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "role": m.role,
                "created_at": m.created_at,
            })
    return result


def add_member(
    session: Session,
    principal: Principal,
    email: str,
    role: Role = Role.MEMBER,
) -> dict:
    user_repo = UserRepository(session)
    user = user_repo.get_by_email(email)
    if not user:
        raise NotFoundError(f"No user found with email {email}")

    member_repo = OrganizationMemberRepository(session)
    existing = member_repo.get_membership(principal.organization_id, user.id)
    if existing:
        raise ConflictError("User is already a member of this organization")

    member = OrganizationMember(
        id=new_id("mem"),
        organization_id=principal.organization_id,
        user_id=user.id,
        role=role,
    )
    member_repo.create(member)
    session.commit()

    return {
        "id": member.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": member.role,
        "created_at": member.created_at,
    }
