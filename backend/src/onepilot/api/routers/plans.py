from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.services import plan_service

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("")
def list_plans(session: DBSession) -> list[dict]:
    return plan_service.list_plans(session)


@router.get("/current")
def get_current_plan(
    principal: CurrentPrincipal,
    session: DBSession,
) -> dict:
    return plan_service.get_current_plan(session, principal)
