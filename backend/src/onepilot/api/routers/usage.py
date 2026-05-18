from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.services import quota_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/summary")
def get_usage_summary(
    principal: CurrentPrincipal,
    session: DBSession,
) -> dict:
    quotas = quota_service.get_usage_summary(session, principal.organization_id)
    return {
        "organization_id": principal.organization_id,
        "plan_code": principal.plan_code,
        "quotas": quotas,
        "total_estimated_cost": 0.0,
    }
