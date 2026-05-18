"""Lead HTTP endpoints (list / get / create / update)."""

from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.schemas.leads import LeadCreate, LeadListResponse, LeadResponse, LeadUpdate
from onepilot.security.permissions import require_member
from onepilot.services import lead_service

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadListResponse)
def list_leads(
    principal: CurrentPrincipal,
    session: DBSession,
    offset: int = 0,
    limit: int = 50,
    status: str | None = None,
) -> LeadListResponse:
    require_member(principal)
    items, total = lead_service.list_leads(
        session,
        principal=principal,
        offset=offset,
        limit=limit,
        status=status,
    )
    return LeadListResponse(
        items=[LeadResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post("", response_model=LeadResponse)
def create_lead(
    body: LeadCreate,
    principal: CurrentPrincipal,
    session: DBSession,
) -> LeadResponse:
    require_member(principal)
    lead = lead_service.create_lead(
        session,
        principal=principal,
        name=body.name,
        email=body.email,
        company=body.company,
        source=body.source,
        urgency=body.urgency,
        intent=body.intent,
        pain_point=body.pain_point,
        summary=body.summary,
        recommended_next_action=body.recommended_next_action,
        status=body.status,
    )
    session.commit()
    return LeadResponse.model_validate(lead)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: str,
    principal: CurrentPrincipal,
    session: DBSession,
) -> LeadResponse:
    require_member(principal)
    lead = lead_service.get_lead(session, principal=principal, lead_id=lead_id)
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: str,
    body: LeadUpdate,
    principal: CurrentPrincipal,
    session: DBSession,
) -> LeadResponse:
    require_member(principal)
    lead = lead_service.update_lead(
        session,
        principal=principal,
        lead_id=lead_id,
        data=body.model_dump(exclude_unset=True),
    )
    session.commit()
    return LeadResponse.model_validate(lead)
