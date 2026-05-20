"""Tests for external web search tool and service."""

from __future__ import annotations

from onepilot.agents.intent_classifier import classify
from onepilot.agents.message_classifier import classify_message
from onepilot.agents.workflow import branch_for, run_agent
from onepilot.core.constants import Intent, MessageClass
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.schemas.web_search import WebSearchToolResult
from onepilot.security.auth import Principal
from onepilot.tools.base import ToolContext
from onepilot.tools.web_search_tool import WebSearchTool


def _principal(org_id: str = "org_test", user_id: str = "usr_test") -> Principal:
    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


def test_web_search_tool_output_shape(db_session) -> None:
    tool = WebSearchTool()
    settings = Settings(SERPER_API_KEY="", APP_ENV="test")
    ctx = ToolContext(session=db_session, principal=_principal(), settings=settings)
    result = tool.run(ctx, query="recent SMB automation trends", max_results=3)

    payload = WebSearchToolResult.model_validate(result.output)
    assert payload.provider_mode in {"missing", "fallback", "live"}
    assert payload.result_count >= 0
    assert "results=" in result.output_summary
    assert result.tool_name == "external.web_search"
    assert isinstance(result.citations, list)


def test_routing_web_search_for_recent_query() -> None:
    msg = classify_message("Find recent SMB automation trends")
    assert msg.message_class == MessageClass.EXTERNAL_RESEARCH
    intent = classify("Find recent SMB automation trends", message_class=msg.message_class)
    assert intent.intent == Intent.WEB_SEARCH
    assert branch_for(intent.intent) == "web_search"


def test_routing_combined_web_and_knowledge() -> None:
    message = (
        "Find recent SMB automation trends and compare them with "
        "NovaEdge Solutions services."
    )
    msg = classify_message(message)
    assert msg.message_class == MessageClass.EXTERNAL_RESEARCH
    intent = classify(message, message_class=msg.message_class)
    assert intent.intent == Intent.WEB_AND_KNOWLEDGE
    assert branch_for(intent.intent) == "web_and_knowledge"


def test_no_web_search_for_general_assistant() -> None:
    msg = classify_message("What can you do for me?")
    assert msg.message_class == MessageClass.CAPABILITY_OR_HELP
    intent = classify("What can you do for me?", message_class=msg.message_class)
    assert intent.intent == Intent.GENERAL_ASSISTANT


def test_no_web_search_for_internal_kb() -> None:
    msg = classify_message("What services does NovaEdge Solutions offer?")
    assert msg.message_class == MessageClass.BUSINESS_KNOWLEDGE
    intent = classify(
        "What services does NovaEdge Solutions offer?",
        message_class=msg.message_class,
    )
    assert intent.intent == Intent.KNOWLEDGE_SEARCH


def test_no_web_search_for_correction() -> None:
    msg = classify_message("This is not what I meant.")
    assert msg.message_class == MessageClass.CORRECTION_OR_META
    intent = classify("This is not what I meant.", message_class=msg.message_class)
    assert intent.intent == Intent.GENERAL_ASSISTANT


def test_agent_combined_flow_records_both_tools(
    client_with_session: tuple[TestClient, Session],
) -> None:
    client, session = client_with_session
    resp = client.post(
        "/auth/register",
        json={
            "email": "webcombo@example.com",
            "password": "strongpass123",
            "full_name": "Web Combo User",
            "organization_name": "WebComboOrg",
        },
    )
    assert resp.status_code == 200, resp.text
    from jose import jwt as jose_jwt

    claims = jose_jwt.get_unverified_claims(resp.json()["access_token"])
    principal = _principal(claims["org"], claims["sub"])
    state = run_agent(
        session=session,
        principal=principal,
        settings=get_settings(),
        conversation_id="conv_web_test",
        message=(
            "Find recent SMB automation trends and compare them with "
            "NovaEdge Solutions services."
        ),
    )
    tool_names = {tc.tool_name for tc in state.tool_calls}
    assert "external.web_search" in tool_names
    assert "rag.answer" in tool_names
    assert state.intent == Intent.WEB_AND_KNOWLEDGE
    assert "Internal company knowledge" in (state.final_response or "")
    assert "External web evidence" in (state.final_response or "")
