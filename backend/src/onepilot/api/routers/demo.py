"""Demo seeding endpoints.

POST /demo/setup  — dev-only: upsert the deterministic demo org + user and
                   return a bearer token.  The seed script calls this so it
                   always operates on the same org that DEV_AUTH_ENABLED uses.

POST /demo/seed   — seed NovaEdge knowledge-base docs into the caller's org.
                   Also accessible as /demo/seed_current_org for the UI.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from onepilot.api.deps import CurrentPrincipal, DBSession, SettingsDep
from onepilot.demo_data import seed as seed_module
from onepilot.security.auth import create_access_token
from onepilot.security.permissions import require_admin

router = APIRouter(prefix="/demo", tags=["demo"])


# ── Response models ────────────────────────────────────────────────────────────

class SetupResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    organization_id: str
    organization_name: str


class SeedResponse(BaseModel):
    documents_created: int
    documents_skipped: int
    total_documents: int
    total_chunks: int
    vector_upsert_count: int
    leads_created: int = 0
    approvals_created: int = 0
    usage_events_created: int = 0
    audit_logs_created: int = 0
    operational_skipped: bool = False


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/setup", response_model=SetupResponse)
def setup_demo(session: DBSession, settings: SettingsDep) -> SetupResponse:
    """Upsert the deterministic demo org/user and return a bearer token.

    Only available when APP_ENV=dev.  The seed script calls this endpoint so
    the org it seeds into is always the same org that DEV_AUTH_ENABLED uses.
    """
    if not (settings.is_dev or settings.is_test):
        raise HTTPException(status_code=403, detail="Only available in dev/test environment")

    principal = seed_module.ensure_demo_principal(session, settings=settings)

    token, expires_at = create_access_token(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        role=principal.role,
        plan_code=principal.plan_code,
    )
    return SetupResponse(
        access_token=token,
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        organization_name=seed_module.DEMO_ORG_NAME,
    )


def _seed_response(
    session: DBSession,
    *,
    principal: CurrentPrincipal,
    settings: SettingsDep,
) -> SeedResponse:
    result = seed_module.seed_knowledge_base(
        session,
        principal=principal,
        settings=settings,
    )
    operational = seed_module.seed_operational_data(
        session,
        principal=principal,
    )
    return SeedResponse(
        documents_created=result.documents_created,
        documents_skipped=result.documents_skipped,
        total_documents=result.total_documents,
        total_chunks=result.total_chunks,
        vector_upsert_count=result.vector_upsert_count,
        leads_created=operational.leads_created,
        approvals_created=operational.approvals_created,
        usage_events_created=operational.usage_events_created,
        audit_logs_created=operational.audit_logs_created,
        operational_skipped=operational.skipped,
    )


@router.post("/seed_current_org", response_model=SeedResponse)
def seed_current_organization_demo(
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> SeedResponse:
    """Seed knowledge base using the configured embeddings provider.
    
    Uses OpenAI embeddings when OPENAI_API_KEY is set, otherwise falls back
    to deterministic embeddings. Automatically reindexes if provider changed.
    Also seeds operational demo data (leads, approvals, usage, audit) when empty.
    """
    require_admin(principal)
    return _seed_response(session, principal=principal, settings=settings)


@router.post("/seed", response_model=SeedResponse)
def seed_demo(
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> SeedResponse:
    """Seed knowledge base using the configured embeddings provider.
    
    Uses OpenAI embeddings when OPENAI_API_KEY is set, otherwise falls back
    to deterministic embeddings. Automatically reindexes if provider changed.
    Also seeds operational demo data (leads, approvals, usage, audit) when empty.
    """
    require_admin(principal)
    return _seed_response(session, principal=principal, settings=settings)
