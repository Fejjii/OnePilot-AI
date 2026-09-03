"""OP-028: CRM-grounded email drafts and recruiter-facing approval copy."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.ids import new_id
from onepilot.providers import get_email_provider
from onepilot.providers.email.mock_email_provider import MockEmailProvider
from onepilot.providers.llm.base import LLMResponse
from onepilot.repositories.models import Organization, Subscription
from onepilot.schemas.gmail import EmailApprovalPayload
from onepilot.security.auth import Principal
from onepilot.services import email_service, gmail_service, lead_service
from onepilot.services.crm_email_grounding import (
    build_approval_copy,
    contains_placeholder_token,
    resolve_email_recipient,
    sanitize_draft_text,
    select_most_promising_lead,
)

STARTER_PROMPT = (
    "Draft a follow-up email to our most promising lead about scheduling an intro call."
)

_PLACEHOLDER_SAMPLES = (
    "[recipient]",
    "[relevant outcome]",
    "[Company]",
    "[Name]",
)


def _principal_for(org_id: str, user_id: str = "usr_crm") -> Principal:
    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.BUSINESS,
    )


def _setup_org(session: Session, *, suffix: str) -> Principal:
    org_id = new_id("org")
    session.add(Organization(id=org_id, name=f"CRM Org {suffix}", slug=f"crm-{suffix}"))
    session.add(
        Subscription(
            id=new_id("sub"),
            organization_id=org_id,
            plan_code=PlanCode.BUSINESS,
            status="active",
        )
    )
    session.flush()
    return _principal_for(org_id, user_id=f"usr_{suffix}")


def _seed_brightline(session: Session, principal: Principal) -> object:
    return lead_service.create_lead(
        session,
        principal=principal,
        name="Sarah Chen",
        company="Brightline Analytics",
        email="sarah.chen@brightline.io",
        source="demo_request",
        status="qualified",
        urgency="high",
        intent="demo",
        pain_point="Support team overwhelmed during product launches",
        summary="VP Operations exploring AI workspace for support automation.",
        recommended_next_action="Schedule discovery call and share Growth plan pricing.",
        enforce_quota=False,
    )


def _seed_northwind(session: Session, principal: Principal) -> object:
    return lead_service.create_lead(
        session,
        principal=principal,
        name="Marcus Webb",
        company="Northwind Legal",
        email="marcus.webb@northwindlegal.com",
        source="referral",
        status="new",
        urgency="low",
        intent="purchase",
        pain_point="Manual email triage for client intake",
        summary="Managing partner wants grounded answers from playbooks.",
        recommended_next_action="Send proposal for Business plan.",
        enforce_quota=False,
    )


def _register(client: TestClient, *, suffix: str) -> str:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"crm{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "CRM User",
            "organization_name": f"CRMOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_lead_via_api(client: TestClient, token: str, **fields: object) -> dict:
    resp = client.post("/leads", json=fields, headers=_auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


class _PlaceholderLLM:
    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        return LLMResponse(
            content=(
                "Subject: Hello [recipient]\n\n"
                "Hi [recipient],\n\n"
                "Following up on [relevant outcome] for [Company].\n"
            ),
            model="gpt-5-nano-2025-08-07",
            input_tokens=40,
            output_tokens=40,
            finish_reason="stop",
        )


class TestCrmLeadResolution:
    def test_most_promising_lead_uses_seeded_crm_record(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="promising")
        brightline = _seed_brightline(db_session, principal)
        _seed_northwind(db_session, principal)

        resolved = resolve_email_recipient(
            db_session,
            principal=principal,
            message=STARTER_PROMPT,
            context={},
        )

        assert resolved.match_reason == "most_promising"
        assert resolved.lead_id == brightline.id
        assert resolved.recipient_name == "Sarah Chen"
        assert resolved.recipient_email == "sarah.chen@brightline.io"
        assert resolved.company == "Brightline Analytics"
        assert resolved.facts["pain_point"].startswith("Support team overwhelmed")
        assert "lead_" not in (resolved.recipient_name or "")

    def test_name_and_company_mentions_resolve_the_matching_lead(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="mention")
        _seed_brightline(db_session, principal)
        northwind = _seed_northwind(db_session, principal)

        by_name = resolve_email_recipient(
            db_session,
            principal=principal,
            message="Draft an email to Sarah Chen about next steps.",
        )
        assert by_name.recipient_email == "sarah.chen@brightline.io"
        assert by_name.match_reason == "name"

        by_company = resolve_email_recipient(
            db_session,
            principal=principal,
            message="Write a follow-up email to Northwind about the proposal.",
        )
        assert by_company.lead_id == northwind.id
        assert by_company.company == "Northwind Legal"

    def test_missing_context_does_not_invent_a_lead(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="empty")
        resolved = resolve_email_recipient(
            db_session,
            principal=principal,
            message=STARTER_PROMPT,
        )
        assert resolved.lead_id is None
        assert resolved.facts == {}
        assert resolved.recipient_name is None
        assert resolved.match_reason == "none"

    def test_named_person_without_crm_row_has_no_fabricated_facts(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="bob")
        resolved = resolve_email_recipient(
            db_session,
            principal=principal,
            message="Draft and send an email to Bob thanking him for the demo.",
        )
        assert resolved.recipient_name == "Bob"
        assert resolved.recipient_email is None
        assert resolved.company is None
        assert resolved.facts == {}
        assert resolved.match_reason == "message_name"

    def test_tenant_isolation_ignores_other_org_leads(
        self, db_session: Session
    ) -> None:
        org_a = _setup_org(db_session, suffix="iso-a")
        org_b = _setup_org(db_session, suffix="iso-b")
        lead_a = _seed_brightline(db_session, org_a)

        resolved = resolve_email_recipient(
            db_session,
            principal=org_b,
            message="Draft an email to Sarah Chen at Brightline Analytics.",
            context={"lead_id": lead_a.id},
        )
        assert resolved.lead_id is None
        assert resolved.facts == {}
        assert resolved.recipient_email is None
        # Name may be extracted from the message, but no CRM company/email.
        assert "brightline.io" not in (resolved.recipient_email or "")


class TestEmailDraftGrounding:
    def test_fallback_draft_uses_crm_facts_and_no_placeholders(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="draft-crm")
        _seed_brightline(db_session, principal)
        resolved = resolve_email_recipient(
            db_session, principal=principal, message=STARTER_PROMPT
        )

        outcome = email_service.draft_email(
            db_session,
            principal=principal,
            context=STARTER_PROMPT,
            recipient_name=resolved.recipient_name,
            recipient_email=resolved.recipient_email,
            crm_facts=resolved.facts,
            settings=Settings(),
            enforce_quota=False,
        )

        body = outcome.draft.body
        subject = outcome.draft.subject
        assert "Sarah" in body
        assert "Brightline Analytics" in body
        assert "support team overwhelmed" in body.lower()
        assert "Schedule discovery call" in body
        assert "Northwind" not in body
        assert "$4" not in body
        assert outcome.draft.recipient_placeholder == "Sarah Chen"
        for token in _PLACEHOLDER_SAMPLES:
            assert token not in body
            assert token not in subject
        assert not contains_placeholder_token(body)
        assert not contains_placeholder_token(subject)

    def test_missing_crm_fallback_is_generic_and_honest(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="draft-empty")
        outcome = email_service.draft_email(
            db_session,
            principal=principal,
            context=STARTER_PROMPT,
            settings=Settings(),
            enforce_quota=False,
        )
        assert outcome.draft.body.startswith("Hello,")
        assert "Sarah Chen" not in outcome.draft.body
        assert "Brightline" not in outcome.draft.body
        assert outcome.draft.recipient_placeholder == ""
        for token in _PLACEHOLDER_SAMPLES:
            assert token not in outcome.draft.body
            assert token not in outcome.draft.subject

    def test_llm_placeholder_tokens_are_stripped(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="llm-ph")
        outcome = email_service.draft_email(
            db_session,
            principal=principal,
            context="Draft a thank-you email.",
            recipient_name="Alex Rivera",
            settings=Settings(),
            llm=_PlaceholderLLM(),  # type: ignore[arg-type]
            enforce_quota=False,
        )
        assert "Alex Rivera" in outcome.draft.body
        for token in _PLACEHOLDER_SAMPLES:
            assert token not in outcome.draft.body
            assert token not in outcome.draft.subject
        assert not contains_placeholder_token(outcome.draft.body)


class TestApprovalCopyAndChat:
    def test_approval_title_names_the_recipient_not_internal_ids(
        self, db_session: Session
    ) -> None:
        title, description = build_approval_copy(
            action_type="gmail_create_draft",
            recipient_name="Sarah Chen",
            company="Brightline Analytics",
            facts={
                "recommended_next_action": "Schedule discovery call and share Growth plan pricing."
            },
        )
        assert title == "Draft follow-up email to Sarah Chen at Brightline Analytics"
        assert "Sarah Chen" in description
        assert "Brightline Analytics" in description
        assert "Schedule discovery call" in description
        assert "Gmail" not in title
        assert "gmail_" not in title
        assert "lead_" not in title
        assert "lead_" not in description

    def test_missing_context_approval_copy_is_still_human(
        self,
    ) -> None:
        title, description = build_approval_copy(
            action_type="gmail_create_draft",
            recipient_name=None,
            company=None,
            facts={},
        )
        assert title == "Draft follow-up email"
        assert "No matching CRM contact" in description
        assert "does not invent" in description
        assert "Gmail action" not in title

    def test_chat_creates_recruiter_approval_and_keeps_gmail_mock(
        self, client: TestClient
    ) -> None:
        token = _register(client, suffix="_chat_crm")
        _create_lead_via_api(
            client,
            token,
            name="Sarah Chen",
            company="Brightline Analytics",
            email="sarah.chen@brightline.io",
            status="qualified",
            urgency="high",
            pain_point="Support team overwhelmed during product launches",
            recommended_next_action="Schedule discovery call and share Growth plan pricing.",
        )

        settings = get_settings()
        assert settings.GMAIL_SEND_ENABLED is False
        provider = get_email_provider(settings)
        assert isinstance(provider, MockEmailProvider)
        sent_before = len(provider._sent)

        resp = client.post(
            "/chat",
            json={"message": STARTER_PROMPT},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["intent"] == "email_drafting"
        assert body["approval_required"] is True
        assert body["approval_id"]
        assert "has been sent" not in (body["final_response"] or "").lower()
        for token_text in _PLACEHOLDER_SAMPLES:
            assert token_text not in (body["final_response"] or "")

        approval = client.get(
            f"/approvals/{body['approval_id']}",
            headers=_auth(token),
        )
        assert approval.status_code == 200, approval.text
        payload = approval.json()
        assert payload["title"] == (
            "Draft follow-up email to Sarah Chen at Brightline Analytics"
        )
        assert "Sarah Chen" in payload["description"]
        assert "lead_" not in payload["title"]
        assert "Gmail action" not in payload["title"]
        assert payload["status"] == "pending"

        email_payload = EmailApprovalPayload.model_validate(payload["proposed_payload"])
        assert email_payload.to == ["sarah.chen@brightline.io"]
        assert email_payload.body.strip()
        assert "sarah.chen@brightline.io" in ",".join(email_payload.to)
        for token_text in _PLACEHOLDER_SAMPLES:
            assert token_text not in email_payload.body
            assert token_text not in email_payload.subject

        assert len(provider._sent) == sent_before

    def test_chat_without_leads_still_requires_approval(
        self, client: TestClient
    ) -> None:
        token = _register(client, suffix="_chat_empty")
        resp = client.post(
            "/chat",
            json={"message": STARTER_PROMPT},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["approval_required"] is True
        approval = client.get(
            f"/approvals/{body['approval_id']}",
            headers=_auth(token),
        ).json()
        assert approval["title"] == "Draft follow-up email"
        assert "invent" in approval["description"]
        for token_text in _PLACEHOLDER_SAMPLES:
            assert token_text not in (body["final_response"] or "")
            assert token_text not in approval["title"]
            assert token_text not in approval["description"]


class TestSanitizeAndRanking:
    def test_sanitize_replaces_recipient_and_strips_other_tokens(self) -> None:
        text = "Hi [recipient], circling back on [relevant outcome]."
        cleaned = sanitize_draft_text(text, recipient_name="Priya Nair")
        assert cleaned == "Hi Priya Nair, circling back on."
        assert not contains_placeholder_token(cleaned)

    def test_most_promising_prefers_high_urgency_qualified(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="rank")
        _seed_northwind(db_session, principal)
        brightline = _seed_brightline(db_session, principal)
        chosen = select_most_promising_lead(
            lead_service.list_leads(db_session, principal=principal, limit=50)[0]
        )
        assert chosen is not None
        assert chosen.id == brightline.id

    def test_approval_payload_stays_valid_for_gmail_schema(
        self, db_session: Session
    ) -> None:
        principal = _setup_org(db_session, suffix="payload")
        _seed_brightline(db_session, principal)
        resolved = resolve_email_recipient(
            db_session, principal=principal, message=STARTER_PROMPT
        )
        outcome = email_service.draft_email(
            db_session,
            principal=principal,
            context=STARTER_PROMPT,
            recipient_name=resolved.recipient_name,
            recipient_email=resolved.recipient_email,
            crm_facts=resolved.facts,
            settings=Settings(),
            enforce_quota=False,
        )
        payload = gmail_service.build_approval_payload(
            subject=outcome.draft.subject,
            body=outcome.draft.body,
            recipient_email=resolved.recipient_email,
            recipient_name=resolved.recipient_name,
            tone=outcome.draft.tone,
        )
        parsed = EmailApprovalPayload.model_validate(payload)
        assert parsed.to == ["sarah.chen@brightline.io"]
        assert outcome.draft.approval_required is True
