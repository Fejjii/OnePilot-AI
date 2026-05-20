"""Calendar tool and agent routing tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from onepilot.agents.intent_classifier import classify
from onepilot.agents.workflow import branch_for, run_agent
from onepilot.core.config import get_settings
from onepilot.core.constants import Intent, MessageClass, PlanCode, Role
from onepilot.security.auth import Principal
from onepilot.tools import registry


def _register(client: TestClient, *, suffix: str) -> tuple[str, str, str]:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"cal{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Cal User",
            "organization_name": f"CalOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    from jose import jwt as jose_jwt

    token = resp.json()["access_token"]
    payload = jose_jwt.get_unverified_claims(token)
    return token, payload["org"], payload["sub"]


def _principal(org_id: str, user_id: str) -> Principal:
    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


class TestCalendarToolsRegistry:
    def test_calendar_tools_registered(self) -> None:
        names = registry.names()
        assert "calendar.check_availability" in names
        assert "calendar.suggest_slots" in names
        assert "calendar.create_event_request" in names


class TestCalendarIntentRouting:
    def test_availability_query(self) -> None:
        result = classify(
            "Am I free tomorrow afternoon?",
            message_class=MessageClass.WORKFLOW_REQUEST,
        )
        assert result.intent == Intent.CALENDAR_AVAILABILITY

    def test_slot_suggestion_query(self) -> None:
        result = classify(
            "Suggest three meeting slots next week.",
            message_class=MessageClass.WORKFLOW_REQUEST,
        )
        assert result.intent == Intent.CALENDAR_SCHEDULING

    def test_schedule_query(self) -> None:
        result = classify(
            "Schedule a 30 minute meeting with a high priority lead next week.",
            message_class=MessageClass.WORKFLOW_REQUEST,
        )
        assert result.intent == Intent.CALENDAR_SCHEDULING

    def test_combined_email_and_schedule(self) -> None:
        result = classify(
            "Draft an email and schedule a meeting with a high priority lead next week.",
            message_class=MessageClass.WORKFLOW_REQUEST,
        )
        assert result.intent == Intent.CALENDAR_AND_EMAIL

    def test_branch_for_calendar_intents(self) -> None:
        assert branch_for(Intent.CALENDAR_AVAILABILITY) == "calendar_assistant"
        assert branch_for(Intent.CALENDAR_SCHEDULING) == "calendar_assistant"
        assert branch_for(Intent.CALENDAR_AND_EMAIL) == "calendar_and_email"
        assert branch_for(Intent.COMPOUND_WORKFLOW) == "compound_workflow"

    def test_compound_workflow_intent(self) -> None:
        msg = (
            "Find recent SMB automation trends, draft an email, and schedule a meeting "
            "with a high priority lead next week."
        )
        result = classify(msg, message_class=MessageClass.WORKFLOW_REQUEST)
        assert result.intent == Intent.COMPOUND_WORKFLOW


class TestCalendarAgentWorkflow:
    def test_availability_branch(self, client_with_session) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_avail")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_cal_1",
            message="Am I free tomorrow afternoon?",
            history=[],
        )
        assert state.intent == Intent.CALENDAR_AVAILABILITY
        assert any(tc.tool_name == "calendar.check_availability" for tc in state.tool_calls)
        assert state.approval_required is False

    def test_schedule_creates_approval_not_event(self, client_with_session) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_sched")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_cal_2",
            message="Schedule a 30 minute meeting with a high priority lead next week.",
            history=[],
        )
        assert state.intent == Intent.CALENDAR_SCHEDULING
        assert any(tc.tool_name == "calendar.create_event_request" for tc in state.tool_calls)
        assert state.approval_required is True
        assert state.approval_id

    def test_gmail_route_still_works(self, client_with_session) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_mail")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_cal_3",
            message="Draft an email to Acme thanking them for the meeting.",
            history=[],
        )
        assert state.intent == Intent.EMAIL_DRAFTING
        assert any(tc.tool_name == "email.draft" for tc in state.tool_calls)

    def test_serper_route_still_works(self, client_with_session) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_serp")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_cal_4",
            message="Find recent SMB automation trends",
            history=[],
        )
        assert state.intent == Intent.WEB_SEARCH
        assert any(tc.tool_name == "external.web_search" for tc in state.tool_calls)

    def test_compound_workflow_calls_all_tools(self, client_with_session) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_compound")
        msg = (
            "Find recent SMB automation trends, draft an email, and schedule a meeting "
            "with a high priority lead next week."
        )
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_compound",
            message=msg,
            history=[],
        )
        tool_names = {tc.tool_name for tc in state.tool_calls}
        assert state.intent == Intent.COMPOUND_WORKFLOW
        assert "external.web_search" in tool_names
        assert "email.draft" in tool_names
        assert "calendar.create_event_request" in tool_names

    def test_rag_route_still_works(self, client_with_session) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_rag")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_cal_5",
            message="What services does NovaEdge offer?",
            history=[],
        )
        assert state.intent == Intent.KNOWLEDGE_SEARCH
        assert any(tc.tool_name == "rag.answer" for tc in state.tool_calls)
