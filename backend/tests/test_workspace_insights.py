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


def test_starter_prompt_chip_focus_modes_are_distinct(db_session) -> None:
    principal = _principal("org_insights_agent", "usr_insights_agent")
    ctx = ToolContext(session=db_session, principal=principal, settings=get_settings())
    tool = WorkspaceInsightsTool()

    overview_prompt = (
        "Summarize our recent business activity across leads, approvals, and conversations."
    )
    approvals_prompt = (
        "Which approvals are currently pending and what do they cover?"
    )
    leads_prompt = "Analyze our current leads and highlight the most promising ones."

    overview = tool.run(ctx, message=overview_prompt).output
    approvals = tool.run(ctx, message=approvals_prompt).output
    leads = tool.run(ctx, message=leads_prompt).output

    # Focus mapping
    assert overview["focus"] == "overview"
    assert approvals["focus"] == "approvals"
    assert leads["focus"] == "leads"

    # Key section grounding differences (avoid brittle full-string equality)
    overview_answer = str(overview["answer"])
    approvals_answer = str(approvals["answer"])
    leads_answer = str(leads["answer"])

    assert "Recent workspace activity:" in overview_answer
    assert "Source: pending ApprovalRequest rows in this organization." in (
        approvals_answer
    )
    assert (
        "Source: Lead records in this organization, ranked by urgency and stage."
        in leads_answer
    )

    # And they should not collapse into the same output.
    assert overview_answer != approvals_answer
    assert overview_answer != leads_answer
    assert approvals_answer != leads_answer

    # Deterministic: same inputs -> same outputs.
    overview2 = tool.run(ctx, message=overview_prompt).output
    assert str(overview2["answer"]) == overview_answer
