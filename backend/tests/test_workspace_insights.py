"""Tests for workspace.insights tool (OP-015)."""

from __future__ import annotations

from onepilot.agents.workflow import run_agent
from onepilot.core.config import get_settings
from onepilot.core.constants import Intent, PlanCode, Role
from onepilot.security.auth import Principal
from onepilot.tools.base import ToolContext
from onepilot.tools.workspace_insights_tool import WorkspaceInsightsTool


def _principal(org_id: str, user_id: str) -> Principal:
    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


def test_workspace_insights_tool_empty_org(db_session) -> None:
    principal = _principal("org_empty_insights", "usr_empty_insights")
    ctx = ToolContext(session=db_session, principal=principal, settings=get_settings())
    result = WorkspaceInsightsTool().run(
        ctx, message="Which approvals are currently pending and what do they cover?"
    )
    assert result.tool_name == "workspace.insights"
    assert result.output["focus"] == "approvals"
    assert "pending" in result.output["answer"].lower()


def test_workspace_insights_agent_branch(db_session) -> None:
    principal = _principal("org_insights_agent", "usr_insights_agent")
    state = run_agent(
        session=db_session,
        principal=principal,
        settings=get_settings(),
        conversation_id="conv_insights",
        message="Analyze our current leads and highlight the most promising ones.",
    )
    assert state.intent == Intent.WORKSPACE_INSIGHTS
    tool_names = [
        tc.tool_name if hasattr(tc, "tool_name") else tc["tool_name"]
        for tc in state.tool_calls
    ]
    assert "workspace.insights" in tool_names
    assert "leads" in (state.final_response or "").lower()
