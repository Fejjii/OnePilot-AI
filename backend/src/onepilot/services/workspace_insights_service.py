"""Deterministic workspace insights from seeded CRM / approvals / conversations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from onepilot.core.constants import ApprovalStatus
from onepilot.security.auth import Principal
from onepilot.services import approval_service, conversation_service, lead_service

_URGENCY_RANK = {"high": 0, "medium": 1, "low": 2}


def build_insights(
    session: Session,
    *,
    principal: Principal,
    query: str,
) -> dict[str, object]:
    """Return structured insight payload plus a markdown answer."""
    leads, lead_total = lead_service.list_leads(
        session, principal=principal, offset=0, limit=50
    )
    approvals, _approval_total, pending_count = approval_service.list_for_org(
        session,
        principal=principal,
        offset=0,
        limit=20,
        status=ApprovalStatus.PENDING.value,
    )
    conversations, conversation_total = conversation_service.list_conversations(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        offset=0,
        limit=10,
    )

    ranked_leads = sorted(
        leads,
        key=lambda lead: (
            _URGENCY_RANK.get((lead.urgency or "medium").lower(), 9),
            lead.name.lower(),
        ),
    )
    promising = [
        lead
        for lead in ranked_leads
        if (lead.urgency or "").lower() == "high"
        or (lead.status or "").lower() in {"qualified", "proposal"}
    ][:5]
    if not promising:
        promising = ranked_leads[:5]

    lowered = (query or "").lower()
    focus = "overview"
    if "approval" in lowered:
        focus = "approvals"
    elif "lead" in lowered:
        focus = "leads"

    answer = _format_answer(
        focus=focus,
        lead_total=lead_total,
        promising=promising,
        pending_count=pending_count,
        approvals=approvals,
        conversation_total=conversation_total,
        conversation_titles=[c.title for c in conversations[:5]],
    )
    return {
        "focus": focus,
        "lead_count": lead_total,
        "pending_approvals": pending_count,
        "conversation_count": conversation_total,
        "answer": answer,
    }


def _format_answer(
    *,
    focus: str,
    lead_total: int,
    promising: list,
    pending_count: int,
    approvals: list,
    conversation_total: int,
    conversation_titles: list[str],
) -> str:
    lead_points = [
        (
            f"{lead.name}"
            + (f" ({lead.company})" if lead.company else "")
            + f" — {lead.urgency or 'medium'} urgency"
            + (f", {lead.status}" if lead.status else "")
            + (
                f". Next: {lead.recommended_next_action}"
                if lead.recommended_next_action
                else ""
            )
        )
        for lead in promising
    ]
    approval_points = [
        f"{item.title} ({item.action_type}, {item.risk_level} risk)"
        for item in approvals[:8]
    ]

    if focus == "approvals":
        summary = (
            f"There are {pending_count} pending approval"
            f"{'s' if pending_count != 1 else ''} in the workspace."
        )
        key_points = approval_points or ["No pending approvals."]
        next_action = (
            "Open Approvals and review the highest-risk items first."
            if pending_count
            else "No approval action is needed right now."
        )
        evidence = "Source: pending ApprovalRequest rows in this organization."
    elif focus == "leads":
        summary = (
            f"The workspace has {lead_total} lead"
            f"{'s' if lead_total != 1 else ''}. Highlighting the most promising."
        )
        key_points = lead_points or ["No leads are seeded in this workspace yet."]
        next_action = (
            promising[0].recommended_next_action
            if promising and promising[0].recommended_next_action
            else "Review the leads pipeline and capture a follow-up."
        )
        evidence = "Source: Lead records in this organization, ranked by urgency and stage."
    else:
        summary = (
            f"Recent workspace activity: {lead_total} leads, {pending_count} pending "
            f"approvals, and {conversation_total} conversation"
            f"{'s' if conversation_total != 1 else ''} in this session."
        )
        key_points = []
        if lead_points:
            key_points.append("Top leads: " + "; ".join(lead_points[:3]))
        if approval_points:
            key_points.append("Pending approvals: " + "; ".join(approval_points[:3]))
        if conversation_titles:
            key_points.append("Recent conversations: " + "; ".join(conversation_titles))
        if not key_points:
            key_points.append("The workspace is seeded but has no extra activity yet.")
        next_action = (
            "Review pending approvals, then follow up with the highest-urgency lead."
        )
        evidence = (
            "Sources: Lead, ApprovalRequest, and Conversation rows scoped to this organization."
        )

    bullets = "\n".join(f"- {point}" for point in key_points)
    return (
        "## Summary\n"
        f"{summary}\n\n"
        "## Key points\n"
        f"{bullets}\n\n"
        "## Evidence or sources\n"
        f"{evidence}\n\n"
        "## Suggested next action\n"
        f"{next_action}"
    )
