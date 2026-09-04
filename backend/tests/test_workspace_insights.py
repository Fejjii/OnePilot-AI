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
    assert "Source: pending approvals in this workspace." in approvals_answer
    assert "Source: leads in this workspace, ranked by urgency and stage." in (
        leads_answer
    )

    # And they should not collapse into the same output.
    assert overview_answer != approvals_answer
    assert overview_answer != leads_answer
    assert approvals_answer != leads_answer

    # Deterministic: same inputs -> same outputs.
    overview2 = tool.run(ctx, message=overview_prompt).output
    assert str(overview2["answer"]) == overview_answer


def test_most_promising_lead_matches_crm_email_ranking(db_session) -> None:
    """Workspace insights and email drafting must name the same top lead."""
    from onepilot.core.ids import new_id
    from onepilot.demo_data.seed import CURATED_DEMO_LEADS
    from onepilot.repositories.models import Organization, Subscription
    from onepilot.services import lead_service
    from onepilot.services.crm_email_grounding import select_most_promising_lead

    org_id = "org_insights_rank"
    db_session.add(Organization(id=org_id, name="Insights Rank", slug="insights-rank"))
    db_session.add(
        Subscription(
            id=new_id("sub"),
            organization_id=org_id,
            plan_code=PlanCode.FREE,
            status="active",
        )
    )
    db_session.flush()
    principal = _principal(org_id, "usr_insights_rank")
    for row in CURATED_DEMO_LEADS:
        lead_service.create_lead(
            db_session,
            principal=principal,
            name=row["name"],
            company=row.get("company"),
            email=row.get("email"),
            source=row.get("source"),
            status=row.get("status"),
            urgency=row.get("urgency"),
            intent=row.get("intent"),
            pain_point=row.get("pain_point"),
            summary=row.get("summary"),
            recommended_next_action=row.get("recommended_next_action"),
            enforce_quota=False,
        )

    leads, _total = lead_service.list_leads(
        db_session, principal=principal, offset=0, limit=50
    )
    chosen = select_most_promising_lead(leads)
    assert chosen is not None
    assert chosen.name == "Sarah Chen"
    assert chosen.company == "Brightline Analytics"

    ctx = ToolContext(session=db_session, principal=principal, settings=get_settings())
    leads_answer = str(
        WorkspaceInsightsTool()
        .run(
            ctx,
            message="Analyze our current leads and highlight the most promising ones.",
        )
        .output["answer"]
    )
    assert "Sarah Chen (Brightline Analytics)" in leads_answer
    first_lead_line = next(
        line for line in leads_answer.splitlines() if line.startswith("- ") and "urgency" in line
    )
    assert first_lead_line.startswith("- Sarah Chen")
