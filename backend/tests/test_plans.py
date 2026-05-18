"""Tests for plan listing and current plan retrieval."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register_user(client: TestClient, suffix: str = "") -> dict:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"plan_user{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Plan User",
            "organization_name": f"PlanOrg{suffix}",
        },
    )
    return resp.json()


EXPECTED_CODES = {"free", "pro", "team", "business"}


class TestListPlans:
    def test_list_plans(self, client: TestClient):
        resp = client.get("/plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert len(plans) == 4

    def test_plan_shape(self, client: TestClient):
        resp = client.get("/plans")
        plans = resp.json()
        for plan in plans:
            assert "code" in plan
            assert "name" in plan
            assert "monthly_price_cents" in plan
            assert "limits" in plan

    def test_plan_codes(self, client: TestClient):
        resp = client.get("/plans")
        plans = resp.json()
        codes = {p["code"] for p in plans}
        assert codes == EXPECTED_CODES

    def test_plan_limits_shape(self, client: TestClient):
        resp = client.get("/plans")
        plans = resp.json()
        expected_limit_keys = {
            "chat_messages",
            "rag_queries",
            "document_uploads",
            "storage_mb",
            "email_drafts",
            "lead_workflows",
            "tool_calls",
            "users",
        }
        for plan in plans:
            assert set(plan["limits"].keys()) == expected_limit_keys


class TestCurrentPlan:
    def test_current_plan_after_register(self, client: TestClient):
        data = _register_user(client, suffix="_curplan")
        token = data["access_token"]
        resp = client.get("/plans/current", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["plan"]["code"] == "free"
        assert body["subscription"]["status"] == "active"
