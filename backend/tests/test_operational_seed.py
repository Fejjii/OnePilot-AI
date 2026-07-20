"""Tests for operational demo data seeding."""

from __future__ import annotations

from sqlalchemy.orm import Session

from onepilot.core.config import get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.ids import new_id
from onepilot.demo_data.seed import (
    CURATED_DEMO_APPROVALS,
    SEEDED_APPROVAL_REASON,
    ensure_curated_demo_approvals,
    ensure_demo_principal,
    seed_operational_data,
)
from onepilot.repositories.approvals import ApprovalRequestRepository
from onepilot.repositories.leads import LeadRepository
from onepilot.repositories.models import ApprovalRequest, Organization, Subscription
from onepilot.repositories.usage_events import UsageEventRepository
from onepilot.security.auth import Principal


def _setup_org(session: Session) -> Principal:
    org_id = new_id("org")
    org = Organization(id=org_id, name="SeedOrg", slug=f"seed-{org_id[:8]}")
    session.add(org)
    session.add(
        Subscription(
            id=new_id("sub"),
            organization_id=org_id,
            plan_code=PlanCode.BUSINESS,
            status="active",
        )
    )
    session.flush()
    return Principal(
        user_id=new_id("usr"),
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.BUSINESS,
    )


def test_operational_seed_creates_demo_records(db_session: Session) -> None:
    principal = _setup_org(db_session)
    result = seed_operational_data(db_session, principal=principal)

    assert result.skipped is False
    assert result.leads_created == 12
    assert result.approvals_created == 8
    assert result.usage_events_created == 40
    assert result.audit_logs_created == 25

    lead_repo = LeadRepository(db_session)
    approval_repo = ApprovalRequestRepository(db_session)
    usage_repo = UsageEventRepository(db_session)

    assert lead_repo.count_for_org(principal.organization_id) == 12
    assert approval_repo.count_pending(principal.organization_id) >= 1
    assert len(usage_repo.list_for_org(principal.organization_id, limit=50)) == 40


def test_operational_seed_is_idempotent(db_session: Session) -> None:
    principal = _setup_org(db_session)
    first = seed_operational_data(db_session, principal=principal)
    second = seed_operational_data(db_session, principal=principal)

    assert first.skipped is False
    assert second.skipped is True
    assert second.leads_created == 0


def test_demo_principal_uses_documented_credentials(db_session: Session) -> None:
    settings = get_settings()
    principal = ensure_demo_principal(db_session, settings=settings)
    assert principal.organization_id == settings.DEV_ORG_ID
    assert principal.user_id == settings.DEV_USER_ID


def test_operational_seed_uses_curated_approval_titles(db_session: Session) -> None:
    principal = _setup_org(db_session)
    seed_operational_data(db_session, principal=principal)
    approval_repo = ApprovalRequestRepository(db_session)
    titles = {
        row.title for row in approval_repo.list_for_org(principal.organization_id, limit=50)
    }
    assert "Send follow-up email to Brightline Analytics" in titles
    assert approval_repo.count_pending(principal.organization_id) >= 2
    # No Faker-style noise in curated titles
    assert not any("Possimus" in t or "Repellendus" in t for t in titles)


def test_ensure_curated_demo_approvals_replaces_seeded_rows(
    db_session: Session,
) -> None:
    principal = _setup_org(db_session)
    approval_repo = ApprovalRequestRepository(db_session)
    approval_repo.create(
        ApprovalRequest(
            id=new_id("apv"),
            organization_id=principal.organization_id,
            action_type="send_email",
            title="Skin name interview military mother purpose",
            description="faker leftover",
            proposed_payload={"demo": True},
            risk_level="high",
            status="pending",
            reason=SEEDED_APPROVAL_REASON,
            created_by=principal.user_id,
        )
    )
    # Legacy Faker row with demo payload but a different reason string
    approval_repo.create(
        ApprovalRequest(
            id=new_id("apv"),
            organization_id=principal.organization_id,
            action_type="send_email",
            title="Possimus repudiandae recusandae officia inventore dolorem.",
            description="legacy faker",
            proposed_payload={
                "demo": True,
                "original_action": "send_email_reply",
                "requester": "Ada",
            },
            risk_level="high",
            status="pending",
            reason="legacy seed",
            created_by=principal.user_id,
        )
    )
    # Agent-created approval must survive refresh
    approval_repo.create(
        ApprovalRequest(
            id=new_id("apv"),
            organization_id=principal.organization_id,
            action_type="send_email",
            title="Agent drafted customer email",
            description="created during chat",
            proposed_payload={"to": "customer@example.com"},
            risk_level="high",
            status="pending",
            reason="Agent proposed gated action",
            created_by=principal.user_id,
        )
    )

    created = ensure_curated_demo_approvals(db_session, principal=principal)
    assert created == len(CURATED_DEMO_APPROVALS)
    rows = approval_repo.list_for_org(principal.organization_id, limit=50)
    titles = {row.title for row in rows}
    assert "Skin name interview military mother purpose" not in titles
    assert "Possimus repudiandae recusandae officia inventore dolorem." not in titles
    assert "Send follow-up email to Brightline Analytics" in titles
    assert "Agent drafted customer email" in titles
