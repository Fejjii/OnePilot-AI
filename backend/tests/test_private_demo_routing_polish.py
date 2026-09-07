"""Private-demo P0 routing: availability, scheduling continuation, and RAG."""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from onepilot.agents.intent_classifier import classify
from onepilot.agents.message_classifier import classify_message
from onepilot.agents.workflow import run_agent
from onepilot.core.config import get_settings
from onepilot.core.constants import Intent, MessageClass, PlanCode, Role
from onepilot.providers.calendar.mock_calendar_provider import MockCalendarProvider
from onepilot.providers.calendar.time_parser import parse_calendar_window
from onepilot.security.auth import Principal
from onepilot.services.calendar_intent import (
    extract_meeting_title,
    recover_prior_scheduling_request,
    resolve_calendar_source_message,
)
from onepilot.services.calendar_service import infer_calendar_tool, prepare_event_approval

AVAILABILITY_PROMPT = "When am I available tomorrow between 9 AM and 5 PM?"
SCHEDULING_PROMPT = (
    'Schedule a 30-minute meeting tomorrow at 3 PM titled "OnePilot Live Calendar Test".'
)
CONTINUATION_PROMPT = "Just schedule the meeting."
RAG_PROMPT = "What is the internal launch codename for this demo?"
RAG_DOC = (
    "# OnePilot Private Knowledge Test\n\n"
    "The internal launch codename for this demo is ORION-47.\n"
)

AVAILABILITY_VARIANTS = (
    "When am I available?",
    "When am I free?",
    "What time am I available?",
    "What times am I free?",
    "Do I have availability?",
    "availability tomorrow",
    "available tomorrow between 9 AM and 5 PM",
    AVAILABILITY_PROMPT,
)


def _register(client: TestClient, *, suffix: str) -> tuple[str, str, str]:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"pdemo{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Private Demo User",
            "organization_name": f"PrivateDemo{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
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


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAvailabilityRouting:
    def test_production_prompt_is_calendar_availability_not_general(self) -> None:
        msg_result = classify_message(AVAILABILITY_PROMPT)
        assert msg_result.message_class == MessageClass.WORKFLOW_REQUEST
        intent = classify(AVAILABILITY_PROMPT, message_class=msg_result.message_class)
        assert intent.intent == Intent.CALENDAR_AVAILABILITY
        assert infer_calendar_tool(AVAILABILITY_PROMPT) == "check_availability"

    def test_availability_natural_variants(self) -> None:
        for prompt in AVAILABILITY_VARIANTS:
            msg_result = classify_message(prompt)
            intent = classify(prompt, message_class=msg_result.message_class)
            assert intent.intent == Intent.CALENDAR_AVAILABILITY, prompt
            assert infer_calendar_tool(prompt) == "check_availability", prompt
            assert infer_calendar_tool(prompt) != "list_events", prompt

    def test_meetings_list_still_distinct_from_availability(self) -> None:
        prompt = "Show my meetings this week."
        assert infer_calendar_tool(prompt) == "list_events"
        msg_result = classify_message(prompt)
        intent = classify(prompt, message_class=msg_result.message_class)
        assert intent.intent == Intent.CALENDAR_AVAILABILITY
        assert infer_calendar_tool(prompt) != "check_availability"

    def test_capability_available_tools_is_not_calendar(self) -> None:
        prompt = "What tools are available?"
        msg_result = classify_message(prompt)
        assert msg_result.message_class == MessageClass.CAPABILITY_OR_HELP
        intent = classify(prompt, message_class=msg_result.message_class)
        assert intent.intent == Intent.GENERAL_ASSISTANT

    def test_agent_uses_check_availability_for_production_prompt(
        self, client_with_session
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_avail_p0")
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_avail_p0",
            message=AVAILABILITY_PROMPT,
            history=[],
        )
        assert state.intent == Intent.CALENDAR_AVAILABILITY
        assert any(tc.tool_name == "calendar.check_availability" for tc in state.tool_calls)
        assert not any(tc.tool_name == "chat.general" for tc in state.tool_calls)
        text = (state.final_response or "").lower()
        assert "available time slots" in text or "open times" in text
        steps = [s.step for s in state.trace_steps]
        assert any(name == "execute_tool:calendar.check_availability" for name in steps)


class TestSchedulingDetailsAndContinuation:
    def test_exact_prompt_routes_to_calendar_scheduling(self) -> None:
        msg_result = classify_message(SCHEDULING_PROMPT)
        assert msg_result.message_class == MessageClass.WORKFLOW_REQUEST
        intent = classify(SCHEDULING_PROMPT, message_class=msg_result.message_class)
        assert intent.intent == Intent.CALENDAR_SCHEDULING
        assert extract_meeting_title(SCHEDULING_PROMPT) == "OnePilot Live Calendar Test"

    def test_title_containing_test_is_not_conversational(self) -> None:
        msg_result = classify_message(SCHEDULING_PROMPT)
        assert msg_result.message_class != MessageClass.CONVERSATIONAL

    def test_berlin_tomorrow_3pm_window(self) -> None:
        ref = datetime(2026, 5, 20, 10, 0)
        parsed = parse_calendar_window(
            SCHEDULING_PROMPT,
            timezone="Europe/Berlin",
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=ref,
        )
        assert parsed.query_type == "specific"
        assert parsed.time_min.hour == 13
        assert (parsed.time_max - parsed.time_min).total_seconds() == 30 * 60

    def test_between_9_and_5_is_range_not_specific(self) -> None:
        ref = datetime(2026, 5, 20, 10, 0)
        parsed = parse_calendar_window(
            AVAILABILITY_PROMPT,
            timezone="Europe/Berlin",
            lookahead_days=14,
            slot_duration_minutes=30,
            reference=ref,
        )
        assert parsed.query_type == "range"
        assert parsed.time_min.hour == 7
        assert parsed.time_max.hour == 15

    def test_continuation_recovers_prior_request(self) -> None:
        history = [{"role": "user", "content": SCHEDULING_PROMPT}]
        recovered = recover_prior_scheduling_request(history)
        assert recovered == SCHEDULING_PROMPT
        assert resolve_calendar_source_message(CONTINUATION_PROMPT, history) == SCHEDULING_PROMPT
        msg_result = classify_message(CONTINUATION_PROMPT, history=history)
        intent = classify(
            CONTINUATION_PROMPT,
            message_class=msg_result.message_class,
            history=history,
        )
        assert intent.intent == Intent.CALENDAR_SCHEDULING

    def test_go_ahead_without_history_does_not_invent_details(self) -> None:
        assert recover_prior_scheduling_request([]) is None
        assert resolve_calendar_source_message("Go ahead", []) == "Go ahead"

    def test_exact_prompt_creates_approval_with_title_and_berlin_slot(
        self, client_with_session, monkeypatch
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_sched_p0")

        def _fail_create(*_args, **_kwargs):
            raise AssertionError("Calendar create must not run before approval")

        monkeypatch.setattr(MockCalendarProvider, "create_event", _fail_create)

        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_sched_p0",
            message=SCHEDULING_PROMPT,
            history=[],
        )
        assert state.intent == Intent.CALENDAR_SCHEDULING
        assert state.approval_required is True
        assert state.approval_id
        assert any(tc.tool_name == "calendar.create_event_request" for tc in state.tool_calls)
        text = state.final_response or ""
        assert "OnePilot Live Calendar Test" in text
        assert "OnePilot scheduled meeting" not in text
        tz = ZoneInfo("Europe/Berlin")
        tomorrow = (datetime.now(tz) + timedelta(days=1)).date()
        assert f"{tomorrow.day} {tomorrow.strftime('%B')}" in text or "15:00" in text
        assert "15:00" in text
        assert "15:30" in text
        assert "pending" in text.lower()

    def test_continuation_preserves_details(self, client_with_session, monkeypatch) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_cont_p0")

        def _fail_create(*_args, **_kwargs):
            raise AssertionError("Calendar create must not run before approval")

        monkeypatch.setattr(MockCalendarProvider, "create_event", _fail_create)

        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=get_settings(),
            conversation_id="conv_cont_p0",
            message=CONTINUATION_PROMPT,
            history=[{"role": "user", "content": SCHEDULING_PROMPT}],
        )
        assert state.intent == Intent.CALENDAR_SCHEDULING
        assert state.approval_required is True
        text = state.final_response or ""
        assert "OnePilot Live Calendar Test" in text
        assert "15:00" in text
        assert "15:30" in text

    def test_prepare_event_approval_does_not_call_create(self, monkeypatch) -> None:
        def _fail_create(*_args, **_kwargs):
            raise AssertionError("Calendar create must not run before approval")

        monkeypatch.setattr(MockCalendarProvider, "create_event", _fail_create)
        result = prepare_event_approval(
            MagicMock(),
            principal=MagicMock(),
            message=SCHEDULING_PROMPT,
            settings=get_settings(),
        )
        assert result["approval_status"] == "pending"
        assert result["approval_payload"]["summary"] == "OnePilot Live Calendar Test"


class TestWorkspaceRagRouting:
    def test_codename_question_is_knowledge_search_not_clarify(self) -> None:
        msg_result = classify_message(RAG_PROMPT)
        assert msg_result.message_class == MessageClass.BUSINESS_KNOWLEDGE
        intent = classify(RAG_PROMPT, message_class=msg_result.message_class)
        assert intent.intent == Intent.KNOWLEDGE_SEARCH
        assert intent.intent != Intent.CLARIFICATION

    def test_casual_hello_is_not_rag(self) -> None:
        msg_result = classify_message("Hello")
        assert msg_result.message_class == MessageClass.CONVERSATIONAL
        intent = classify("Hello", message_class=msg_result.message_class)
        assert intent.intent == Intent.GENERAL_ASSISTANT

    def test_workspace_answers_indexed_doc(self, client_with_session) -> None:
        client, _session = client_with_session
        token, _org_id, _user_id = _register(client, suffix="_rag_p0")
        upload = client.post(
            "/documents/upload",
            files={
                "file": (
                    "onepilot-private-knowledge-test.md",
                    io.BytesIO(RAG_DOC.encode("utf-8")),
                    "text/markdown",
                )
            },
            headers=_h(token),
        )
        assert upload.status_code == 200, upload.text

        chat = client.post(
            "/chat",
            json={"message": RAG_PROMPT},
            headers=_h(token),
        )
        assert chat.status_code == 200, chat.text
        body = chat.json()
        assert body["intent"] == "knowledge_search"
        assert body["citations"], "Expected tenant-scoped citation"
        assert "ORION-47" in (body["final_response"] or "")
        tool_names = [tc.get("tool_name") for tc in (body.get("tool_calls") or [])]
        assert "rag.answer" in tool_names
        assert "clarification" not in (body.get("safety_flags") or [])
        title = body["citations"][0]["document_title"]
        assert "OnePilot Private Knowledge Test" in title or "private knowledge" in title.lower()
