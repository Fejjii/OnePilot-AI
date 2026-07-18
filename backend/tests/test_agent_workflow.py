"""Tests for the LangGraph agent workflow (routing + branches)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from onepilot.agents.workflow import (
    CLARIFICATION_RESPONSE,
    OUT_OF_SCOPE_RESPONSE,
    WEAK_EVIDENCE_RESPONSE,
    branch_for,
    run_agent,
)
from onepilot.core.config import get_settings
from onepilot.core.constants import Intent, PlanCode, Role
from onepilot.security.auth import Principal


def _register(client: TestClient, *, suffix: str) -> tuple[str, str, str]:
    """Register a user and return (token, org_id, user_id)."""
    resp = client.post(
        "/auth/register",
        json={
            "email": f"agent{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Agent User",
            "organization_name": f"AgentOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    from jose import jwt as jose_jwt

    payload = jose_jwt.get_unverified_claims(token)
    return token, payload["org"], payload["sub"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _principal(org_id: str, user_id: str) -> Principal:
    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


class TestBranchSelection:
    def test_branch_for_each_intent(self) -> None:
        assert branch_for(Intent.KNOWLEDGE_SEARCH) == "knowledge_search"
        assert branch_for(Intent.DOCUMENT_SUMMARY) == "knowledge_search"
        assert branch_for(Intent.WEB_SEARCH) == "web_search"
        assert branch_for(Intent.WEB_AND_KNOWLEDGE) == "web_and_knowledge"
        assert branch_for(Intent.EMAIL_DRAFTING) == "email_assistant"
        assert branch_for(Intent.CALENDAR_AVAILABILITY) == "calendar_assistant"
        assert branch_for(Intent.CALENDAR_SCHEDULING) == "calendar_assistant"
        assert branch_for(Intent.CALENDAR_AND_EMAIL) == "calendar_and_email"
        assert branch_for(Intent.LEAD_SUPPORT) == "lead_assistant"
        assert branch_for(Intent.WORKFLOW_ACTION) == "lead_assistant"
        assert branch_for(Intent.GENERAL_ASSISTANT) == "general_chat"
        assert branch_for(Intent.OUT_OF_SCOPE) == "out_of_scope"
        assert branch_for(Intent.CLARIFICATION) == "clarification"

    def test_branch_for_none_defaults_to_general(self) -> None:
        assert branch_for(None) == "general_chat"


class TestRunAgentBranches:
    def test_general_chat_branch(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_gen")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message="Hello there, how are you?",
            history=[],
        )
        assert state.intent == Intent.GENERAL_ASSISTANT
        assert state.final_response
        assert any(tc.tool_name == "chat.general" for tc in state.tool_calls)

    def test_out_of_scope_branch(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_oos")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message="Tell me a joke about programming.",
            history=[],
        )
        assert state.intent == Intent.OUT_OF_SCOPE
        assert state.final_response == OUT_OF_SCOPE_RESPONSE
        assert state.approval_required is False

    def test_clarification_branch(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_clar")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message="ok",
            history=[],
        )
        assert state.intent == Intent.CLARIFICATION
        assert state.final_response == CLARIFICATION_RESPONSE

    def test_knowledge_search_branch_weak_evidence(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_ks")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message="What is our refund policy?",
            history=[],
        )
        assert state.intent == Intent.KNOWLEDGE_SEARCH
        assert state.final_response == WEAK_EVIDENCE_RESPONSE
        assert "weak_evidence" in state.safety_flags

    def test_knowledge_search_branch_with_document(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, _session = client_with_session
        token, _org_id, _user_id = _register(client, suffix="_ks2")
        # Seed a doc via the public API.
        resp = client.post(
            "/documents/upload",
            files={
                "file": (
                    "policy.md",
                    io.BytesIO(
                        b"# Refund Policy\n\nWe refund within 14 days of purchase upon written request."
                    ),
                    "text/markdown",
                )
            },
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text

        chat = client.post(
            "/chat",
            json={"message": "What is our refund policy?"},
            headers=_h(token),
        )
        assert chat.status_code == 200, chat.text
        body = chat.json()
        assert body["intent"] == "knowledge_search"
        assert body["citations"], "Expected at least one citation"

    def test_lead_branch_captures_lead_on_explicit_request(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_lead")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message=(
                "Capture this lead: John Doe at Acme is asking about pricing."
            ),
            history=[],
        )
        assert state.intent == Intent.LEAD_SUPPORT
        tool_call = next(
            tc for tc in state.tool_calls if tc.tool_name == "lead.support"
        )
        assert "captured=True" in tool_call.output_summary

    def test_lead_branch_does_not_capture_implicit(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_lead2")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message="We have a new interested customer asking about pricing.",
            history=[],
        )
        assert state.intent == Intent.LEAD_SUPPORT
        tool_call = next(
            tc for tc in state.tool_calls if tc.tool_name == "lead.support"
        )
        assert "captured=False" in tool_call.output_summary

    def test_email_branch_produces_approval(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_email")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message="Draft and send an email to Bob thanking him for the demo.",
            history=[],
        )
        assert state.intent == Intent.EMAIL_DRAFTING
        assert state.approval_required is True
        assert state.approval_id and state.approval_id.startswith("apv_")
        assert "Pending approval" in (state.final_response or "")

    def test_email_draft_only_requires_approval_in_mock_mode(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_email_draft")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message="Draft an email to a lead about NovaEdge automation services.",
            history=[],
        )
        assert state.intent == Intent.EMAIL_DRAFTING
        assert state.approval_required is True
        assert state.approval_id and state.approval_id.startswith("apv_")


class TestTraceSteps:
    def test_trace_contains_classify_route_guardrail_finalize(
        self, client_with_session: tuple[TestClient, object]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_trace")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_test",
            message="Hello!",
            history=[],
        )
        step_names = [s.step for s in state.trace_steps]
        assert "classify_intent" in step_names
        assert "route" in step_names
        assert "guardrail" in step_names
        assert "finalize_response" in step_names
