"""Public-demo approval hygiene (OP-034).

The shared public-demo Approvals inbox must drop stale demo-visitor residue
without exposing a public DELETE route or touching other organizations.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.ids import new_id
from onepilot.demo_data.seed import (
    CURATED_DEMO_APPROVALS,
    SEEDED_APPROVAL_REASON,
    STALE_PUBLIC_DEMO_APPROVAL_RETENTION,
    cleanup_stale_public_demo_approvals,
    create_demo_visitor_principal,
    ensure_curated_demo_approvals,
    ensure_demo_principal,
    is_demo_visitor_user_id,
)
from onepilot.repositories.approvals import ApprovalRequestRepository
from onepilot.repositories.models import ApprovalRequest, Organization, Subscription
from onepilot.security.auth import Principal


def _settings(*, enabled: bool = True) -> Settings:
    return Settings(
        APP_ENV="test",
        PUBLIC_DEMO_ENABLED=enabled,
        DEV_ORG_ID="org_demo_onepilot",
        DEV_USER_ID="usr_demo_admin",
    )


def _other_org(session: Session) -> Principal:
    org_id = new_id("org")
    session.add(Organization(id=org_id, name="OtherOrg", slug=f"other-{org_id[:8]}"))
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


def _add_approval(
    session: Session,
    *,
    organization_id: str,
    created_by: str,
    title: str,
    payload: dict | None = None,
    reason: str = "Agent proposed gated action",
    action_type: str = "send_email",
    hours_ago: float | None = None,
) -> ApprovalRequest:
    row = ApprovalRequest(
        id=new_id("apv"),
        organization_id=organization_id,
        action_type=action_type,
        title=title,
        description="test approval",
        proposed_payload=payload if payload is not None else {"to": "reviewer@example.com"},
        risk_level="medium",
        status="pending",
        reason=reason,
        created_by=created_by,
    )
    session.add(row)
    session.flush()
    if hours_ago is not None:
        row.created_at = datetime.now(UTC) - timedelta(hours=hours_ago)
        session.flush()
    return row


def _titles(session: Session, organization_id: str) -> set[str]:
    rows = ApprovalRequestRepository(session).list_for_org(organization_id, limit=200)
    return {row.title for row in rows}


def _canonical_titles() -> set[str]:
    return {item["title"][:255] for item in CURATED_DEMO_APPROVALS}


def test_stale_retention_is_six_hours() -> None:
    assert STALE_PUBLIC_DEMO_APPROVAL_RETENTION == timedelta(hours=6)


def test_visitor_id_convention_excludes_demo_owner() -> None:
    settings = _settings()
    visitor = new_id("usr_demo")
    assert is_demo_visitor_user_id(visitor, settings=settings)
    assert not is_demo_visitor_user_id(settings.DEV_USER_ID, settings=settings)
    assert not is_demo_visitor_user_id(new_id("usr"), settings=settings)


def test_cleanup_disabled_outside_public_demo_enabled(db_session: Session) -> None:
    settings = _settings(enabled=False)
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    leftover = _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Stale leftover draft",
        hours_ago=24,
    )

    removed = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert removed == 0
    assert leftover.id in {
        row.id
        for row in ApprovalRequestRepository(db_session).list_for_org(
            owner.organization_id, limit=50
        )
    }


def test_cleanup_preserves_canonical_curated_approvals(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    curated_payload = {
        "curated": True,
        "to": "sarah.chen@brightline.io",
        "subject": "x",
        "body": "y",
    }
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Send follow-up email to Brightline Analytics",
        payload=curated_payload,
        reason=SEEDED_APPROVAL_REASON,
        hours_ago=48,
    )
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Visitor curated flag only",
        payload={"curated": True, "to": "priya.nair@atlashealth.org"},
        reason="Agent proposed gated action",
        hours_ago=48,
    )

    removed = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert removed == 0
    titles = _titles(db_session, owner.organization_id)
    assert "Send follow-up email to Brightline Analytics" in titles
    assert "Visitor curated flag only" in titles


def test_cleanup_preserves_recent_non_curated_demo_approvals(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    recent = _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Active session draft",
        hours_ago=1,
    )

    removed = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert removed == 0
    assert recent.title in _titles(db_session, owner.organization_id)


def test_cleanup_removes_stale_non_curated_demo_visitor_approvals(
    db_session: Session,
) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    stale = _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Yesterday leftover draft",
        hours_ago=12,
    )

    removed = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert removed == 1
    assert stale.title not in _titles(db_session, owner.organization_id)


def test_cleanup_leaves_other_organization_untouched(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    other = _other_org(db_session)
    foreign_visitor_id = new_id("usr_demo")
    foreign = _add_approval(
        db_session,
        organization_id=other.organization_id,
        created_by=foreign_visitor_id,
        title="Other org leftover",
        hours_ago=24,
    )

    removed = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert removed == 0
    assert foreign.id in {
        row.id
        for row in ApprovalRequestRepository(db_session).list_for_org(
            other.organization_id, limit=50
        )
    }


def test_cleanup_leaves_non_demo_user_approvals_untouched(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=settings.DEV_USER_ID,
        title="Demo owner leftover",
        hours_ago=24,
    )
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=new_id("usr"),
        title="Regular user leftover",
        hours_ago=24,
    )

    removed = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert removed == 0
    titles = _titles(db_session, owner.organization_id)
    assert "Demo owner leftover" in titles
    assert "Regular user leftover" in titles


def test_cleanup_is_idempotent(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Stale leftover draft",
        hours_ago=9,
    )

    first = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    second = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert first == 1
    assert second == 0
    assert "Stale leftover draft" not in _titles(db_session, owner.organization_id)


def test_cleanup_noops_when_principal_is_not_public_demo_org(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Should remain without demo principal",
        hours_ago=24,
    )
    other = _other_org(db_session)

    removed = cleanup_stale_public_demo_approvals(
        db_session, principal=other, settings=settings
    )
    assert removed == 0
    assert "Should remain without demo principal" in _titles(
        db_session, owner.organization_id
    )


def test_delete_ids_for_org_never_crosses_tenants(db_session: Session) -> None:
    demo = ensure_demo_principal(db_session, settings=_settings())
    other = _other_org(db_session)
    demo_row = _add_approval(
        db_session,
        organization_id=demo.organization_id,
        created_by=demo.user_id,
        title="Demo row",
    )
    other_row = _add_approval(
        db_session,
        organization_id=other.organization_id,
        created_by=other.user_id,
        title="Other row",
    )
    repo = ApprovalRequestRepository(db_session)
    removed = repo.delete_ids_for_org(demo.organization_id, [demo_row.id, other_row.id])
    assert removed == 1
    assert other_row.title in _titles(db_session, other.organization_id)
    assert demo_row.title not in _titles(db_session, demo.organization_id)


def test_old_placeholder_incomplete_residue_is_removed(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Old placeholder Gmail draft",
        payload={"to": "", "subject": "gmail_draft", "body": ""},
        hours_ago=30,
    )
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="OnePilot scheduled meeting",
        action_type="schedule_meeting",
        payload={
            "summary": "OnePilot scheduled meeting",
            "start_time": "",
            "end_time": "",
            "attendees": [],
        },
        hours_ago=30,
    )

    removed = cleanup_stale_public_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert removed == 2
    titles = _titles(db_session, owner.organization_id)
    assert "Old placeholder Gmail draft" not in titles
    assert "OnePilot scheduled meeting" not in titles


def test_curated_refresh_still_yields_canonical_set(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Old placeholder Gmail draft",
        payload={"to": "", "subject": "gmail_draft", "body": ""},
        hours_ago=20,
    )
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Active recruiter draft",
        hours_ago=1,
    )

    created = ensure_curated_demo_approvals(
        db_session, principal=owner, settings=settings
    )
    assert created == len(CURATED_DEMO_APPROVALS)
    titles = _titles(db_session, owner.organization_id)
    assert _canonical_titles() <= titles
    assert "Old placeholder Gmail draft" not in titles
    assert "Active recruiter draft" in titles
    leftover_titles = titles - _canonical_titles()
    assert leftover_titles == {"Active recruiter draft"}


def test_active_recruiter_approval_survives_retention_window(db_session: Session) -> None:
    settings = _settings()
    owner = ensure_demo_principal(db_session, settings=settings)
    visitor = create_demo_visitor_principal(db_session, settings=settings)
    _add_approval(
        db_session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Live recruiter follow-up",
        payload={
            "to": "sarah.chen@brightline.io",
            "subject": "Next steps",
            "body": "Grounded follow-up from this session.",
        },
        hours_ago=2,
    )

    ensure_curated_demo_approvals(db_session, principal=owner, settings=settings)
    assert "Live recruiter follow-up" in _titles(db_session, owner.organization_id)


def test_demo_start_invokes_hygiene(
    client_with_session: tuple[TestClient, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PUBLIC_DEMO_ENABLED", "true")
    get_settings.cache_clear()
    client, session = client_with_session
    settings = get_settings()
    assert settings.PUBLIC_DEMO_ENABLED is True

    owner = ensure_demo_principal(session, settings=settings)
    visitor = create_demo_visitor_principal(session, settings=settings)
    _add_approval(
        session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Old leftover Gmail draft",
        payload={"to": "", "subject": "gmail_draft", "body": ""},
        hours_ago=18,
    )
    _add_approval(
        session,
        organization_id=owner.organization_id,
        created_by=visitor.user_id,
        title="Active recruiter email",
        hours_ago=1,
    )

    resp = client.post("/demo/start")
    assert resp.status_code == 200, resp.text

    titles = _titles(session, owner.organization_id)
    assert "Old leftover Gmail draft" not in titles
    assert "Active recruiter email" in titles
    assert _canonical_titles() <= titles
