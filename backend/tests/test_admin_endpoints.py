"""Tests for admin endpoints: audit logs and usage events."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _register(client: TestClient, *, suffix: str) -> str:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"admin{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Admin User",
            "organization_name": f"AdminOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAdminAudit:
    def test_audit_logs_listed_for_admin(self, client: TestClient) -> None:
        token = _register(client, suffix="_audit")
        # Generate audit entries.
        client.post(
            "/documents/upload",
            files={"file": ("a.md", io.BytesIO(b"# A\n\nHello world."), "text/markdown")},
            headers=_h(token),
        )
        resp = client.get("/admin/audit-logs", headers=_h(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1
        actions = {item["action"] for item in body["items"]}
        assert "document.uploaded" in actions

    def test_audit_logs_filtered_by_action(self, client: TestClient) -> None:
        token = _register(client, suffix="_audit_filter")
        client.post(
            "/documents/upload",
            files={"file": ("b.md", io.BytesIO(b"# B\n\nText"), "text/markdown")},
            headers=_h(token),
        )
        resp = client.get(
            "/admin/audit-logs?action=document.uploaded",
            headers=_h(token),
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["action"] == "document.uploaded"


class TestAdminUsageEvents:
    def test_usage_events_listed(self, client: TestClient) -> None:
        token = _register(client, suffix="_usage")
        client.post(
            "/documents/upload",
            files={"file": ("c.md", io.BytesIO(b"# C\n\nText"), "text/markdown")},
            headers=_h(token),
        )
        resp = client.get("/admin/usage-events", headers=_h(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        features = {item["feature"] for item in body["items"]}
        assert "document_uploads" in features


class TestAdminPermissions:
    def test_member_cannot_access_admin(
        self, client_with_session: tuple[TestClient, Session]
    ) -> None:
        client, session = client_with_session
        owner_token = _register(client, suffix="_perm_aud")
        # Create a member in the same org and call as them.
        from jose import jwt as jose_jwt

        from onepilot.core.constants import Role
        from onepilot.core.ids import new_id
        from onepilot.repositories.models import OrganizationMember, User
        from onepilot.security.auth import create_access_token, hash_password

        org_id = jose_jwt.get_unverified_claims(owner_token)["org"]
        member = User(
            id=new_id("usr"),
            email="member_admin@example.com",
            hashed_password=hash_password("strongpass123"),
            full_name="Member",
        )
        session.add(member)
        session.add(
            OrganizationMember(
                id=new_id("mem"),
                organization_id=org_id,
                user_id=member.id,
                role=Role.MEMBER,
            )
        )
        session.commit()

        member_token, _ = create_access_token(
            user_id=member.id,
            organization_id=org_id,
            role=Role.MEMBER,
            plan_code="free",
        )
        resp = client.get(
            "/admin/audit-logs",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403
