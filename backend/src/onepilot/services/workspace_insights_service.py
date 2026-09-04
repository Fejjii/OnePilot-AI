"""Deterministic workspace insights from seeded CRM / approvals / conversations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from onepilot.core.constants import ApprovalStatus
from onepilot.services import approval_service, conversation_service, lead_service
from onepilot.services.crm_email_grounding import rank_leads

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from onepilot.security.auth import Principal

_ACTION_LABELS = {
    "send_email": "send email",
    "gmail_create_draft": "email draft",
    "gmail_send_email": "send email",
    "schedule_meeting": "schedule meeting",
    "calendar_create_event": "calendar event",
    "google_calendar_create_event": "calendar event",
    "update_crm": "update CRM",
}

_OVERVIEW_KEYWORDS_RE = re.compile(
    r"\b(summarize|summary of|overview)\b|business activity|recent business activity",
    re.IGNORECASE,
)
_APPROVALS_KEYWORD_RE = re.compile(r"\bapprov(?:al|als)\b", re.IGNORECASE)
_LEADS_INTENT_RE = re.compile(
    r"\b(analy|prioritize|promising|highlight|most promising)\b", re.IGNORECASE
)
_PENDING_RE = re.compile(r"\bpending\b|currently pending", re.IGNORECASE)


def _detect_focus(query: str) -> str:
    """Detect which `workspace-insights` focus mode the prompt intends.

    Ordering matters: overview/business-summary requests should not be
    misclassified as approvals just because they mention the word
    "approvals".
    """

    lowered = (query or "").lower()

    if _OVERVIEW_KEYWORDS_RE.search(lowered):
        return "overview"

    # Approvals-focused prompts should mention both "approvals" and "pending".
    if _APPROVALS_KEYWORD_RE.search(lowered) and _PENDING_RE.search(lowered):
        return "approvals"

    # Leads-focused prompts typically describe analysis/promotion within leads.
    if "lead" in lowered and _LEADS_INTENT_RE.search(lowered):
        return "leads"

    # Backstop: explicit leads mention -> leads focus.
    if "lead" in lowered:
        return "leads"

    return "overview"


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

    ranked_leads = rank_leads(leads)
    promising = [
        lead
        for lead in ranked_leads
        if (lead.urgency or "").lower() == "high"
        or (lead.status or "").lower() in {"qualified", "proposal"}
    ][:5]
    if not promising:
        promising = ranked_leads[:5]

    focus = _detect_focus(query)

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
            + (f", {_pretty_label(lead.status)}" if lead.status else "")
            + (
                f". Next: {lead.recommended_next_action}"
                if lead.recommended_next_action
                else ""
            )
        )
        for lead in promising
    ]
    approval_points = [
        f"{item.title} ({_action_label(item.action_type)}, {item.risk_level} risk)"
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
        evidence = "Source: pending approvals in this workspace."
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
        evidence = "Source: leads in this workspace, ranked by urgency and stage."
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
            "Sources: leads, approvals, and conversations in this workspace."
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


def _action_label(action_type: str | None) -> str:
    raw = (action_type or "").strip()
    if not raw:
        return "action"
    return _ACTION_LABELS.get(raw, raw.replace("_", " "))


def _pretty_label(value: str | None) -> str:
    return (value or "").replace("_", " ")
