from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.services import auth_service

router = APIRouter(tags=["users"])


@router.get("/me")
def get_me(principal: CurrentPrincipal, session: DBSession) -> dict:
    details = auth_service.get_principal_details(session, principal)
    user = details["user"]
    org = details["organization"]
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "updated_at": org.updated_at.isoformat() if org.updated_at else None,
        } if org else None,
        "role": details["role"],
        "plan": details["plan_code"],
    }
