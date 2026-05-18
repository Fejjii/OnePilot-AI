"""Lead service.

Captures, qualifies, and stores leads. Writes an audit log on every create or
update. External CRM sync is **not** performed yet — only an audit log is
written. Approval gates are enforced upstream by the agent workflow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from onepilot.core.constants import UsageFeature
from onepilot.core.errors import NotFoundError, ValidationError
from onepilot.core.ids import new_id
from onepilot.core.logging import get_logger
from onepilot.repositories.leads import LeadRepository
from onepilot.repositories.models import Lead
from onepilot.security.auth import Principal
from onepilot.services import audit_service, quota_service, usage_service

logger = get_logger(__name__)


# Heuristic urgency keywords for the lead-support tool.
_HIGH_URGENCY = (
    "asap",
    "urgent",
    "immediately",
    "today",
    "critical",
    "blocker",
    "production down",
)
_LOW_URGENCY = ("whenever", "no rush", "fyi", "exploring", "just looking")


# Heuristic intent keywords for leads.
_INTENT_BUY = ("buy", "pricing", "purchase", "subscribe", "upgrade", "license")
_INTENT_DEMO = ("demo", "trial", "see the product", "walkthrough")
_INTENT_SUPPORT = ("issue", "bug", "support", "problem", "broken")
_INTENT_PARTNERSHIP = ("partner", "partnership", "integration", "reseller")


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


@dataclass(slots=True)
class LeadClassification:
    urgency: str
    intent: str | None
    summary: str
    pain_point: str | None
    recommended_next_action: str


def classify_lead(message: str, *, name: str | None = None) -> LeadClassification:
    """Heuristically derive urgency, intent, and a next-action recommendation."""
    text = (message or "").lower()

    urgency = "medium"
    if any(kw in text for kw in _HIGH_URGENCY):
        urgency = "high"
    elif any(kw in text for kw in _LOW_URGENCY):
        urgency = "low"

    intent: str | None
    if any(kw in text for kw in _INTENT_BUY):
        intent = "purchase"
    elif any(kw in text for kw in _INTENT_DEMO):
        intent = "demo"
    elif any(kw in text for kw in _INTENT_SUPPORT):
        intent = "support"
    elif any(kw in text for kw in _INTENT_PARTNERSHIP):
        intent = "partnership"
    else:
        intent = None

    pain_point: str | None = None
    if intent == "support" or "problem" in text or "issue" in text:
        pain_point = (message or "").strip()[:512]

    summary = _summarize(message, who=name)

    recommended = _recommend_next_action(intent, urgency)

    return LeadClassification(
        urgency=urgency,
        intent=intent,
        summary=summary,
        pain_point=pain_point,
        recommended_next_action=recommended,
    )


def _summarize(message: str, *, who: str | None) -> str:
    cleaned = " ".join((message or "").split())
    if not cleaned:
        return "Lead captured from chat."
    snippet = cleaned[:240]
    if who:
        return f"Lead from {who}: {snippet}"
    return f"Lead from chat: {snippet}"


def _recommend_next_action(intent: str | None, urgency: str) -> str:
    if intent == "purchase":
        return "Send pricing & schedule a discovery call within 24h."
    if intent == "demo":
        return "Offer a 20-minute product demo this week."
    if intent == "support":
        return "Escalate to support, share known-issue article if relevant."
    if intent == "partnership":
        return "Forward to partnerships team for evaluation."
    if urgency == "high":
        return "Reach out within 4 hours; clarify the request."
    return "Acknowledge receipt and schedule a follow-up."


def extract_email(message: str) -> str | None:
    match = _EMAIL_RE.search(message or "")
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def create_lead(
    session: Session,
    *,
    principal: Principal,
    name: str,
    email: str | None = None,
    company: str | None = None,
    source: str | None = None,
    urgency: str = "medium",
    intent: str | None = None,
    pain_point: str | None = None,
    summary: str | None = None,
    recommended_next_action: str | None = None,
    status: str = "new",
    enforce_quota: bool = True,
) -> Lead:
    if not name or not name.strip():
        raise ValidationError("Lead name is required")

    if enforce_quota:
        quota_service.check_and_increment(
            session,
            principal.organization_id,
            UsageFeature.LEAD_WORKFLOWS,
            amount=1,
        )

    lead = Lead(
        id=new_id("lead"),
        organization_id=principal.organization_id,
        name=name.strip()[:255],
        email=(email or None),
        company=company,
        source=source or "chat",
        urgency=urgency,
        intent=intent,
        pain_point=pain_point,
        summary=summary,
        recommended_next_action=recommended_next_action,
        status=status,
        created_by=principal.user_id,
    )
    repo = LeadRepository(session)
    repo.create(lead)

    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="lead.created",
        resource_type="lead",
        resource_id=lead.id,
        detail={
            "name": lead.name,
            "urgency": lead.urgency,
            "intent": lead.intent,
            "source": lead.source,
        },
    )
    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=UsageFeature.LEAD_WORKFLOWS.value,
        provider="onepilot.lead_service",
        metadata={"lead_id": lead.id, "operation": "create"},
    )
    logger.info(
        "lead_created",
        organization_id=principal.organization_id,
        lead_id=lead.id,
        urgency=lead.urgency,
    )
    return lead


def update_lead(
    session: Session,
    *,
    principal: Principal,
    lead_id: str,
    data: dict,
) -> Lead:
    repo = LeadRepository(session)
    lead = repo.get(lead_id, organization_id=principal.organization_id)
    if lead is None:
        raise NotFoundError(f"Lead '{lead_id}' not found")

    clean = {k: v for k, v in data.items() if v is not None}
    repo.update(lead, clean)

    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="lead.updated",
        resource_type="lead",
        resource_id=lead.id,
        detail={"fields": sorted(clean.keys())},
    )
    return lead


def list_leads(
    session: Session,
    *,
    principal: Principal,
    offset: int = 0,
    limit: int = 50,
    status: str | None = None,
) -> tuple[list[Lead], int]:
    repo = LeadRepository(session)
    items = repo.list_for_org(
        principal.organization_id,
        offset=offset,
        limit=min(limit, 100),
        status=status,
    )
    total = repo.count_for_org(principal.organization_id)
    return items, total


def get_lead(
    session: Session, *, principal: Principal, lead_id: str
) -> Lead:
    repo = LeadRepository(session)
    lead = repo.get(lead_id, organization_id=principal.organization_id)
    if lead is None:
        raise NotFoundError(f"Lead '{lead_id}' not found")
    return lead
