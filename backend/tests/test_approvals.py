"""Tests for approval service and /approvals endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.core.constants import ApprovalStatus, PlanCode, Role
from onepilot.core.errors import PermissionDeniedError, ValidationError
from onepilot.core.ids import new_id
from onepilot.repositories.models import Organization, Subscription
from onepilot.security.auth import Principal
from onepilot.services import approval_service


def _setup_principal(session: Session, *, role: Role = Role.OWNER) -> Principal:
    org_id = new_id("org")
    session.add(Organization(id=org_id, name="ApvOrg", slug=f"apv-{org_id[:8]}"))
    session.add(
        Subscription(
            id=new_id("sub"),
            organization_id=org_id,
            plan_code=PlanCode.FREE,
            status="active",
        )
    )
    session.flush()
    return Principal(
        user_id="usr_test",
        organization_id=org_id,
        role=role,
        plan_code=PlanCode.FREE,
    )


class TestApprovalService:
    def test_requires_approval_set(self) -> None:
        assert approval_service.requires_approval("send_email")
        assert approval_service.requires_approval("update_crm")
        assert not approval_service.requires_approval("rag_search")

    def test_create_pending(self, db_session: Session) -> None:
        principal = _setup_principal(db_session)
        apv = approval_service.create(
            db_session,
            principal=principal,
            action_type="send_email",
            title="Send pricing email to Bob",
            proposed_payload={"to": "bob@acme.io"},
            risk_level="medium",
        )
        assert apv.status == ApprovalStatus.PENDING.value
        assert apv.organization_id == principal.organization_id

    def test_invalid_risk_rejected(self, db_session: Session) -> None:
        principal = _setup_principal(db_session)
        with pytest.raises(ValidationError):
            approval_service.create(
                db_session,
                principal=principal,
                action_type="send_email",
                title="x",
                risk_level="extreme",
            )

    def test_decide_requires_owner_or_admin(self, db_session: Session) -> None:
        principal = _setup_principal(db_session, role=Role.MEMBER)
        apv = approval_service.create(
            db_session,
            principal=Principal(
                user_id="usr_owner",
                organization_id=principal.organization_id,
                role=Role.OWNER,
                plan_code=PlanCode.FREE,
            ),
            action_type="send_email",
            title="t",
        )
        with pytest.raises(PermissionDeniedError):
            approval_service.decide(
                db_session,
                principal=principal,
                approval_id=apv.id,
                status=ApprovalStatus.APPROVED,
            )

    def test_decide_owner_succeeds_and_records_audit(
        self, db_session: Session
    ) -> None:
        principal = _setup_principal(db_session)
        apv = approval_service.create(
            db_session,
            principal=principal,
            action_type="send_email",
            title="t",
        )
        decided = approval_service.decide(
            db_session,
            principal=principal,
            approval_id=apv.id,
            status=ApprovalStatus.APPROVED,
            reason="ok",
        )
        assert decided.status == ApprovalStatus.APPROVED.value
        assert decided.reviewed_by == principal.user_id
        assert decided.reason == "ok"

    def test_cannot_decide_twice(self, db_session: Session) -> None:
        principal = _setup_principal(db_session)
        apv = approval_service.create(
            db_session, principal=principal, action_type="send_email", title="t"
        )
        approval_service.decide(
            db_session,
            principal=principal,
            approval_id=apv.id,
            status=ApprovalStatus.APPROVED,
        )
        with pytest.raises(ValidationError):
            approval_service.decide(
                db_session,
                principal=principal,
                approval_id=apv.id,
                status=ApprovalStatus.REJECTED,
            )


class TestApprovalEndpoints:
    def _register(
        self, client: TestClient, *, suffix: str
    ) -> str:
        resp = client.post(
            "/auth/register",
            json={
                "email": f"apv{suffix}@example.com",
                "password": "strongpass123",
                "full_name": "Apv User",
                "organization_name": f"ApvOrg{suffix}",
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    def _h(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_list_pending_and_decide(self, client: TestClient) -> None:
        token = self._register(client, suffix="_flow")
        # Generate an approval via the chat agent (send_email branch).
        chat = client.post(
            "/chat",
            json={
                "message": "Draft and send an email to Bob about pricing.",
                "context": {"action": "send"},
            },
            headers=self._h(token),
        )
        approval_id = chat.json()["approval_id"]
        assert approval_id

        listing = client.get("/approvals?status=pending", headers=self._h(token)).json()
        assert listing["pending_count"] >= 1
        assert any(a["id"] == approval_id for a in listing["items"])

        decision = client.post(
            f"/approvals/{approval_id}/decision",
            json={"status": "approved", "reason": "fine"},
            headers=self._h(token),
        )
        assert decision.status_code == 200, decision.text
        assert decision.json()["status"] == "approved"

    def test_member_cannot_decide(
        self,
        client_with_session: tuple[TestClient, Session],
    ) -> None:
        client, session = client_with_session
        # Register an org/owner.
        owner_token = self._register(client, suffix="_perm_owner")
        chat = client.post(
            "/chat",
            json={
                "message": "Draft and send an email to Bob about renewal.",
                "context": {"action": "send"},
            },
            headers=self._h(owner_token),
        )
        approval_id = chat.json()["approval_id"]
        assert approval_id

        # Create a member user inside the same org and authenticate.
        from jose import jwt as jose_jwt

        from onepilot.core.constants import Role
        from onepilot.core.ids import new_id
        from onepilot.repositories.models import OrganizationMember, User
        from onepilot.security.auth import create_access_token, hash_password

        org_id = jose_jwt.get_unverified_claims(owner_token)["org"]
        member_user = User(
            id=new_id("usr"),
            email=f"member{approval_id[-4:]}@example.com",
            hashed_password=hash_password("strongpass123"),
            full_name="Member",
        )
        session.add(member_user)
        session.add(
            OrganizationMember(
                id=new_id("mem"),
                organization_id=org_id,
                user_id=member_user.id,
                role=Role.MEMBER,
            )
        )
        session.commit()

        member_token, _ = create_access_token(
            user_id=member_user.id,
            organization_id=org_id,
            role=Role.MEMBER,
            plan_code="free",
        )
        decision = client.post(
            f"/approvals/{approval_id}/decision",
            json={"status": "approved"},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert decision.status_code == 403
