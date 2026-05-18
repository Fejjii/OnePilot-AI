from __future__ import annotations

from fastapi import APIRouter, Query

from onepilot.api.deps import CurrentPrincipal, DBSession
from onepilot.schemas.billing import (
    BillingPlansResponse,
    BillingSummaryResponse,
    BillingUsageResponse,
    InvoicePreviewResponse,
)
from onepilot.services import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/summary", response_model=BillingSummaryResponse)
def get_billing_summary(
    principal: CurrentPrincipal,
    session: DBSession,
) -> dict:
    return billing_service.get_billing_summary(session, principal.organization_id)


@router.get("/usage", response_model=BillingUsageResponse)
def get_billing_usage(
    principal: CurrentPrincipal,
    session: DBSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    return billing_service.get_billing_usage(
        session,
        principal.organization_id,
        offset=offset,
        limit=limit,
    )


@router.get("/invoice-preview", response_model=InvoicePreviewResponse)
def get_invoice_preview(
    principal: CurrentPrincipal,
    session: DBSession,
) -> dict:
    preview = billing_service.get_invoice_preview(session, principal.organization_id)
    preview.pop("stripe_preview", None)
    return preview


@router.get("/plans", response_model=BillingPlansResponse)
def get_billing_plans(
    principal: CurrentPrincipal,
    session: DBSession,
) -> dict:
    return billing_service.list_billing_plans(session, principal.organization_id)
