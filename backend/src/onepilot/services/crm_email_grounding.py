"""CRM-grounded recipient resolution and recruiter-facing email copy.

Resolves a tenant-scoped lead from chat/application context and builds
approval titles that name the real person or company. Never invents
customer facts or emits bracketed template placeholders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from onepilot.core.errors import NotFoundError
from onepilot.repositories.models import Lead
from onepilot.security.auth import Principal
from onepilot.services import lead_service

_URGENCY_RANK = {"high": 0, "medium": 1, "low": 2}
_STATUS_RANK = {
    "qualified": 0,
    "proposal": 1,
    "contacted": 2,
    "new": 3,
    "won": 4,
    "lost": 5,
}

_PROMISING_RE = re.compile(
    r"\b(?:most\s+promising|top|best|highest[\s-]?priority)\s+leads?\b",
    re.IGNORECASE,
)
_GENERIC_LEAD_RE = re.compile(
    r"\b(?:a|the|our|this)\s+lead\b",
    re.IGNORECASE,
)
_TO_PERSON_RE = re.compile(
    r"\b(?:to|for)\s+"
    r"(?!our\s+most|the\s+most|a\s+lead|the\s+lead|our\s+lead|this\s+lead)"
    r"([A-Z][a-zA-Z''.-]+(?:\s+[A-Z][a-zA-Z''.-]+){0,2})\b"
)

_CRM_FACT_FIELDS: tuple[str, ...] = (
    "name",
    "company",
    "email",
    "status",
    "urgency",
    "intent",
    "pain_point",
    "summary",
    "recommended_next_action",
)

_BRACKET_PLACEHOLDER_RE = re.compile(r"\[[^\[\]]{1,80}\]")
_NAME_LIKE_PLACEHOLDERS = frozenset(
    {
        "recipient",
        "name",
        "first name",
        "contact",
        "contact name",
        "customer",
        "customer name",
    }
)

# Internal identifiers must never appear in recruiter-facing copy.
_INTERNAL_ID_RE = re.compile(
    r"\b(?:lead|org|usr|apv|conv|doc|gmail)_[a-z0-9]+\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ResolvedEmailRecipient:
    """Tenant-scoped recipient resolution for email drafting."""

    recipient_name: str | None
    recipient_email: str | None
    company: str | None
    facts: dict[str, str] = field(default_factory=dict)
    match_reason: str = "none"
    lead_id: str | None = None


def crm_facts_from_lead(lead: Lead) -> dict[str, str]:
    """Return only non-empty stored CRM fields. Never fabricates values."""
    facts: dict[str, str] = {}
    for name in _CRM_FACT_FIELDS:
        value = getattr(lead, name, None)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            facts[name] = text
    return facts


def rank_leads(leads: list[Lead]) -> list[Lead]:
    """Deterministic recruiter ranking: urgency, then pipeline status, then name."""
    return sorted(
        leads,
        key=lambda lead: (
            _URGENCY_RANK.get((lead.urgency or "medium").lower(), 9),
            _STATUS_RANK.get((lead.status or "").lower(), 9),
            (lead.name or "").lower(),
        ),
    )


def select_most_promising_lead(leads: list[Lead]) -> Lead | None:
    """Pick the highest-priority open lead, matching workspace insight ranking."""
    if not leads:
        return None
    ranked = rank_leads(leads)
    promising = [
        lead
        for lead in ranked
        if (lead.urgency or "").lower() == "high"
        or (lead.status or "").lower() in {"qualified", "proposal"}
    ]
    return (promising or ranked)[0]


def resolve_email_recipient(
    session: Session,
    *,
    principal: Principal,
    message: str,
    context: dict | None = None,
) -> ResolvedEmailRecipient:
    """Resolve a CRM lead for email drafting without crossing tenants.

    Preference order:
    1. Explicit ``lead_id`` in context (org-scoped)
    2. Recipient email from context or the message
    3. Recipient name from context
    4. Name / company mention in the message
    5. "Most promising lead" / generic lead phrasing
    6. A person name extracted from the message (no CRM facts)
    """
    ctx = context or {}
    leads, _total = lead_service.list_leads(
        session, principal=principal, offset=0, limit=100
    )

    explicit_id = str(ctx.get("lead_id") or "").strip()
    if explicit_id:
        try:
            lead = lead_service.get_lead(
                session, principal=principal, lead_id=explicit_id
            )
        except NotFoundError:
            lead = None
        if lead is not None:
            return _from_lead(lead, match_reason="lead_id", context=ctx)

    explicit_email = _clean(ctx.get("recipient_email")) or lead_service.extract_email(
        message
    )
    if explicit_email:
        matched = _lead_by_email(leads, explicit_email)
        if matched is not None:
            return _from_lead(matched, match_reason="email", context=ctx)

    explicit_name = _clean(ctx.get("recipient_name"))
    if explicit_name:
        matched = _lead_by_name(leads, explicit_name)
        if matched is not None:
            return _from_lead(matched, match_reason="name", context=ctx)

    mentioned = _find_mentioned_lead(message, leads)
    if mentioned is not None:
        reason = "company" if _mentions_company(message, mentioned) and not _mentions_name(
            message, mentioned
        ) else "name"
        return _from_lead(mentioned, match_reason=reason, context=ctx)

    if _PROMISING_RE.search(message or "") or _GENERIC_LEAD_RE.search(message or ""):
        promising = select_most_promising_lead(leads)
        if promising is not None:
            return _from_lead(promising, match_reason="most_promising", context=ctx)

    if explicit_email or explicit_name:
        return ResolvedEmailRecipient(
            recipient_name=explicit_name,
            recipient_email=explicit_email,
            company=_clean(ctx.get("company")),
            facts={},
            match_reason="context_only",
        )

    extracted_name = _extract_person_name(message)
    if extracted_name:
        return ResolvedEmailRecipient(
            recipient_name=extracted_name,
            recipient_email=None,
            company=None,
            facts={},
            match_reason="message_name",
        )

    return ResolvedEmailRecipient(
        recipient_name=None,
        recipient_email=None,
        company=None,
        facts={},
        match_reason="none",
    )


def audience_label(*, recipient_name: str | None, company: str | None) -> str | None:
    """Human-readable 'who' for approval titles. No IDs."""
    name = _clean(recipient_name)
    org = _clean(company)
    if name and org:
        return f"{name} at {org}"
    return name or org


def build_approval_copy(
    *,
    action_type: str,
    recipient_name: str | None,
    company: str | None,
    facts: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Recruiter-friendly approval title and description. No raw IDs."""
    is_send = action_type == "gmail_send_email"
    verb = "Send" if is_send else "Draft"
    who = audience_label(recipient_name=recipient_name, company=company)
    facts = facts or {}

    title = f"{verb} follow-up email to {who}" if who else f"{verb} follow-up email"
    title = _sanitize_facing_text(title)

    if who and facts.get("recommended_next_action"):
        next_step = facts["recommended_next_action"].rstrip(".")
        description = (
            f"{verb} a follow-up email to {who} covering {next_step}. "
            "A teammate must approve before any email is sent."
        )
    elif who and facts.get("pain_point"):
        description = (
            f"{verb} a follow-up email to {who} regarding {facts['pain_point']}. "
            "A teammate must approve before any email is sent."
        )
    elif who:
        description = (
            f"{verb} a follow-up email to {who}. "
            "A teammate must approve before any email is sent."
        )
    else:
        description = (
            f"{verb} a follow-up email. No matching CRM contact was found, "
            "so the draft uses only the request text and does not invent "
            "customer details. A teammate must approve before any email is sent."
        )
    return title[:200], _sanitize_facing_text(description)[:1024]


def format_crm_prompt_block(facts: dict[str, str]) -> str:
    """Prompt block listing only stored CRM facts."""
    labels = {
        "name": "Name",
        "company": "Company",
        "email": "Email",
        "status": "Pipeline status",
        "urgency": "Urgency",
        "intent": "Intent",
        "pain_point": "Known pain point",
        "summary": "CRM summary",
        "recommended_next_action": "Recommended next action",
    }
    lines = [
        "Known CRM context (use only these facts; do not add people, "
        "companies, or outcomes that are not listed):"
    ]
    for key, label in labels.items():
        value = facts.get(key)
        if value:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def sanitize_draft_text(text: str, *, recipient_name: str | None = None) -> str:
    """Remove bracketed template tokens. Never leave [recipient]-style copy."""

    def _replace(match: re.Match[str]) -> str:
        inner = match.group(0)[1:-1].strip().lower()
        if inner in _NAME_LIKE_PLACEHOLDERS and recipient_name:
            return recipient_name
        return ""

    cleaned = _BRACKET_PLACEHOLDER_RE.sub(_replace, text or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r"Hi\s*,", "Hello,", cleaned)
    cleaned = re.sub(r"Hello\s*,", "Hello,", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def contains_placeholder_token(text: str) -> bool:
    """True when bracketed template tokens remain in the text."""
    return bool(_BRACKET_PLACEHOLDER_RE.search(text or ""))


def _from_lead(
    lead: Lead, *, match_reason: str, context: dict
) -> ResolvedEmailRecipient:
    facts = crm_facts_from_lead(lead)
    name = _clean(context.get("recipient_name")) or facts.get("name")
    email = _clean(context.get("recipient_email")) or facts.get("email")
    company = _clean(context.get("company")) or facts.get("company")
    return ResolvedEmailRecipient(
        recipient_name=name,
        recipient_email=email,
        company=company,
        facts=facts,
        match_reason=match_reason,
        lead_id=lead.id,
    )


def _lead_by_email(leads: list[Lead], email: str) -> Lead | None:
    needle = email.strip().lower()
    for lead in leads:
        if (lead.email or "").strip().lower() == needle:
            return lead
    return None


def _lead_by_name(leads: list[Lead], name: str) -> Lead | None:
    needle = _normalize(name)
    if not needle:
        return None
    exact = [lead for lead in leads if _normalize(lead.name) == needle]
    if len(exact) == 1:
        return exact[0]
    first = [
        lead
        for lead in leads
        if (lead.name or "").split() and _normalize((lead.name or "").split()[0]) == needle
    ]
    if len(first) == 1:
        return first[0]
    return exact[0] if exact else None


def _find_mentioned_lead(message: str, leads: list[Lead]) -> Lead | None:
    matches = [lead for lead in leads if _lead_mentioned(message, lead)]
    unique: dict[str, Lead] = {lead.id: lead for lead in matches}
    if len(unique) == 1:
        return next(iter(unique.values()))
    return None


def _lead_mentioned(message: str, lead: Lead) -> bool:
    return _mentions_name(message, lead) or _mentions_company(message, lead)


def _mentions_name(message: str, lead: Lead) -> bool:
    hay = _normalize(message)
    tokens = hay.split()
    full = _normalize(lead.name)
    if full and len(full) >= 3 and full in hay:
        return True
    first = (lead.name or "").split()[0] if lead.name else ""
    return bool(first) and len(first) >= 4 and _normalize(first) in tokens


def _mentions_company(message: str, lead: Lead) -> bool:
    hay = _normalize(message)
    tokens = hay.split()
    full = _normalize(lead.company)
    if full and len(full) >= 3 and full in hay:
        return True
    first = (lead.company or "").split()[0] if lead.company else ""
    return bool(first) and len(first) >= 5 and _normalize(first) in tokens


def _extract_person_name(message: str) -> str | None:
    match = _TO_PERSON_RE.search(message or "")
    if not match:
        return None
    name = match.group(1).strip(" .,")
    if len(name) < 2:
        return None
    return name


def _sanitize_facing_text(text: str) -> str:
    cleaned = sanitize_draft_text(text)
    cleaned = _INTERNAL_ID_RE.sub("", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _normalize(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
