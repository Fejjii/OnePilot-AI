"""Tests for organization endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from onepilot.core.constants import PlanCode, Role
from onepilot.security.auth import create_access_token


def _register_user(client: TestClient, suffix: str = "") -> dict:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"orguser{suffix}@example.com",
            "password": "strongpass123",
            "full_name": f"OrgUser {suffix}",
            "organization_name": f"OrgTest{suffix}",
        },
    )
    assert resp.status_code == 200
    return resp.json()


class TestGetOrganization:
    def test_get_current_organization(self, client: TestClient):
        data = _register_user(client, suffix="_getorg")
        token = data["access_token"]
        resp = client.get(
            "/organizations/current",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert body["name"] == "OrgTest_getorg"
        assert "slug" in body


class TestListMembers:
    def test_list_members(self, client: TestClient):
        data = _register_user(client, suffix="_listmem")
        token = data["access_token"]
        resp = client.get(
            "/organizations/current/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        members = resp.json()
        assert len(members) == 1
        assert members[0]["role"] == Role.OWNER

    def test_list_members_forbidden_as_member(self, client: TestClient, db_session):
        data = _register_user(client, suffix="_listforbid")
        from onepilot.security.auth import decode_access_token

        principal = decode_access_token(data["access_token"])
        member_token, _ = create_access_token(
            user_id=principal.user_id,
            organization_id=principal.organization_id,
            role=Role.MEMBER,
            plan_code=PlanCode.FREE,
        )
        resp = client.get(
            "/organizations/current/members",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403


class TestAddMember:
    def test_add_member_as_owner(self, client: TestClient):
        owner_data = _register_user(client, suffix="_addowner")
        owner_token = owner_data["access_token"]

        second_resp = client.post(
            "/auth/register",
            json={
                "email": "second_user_add@example.com",
                "password": "strongpass123",
                "full_name": "Second User",
                "organization_name": "SecondOrg",
            },
        )
        assert second_resp.status_code == 200

        resp = client.post(
            "/organizations/current/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"email": "second_user_add@example.com", "role": "member"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "second_user_add@example.com"
        assert body["role"] == Role.MEMBER

    def test_add_member_forbidden_as_member(self, client: TestClient):
        data = _register_user(client, suffix="_addforbid")
        from onepilot.security.auth import decode_access_token

        principal = decode_access_token(data["access_token"])
        member_token, _ = create_access_token(
            user_id=principal.user_id,
            organization_id=principal.organization_id,
            role=Role.MEMBER,
            plan_code=PlanCode.FREE,
        )
        resp = client.post(
            "/organizations/current/members",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"email": "someone@example.com", "role": "member"},
        )
        assert resp.status_code == 403
