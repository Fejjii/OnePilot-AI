"""Demo seeding and public demo-access endpoints.

POST /demo/setup  — dev-only: upsert the deterministic demo org + user and
                   return a bearer token.  The seed script calls this so it
                   always operates on the same org that DEV_AUTH_ENABLED uses.

POST /demo/seed   — seed NovaEdge knowledge-base docs into the caller's org.
                   Also accessible as /demo/seed_current_org for the UI.

POST /demo/start  — one-click public demo entry (OP-006). Only available when
                   PUBLIC_DEMO_ENABLED=true. Idempotently seeds the demo org
                   and returns a short-lived bearer token, so reviewers never
                   need credentials. Rate limited per client IP.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from onepilot.api.deps import CurrentPrincipal, DBSession, SettingsDep
from onepilot.core.logging import get_logger
from onepilot.demo_data import seed as seed_module
from onepilot.security.auth import create_access_token
from onepilot.security.permissions import require_admin
from onepilot.security.rate_limit import (
    FEATURE_DEMO_START,
    enforce_rate_limit_for_client,
)

logger = get_logger(__name__)

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


class DemoStartResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    organization_name: str
    demo_mode: bool = True
    simulated_providers: bool = True


# ── Helpers ────────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/start", response_model=DemoStartResponse)
def start_public_demo(
    request: Request,
    session: DBSession,
    settings: SettingsDep,
) -> DemoStartResponse:
    """One-click public demo entry (OP-006).

    Gated by PUBLIC_DEMO_ENABLED so there is no unauthenticated token minting
    outside explicit public-demo mode. Idempotently seeds the demo org
    (knowledge base + operational data) and returns a short-lived token
    scoped to that single shared tenant. No password is exposed or required.
    """
    if not settings.PUBLIC_DEMO_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="The public demo is not enabled on this server.",
        )

    enforce_rate_limit_for_client(
        f"demo_start:{_client_ip(request)}",
        FEATURE_DEMO_START,
    )

    principal = seed_module.ensure_demo_principal(session, settings=settings)

    try:
        seed_module.seed_knowledge_base(session, principal=principal, settings=settings)
        seed_module.seed_operational_data(session, principal=principal)
        # Always refresh seeded approvals to curated NovaEdge copy so the shared
        # public-demo org never serves leftover Faker/lorem titles (launch UX).
        seed_module.ensure_curated_demo_approvals(session, principal=principal)
    except Exception:
        # Never leak seeding internals to an unauthenticated caller.
        logger.exception("demo_start_seed_failed")
        raise HTTPException(
            status_code=503,
            detail="Demo workspace could not be prepared. Please try again shortly.",
        ) from None

    # Shared demo tenant: wipe prior visitors' user/agent memories so nothing
    # leaks across unrelated public-demo sessions (OP-012). Never roll back the
    # seeded workspace if clearing fails.
    try:
        from onepilot.services import memory_service

        deleted = memory_service.clear_user_memory(session, principal=principal)
        session.commit()
        logger.info(
            "demo_start_memory_cleared",
            organization_id=principal.organization_id,
            deleted_count=deleted,
        )
    except Exception:
        logger.exception("demo_start_memory_clear_failed")

    token, expires_at = create_access_token(
        user_id=principal.user_id,
        organization_id=principal.organization_id,
        role=principal.role,
        plan_code=principal.plan_code,
        expires_delta=timedelta(minutes=settings.PUBLIC_DEMO_SESSION_MINUTES),
    )
    logger.info(
        "demo_start_session_issued",
        organization_id=principal.organization_id,
        expires_at=expires_at.isoformat(),
    )
    return DemoStartResponse(
        access_token=token,
        expires_at=expires_at.isoformat(),
        organization_name=seed_module.DEMO_ORG_NAME,
    )


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
    # Refresh seeded approvals even when operational seed was skipped (idempotent
    # lead short-circuit). Keeps the shared demo inbox recruiter-ready.
    approvals_refreshed = seed_module.ensure_curated_demo_approvals(
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
        approvals_created=max(operational.approvals_created, approvals_refreshed),
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
