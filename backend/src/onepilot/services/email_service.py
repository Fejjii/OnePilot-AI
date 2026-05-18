"""Email drafting service.

Builds a structured :class:`EmailDraft`. Emails are **never sent** here. If
the caller requests an action that would send (or perform an external action),
the agent layer must create an approval request before any external call.
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

logger = get_logger(__name__)

VALID_TONES = ("professional", "friendly", "concise", "warm", "formal")
DEFAULT_TONE = "professional"


@dataclass(slots=True)
class EmailDraftOutcome:
    draft: EmailDraft
    fallback_used: bool
    model: str


def _system_prompt(tone: str) -> str:
    tone = tone if tone in VALID_TONES else DEFAULT_TONE
    return (
        "You are an email drafting assistant for a SaaS company. Write a "
        f"{tone}, on-brand email. Use clear paragraphs. Do not invent facts. "
        "Return only the subject line and body. Use [recipient] as a placeholder "
        "when no recipient name is provided. Never claim the email has been sent."
    )


def _build_user_prompt(
    context: str,
    *,
    recipient_name: str | None,
    citations_block: str | None,
) -> str:
    parts: list[str] = [f"Context: {context.strip()}"]
    if recipient_name:
        parts.append(f"Recipient: {recipient_name}")
    else:
        parts.append("Recipient: [recipient]")
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
    context: str, tone: str, recipient_name: str | None
) -> tuple[str, str]:
    greeting = f"Hi {recipient_name}" if recipient_name else "Hi [recipient]"
    subject = f"Following up on {context.strip().split('.')[0][:60]}" or "Quick follow up"
    body = (
        f"{greeting},\n\n"
        f"Thanks for reaching out. Based on your note ({context.strip()[:200]}), "
        "here is a quick summary and next step from our side. "
        "Please let me know if this works for you, or if you'd like to schedule a "
        "short call to walk through it.\n\nBest regards,\nThe OnePilot team"
    )
    return subject, body


def draft_email(
    session: Session,
    *,
    principal: Principal,
    context: str,
    tone: str = DEFAULT_TONE,
    recipient_name: str | None = None,
    recipient_email: str | None = None,
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

    started = time.monotonic()
    if is_fallback:
        subject, body = _fallback_draft(context, tone, recipient_name)
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
                {"role": "system", "content": _system_prompt(tone)},
                {
                    "role": "user",
                    "content": _build_user_prompt(
                        context,
                        recipient_name=recipient_name,
                        citations_block=citations_block,
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=600,
        )
        subject, body = _parse_subject_body(response.content)
        model_name = response.model
        input_tokens = response.input_tokens
        output_tokens = response.output_tokens

    latency_ms = int((time.monotonic() - started) * 1000)

    draft = EmailDraft(
        subject=subject,
        body=body,
        tone=tone,
        recipient_placeholder=recipient_name or "[recipient]",
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
        },
    )
    logger.info(
        "email_drafted",
        organization_id=principal.organization_id,
        fallback=is_fallback,
        subject_len=len(subject),
    )
    return EmailDraftOutcome(draft=draft, fallback_used=is_fallback, model=model_name)
