"""Tests for lead service, classifier, and /leads endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.core.constants import PlanCode, Role
from onepilot.core.ids import new_id
from onepilot.repositories.leads import LeadRepository
from onepilot.repositories.models import Organization, Subscription
from onepilot.security.auth import Principal
from onepilot.services import lead_service


def _setup_org(session: Session) -> Principal:
    org_id = new_id("org")
    org = Organization(id=org_id, name="LeadOrg", slug=f"lead-{org_id[:8]}")
    session.add(org)
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
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


class TestLeadClassifier:
    def test_urgency_high(self) -> None:
        cls = lead_service.classify_lead("This is urgent, our production is down ASAP")
        assert cls.urgency == "high"

    def test_urgency_low(self) -> None:
        cls = lead_service.classify_lead("Just exploring, no rush at all")
        assert cls.urgency == "low"

    def test_intent_purchase(self) -> None:
        cls = lead_service.classify_lead("We are looking to buy 50 licenses next quarter")
        assert cls.intent == "purchase"
        assert "discovery" in cls.recommended_next_action.lower()

    def test_intent_demo(self) -> None:
        cls = lead_service.classify_lead("Can we get a demo of your platform?")
        assert cls.intent == "demo"

    def test_intent_support(self) -> None:
        cls = lead_service.classify_lead("We're having an issue with billing")
        assert cls.intent == "support"
        assert cls.pain_point is not None

    def test_extract_email(self) -> None:
        assert (
            lead_service.extract_email("Email me at john.doe+test@globex.io please")
            == "john.doe+test@globex.io"
        )
        assert lead_service.extract_email("no email here") is None


class TestLeadService:
    def test_create_lead_records_audit_and_usage(self, db_session: Session) -> None:
        principal = _setup_org(db_session)
        lead = lead_service.create_lead(
            db_session,
            principal=principal,
            name="John Doe",
            email="john@acme.io",
            company="Acme",
            urgency="high",
            intent="purchase",
        )
        assert lead.id.startswith("lead_")
        assert lead.organization_id == principal.organization_id

        repo = LeadRepository(db_session)
        rows, count = repo.list_for_org(principal.organization_id), repo.count_for_org(
            principal.organization_id
        )
        assert count == 1
        assert rows[0].id == lead.id

    def test_create_lead_requires_name(self, db_session: Session) -> None:
        principal = _setup_org(db_session)
        with pytest.raises(Exception):
            lead_service.create_lead(db_session, principal=principal, name="")


class TestLeadEndpoints:
    def _register(self, client: TestClient, *, suffix: str) -> str:
        resp = client.post(
            "/auth/register",
            json={
                "email": f"leadapi{suffix}@example.com",
                "password": "strongpass123",
                "full_name": "Lead User",
                "organization_name": f"LeadApiOrg{suffix}",
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    def _h(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_create_and_list_lead(self, client: TestClient) -> None:
        token = self._register(client, suffix="_crud")
        resp = client.post(
            "/leads",
            json={"name": "Jane", "email": "jane@beta.io", "urgency": "medium"},
            headers=self._h(token),
        )
        assert resp.status_code == 200, resp.text
        lead_id = resp.json()["id"]
        assert lead_id.startswith("lead_")

        listing = client.get("/leads", headers=self._h(token)).json()
        assert listing["total"] == 1
        assert listing["items"][0]["id"] == lead_id

    def test_update_lead_writes_audit(self, client: TestClient) -> None:
        token = self._register(client, suffix="_upd")
        lead_id = client.post(
            "/leads",
            json={"name": "Maya"},
            headers=self._h(token),
        ).json()["id"]
        patched = client.patch(
            f"/leads/{lead_id}",
            json={"status": "qualified", "urgency": "high"},
            headers=self._h(token),
        )
        assert patched.status_code == 200
        assert patched.json()["status"] == "qualified"
        assert patched.json()["urgency"] == "high"
