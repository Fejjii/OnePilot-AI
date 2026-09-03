"""Email drafting service.

Builds a structured :class:`EmailDraft`. Emails are **never sent** here. If
the caller requests an action that would send (or perform an external action),
the agent layer must create an approval request before any external call.

Drafts are grounded in tenant-scoped CRM facts when a matching lead exists.
The service never invents customer details or emits bracketed placeholders.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import UsageFeature
from onepilot.core.logging import get_logger
from onepilot.providers import get_llm_provider
from onepilot.providers.llm.base import LLMProvider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.schemas.email import EmailDraft
from onepilot.security.auth import Principal
from onepilot.services import quota_service, usage_service
from onepilot.services.crm_email_grounding import (
    format_crm_prompt_block,
    sanitize_draft_text,
)

logger = get_logger(__name__)

VALID_TONES = ("professional", "friendly", "concise", "warm", "formal")
DEFAULT_TONE = "professional"


@dataclass(slots=True)
class EmailDraftOutcome:
    draft: EmailDraft
    fallback_used: bool
    model: str


def _system_prompt(tone: str, *, has_recipient: bool) -> str:
    tone = tone if tone in VALID_TONES else DEFAULT_TONE
    greeting_rule = (
        "Address the recipient by the provided name."
        if has_recipient
        else (
            "Use a generic greeting such as Hello, — do not invent a "
            "recipient name, company, or outcome."
        )
    )
    return (
        "You are an email drafting assistant for a SaaS company. Write a "
        f"{tone}, on-brand email. Use clear paragraphs. Do not invent facts. "
        "Only use people, companies, pain points, and next steps that are "
        "explicitly provided. If a detail is missing, omit it rather than "
        "guessing. Never use bracketed placeholders such as [recipient] or "
        f"[relevant outcome]. {greeting_rule} Return only the subject line "
        "and body. Never claim the email has been sent."
    )


def _build_user_prompt(
    context: str,
    *,
    recipient_name: str | None,
    recipient_email: str | None,
    citations_block: str | None,
    crm_facts: dict[str, str] | None,
) -> str:
    parts: list[str] = [f"Request: {context.strip()}"]
    if recipient_name:
        parts.append(f"Recipient name: {recipient_name}")
    if recipient_email:
        parts.append(f"Recipient email: {recipient_email}")
    if crm_facts:
        parts.append(format_crm_prompt_block(crm_facts))
    else:
        parts.append(
            "No CRM record was found. Do not invent a customer, company, "
            "pain point, or outcome. Write a generic professional follow-up "
            "that only reflects the user's request."
        )
    if citations_block:
        parts.append(f"Reference material:\n{citations_block}")
    parts.append(
        "Write a Subject: line, then a blank line, then the body. Keep it under 220 words."
    )
    return "\n\n".join(parts)


def _parse_subject_body(text: str) -> tuple[str, str]:
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    subject = ""
    body_lines: list[str] = []
    for line in lines:
        if not subject and line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            continue
        body_lines.append(line)
    if not subject:
        subject = "Following up"
    body = "\n".join(body_lines).strip()
    return subject, body


def _fallback_draft(
    context: str,
    tone: str,
    recipient_name: str | None,
    crm_facts: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Deterministic draft using only provided CRM facts and the request."""
    facts = crm_facts or {}
    name = recipient_name or facts.get("name")
    company = facts.get("company")
    pain = facts.get("pain_point")
    next_action = facts.get("recommended_next_action")

    greeting = f"Hi {name}," if name else "Hello,"
    if company:
        subject = f"Following up with {company}"
    elif name:
        subject = f"Following up with {name}"
    else:
        subject = "Following up"

    paragraphs: list[str] = [greeting, ""]
    if company:
        paragraphs.append(f"I wanted to follow up with you at {company}.")
    else:
        paragraphs.append("I wanted to follow up as you requested.")

    if pain:
        paragraphs.append(f"You mentioned {pain[0].lower() + pain[1:] if pain else pain}.")
    if next_action:
        paragraphs.append(f"Suggested next step: {next_action}")
    elif "intro" in context.lower() or "call" in context.lower() or "schedul" in context.lower():
        paragraphs.append(
            "If a short intro call would help, please share a time that works."
        )
    else:
        paragraphs.append("Please let me know if a short conversation would be helpful.")

    paragraphs.append("\nBest regards,\nThe OnePilot team")
    body = "\n".join(paragraphs)
    return subject, body


def _finalize_subject_body(
    subject: str,
    body: str,
    *,
    recipient_name: str | None,
) -> tuple[str, str]:
    subject = sanitize_draft_text(subject, recipient_name=recipient_name) or "Following up"
    body = sanitize_draft_text(body, recipient_name=recipient_name)
    return subject, body


def draft_email(
    session: Session,
    *,
    principal: Principal,
    context: str,
    tone: str = DEFAULT_TONE,
    recipient_name: str | None = None,
    recipient_email: str | None = None,
    crm_facts: dict[str, str] | None = None,
    citations: list[dict] | None = None,
    settings: Settings,
    llm: LLMProvider | None = None,
    enforce_quota: bool = True,
) -> EmailDraftOutcome:
    if enforce_quota:
        quota_service.check_and_increment(
            session,
            principal.organization_id,
            UsageFeature.EMAIL_DRAFTS,
            amount=1,
        )

    tone = tone if tone in VALID_TONES else DEFAULT_TONE
    llm = llm or get_llm_provider(settings)
    is_fallback = isinstance(llm, FallbackLLMProvider)
    facts = {k: v for k, v in (crm_facts or {}).items() if v and str(v).strip()}

    started = time.monotonic()
    if is_fallback:
        subject, body = _fallback_draft(context, tone, recipient_name, facts)
        model_name = "fallback-email-v1"
        input_tokens = max(1, len(context) // 4)
        output_tokens = max(1, len(body) // 4)
    else:
        citations_block = None
        if citations:
            citations_block = "\n".join(
                f"- {c.get('document_title', 'Source')}: {c.get('chunk_text', '')[:200]}"
                for c in citations[:3]
            )
        response = llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": _system_prompt(tone, has_recipient=bool(recipient_name)),
                },
                {
                    "role": "user",
                    "content": _build_user_prompt(
                        context,
                        recipient_name=recipient_name,
                        recipient_email=recipient_email,
                        citations_block=citations_block,
                        crm_facts=facts or None,
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=600,
        )
        subject, body = _parse_subject_body(response.content or "")
        if not body.strip():
            logger.warning(
                "email_empty_llm_content",
                organization_id=principal.organization_id,
                model=response.model,
                finish_reason=response.finish_reason,
                output_tokens=response.output_tokens,
            )
            subject, body = _fallback_draft(context, tone, recipient_name, facts)
        model_name = response.model
        input_tokens = response.input_tokens
        output_tokens = response.output_tokens

    latency_ms = int((time.monotonic() - started) * 1000)

    if not body.strip():
        subject, body = _fallback_draft(context, tone, recipient_name, facts)

    subject, body = _finalize_subject_body(
        subject, body, recipient_name=recipient_name
    )
    if not body.strip():
        subject, body = _finalize_subject_body(
            *_fallback_draft(context, tone, recipient_name, facts),
            recipient_name=recipient_name,
        )

    draft = EmailDraft(
        subject=subject,
        body=body,
        tone=tone,
        recipient_placeholder=recipient_name or "",
        context_used=[context.strip()[:200]],
        citations=[],
        risk_level="medium",
        approval_required=True,
    )

    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=UsageFeature.EMAIL_DRAFTS.value,
        model=model_name,
        provider=type(llm).__name__,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        fallback_used=is_fallback,
        latency_ms=latency_ms,
        metadata={
            "tone": tone,
            "recipient_email": recipient_email,
            "crm_grounded": bool(facts),
        },
    )
    logger.info(
        "email_drafted",
        organization_id=principal.organization_id,
        fallback=is_fallback,
        subject_len=len(subject),
        crm_grounded=bool(facts),
    )
    return EmailDraftOutcome(draft=draft, fallback_used=is_fallback, model=model_name)
