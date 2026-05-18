"""Lead support tool.

Classifies a chat-derived lead, decides whether the message clearly asks to
capture/qualify a lead, and (when so) persists a lead row. Approval is not
required to *capture* a lead, but external CRM sync is gated upstream.
"""

from __future__ import annotations

import re
import time
from typing import Any

from onepilot.services import lead_service
from onepilot.tools.base import Tool, ToolContext, ToolResult

# Phrases that indicate the user explicitly wants to capture/qualify a lead.
_CAPTURE_TRIGGERS = (
    "capture this lead",
    "add this lead",
    "save this lead",
    "qualify this lead",
    "create a lead",
    "log this lead",
    "track this lead",
    "new lead",
    "this is a lead",
)


class LeadSupportTool(Tool):
    name = "lead.support"
    description = (
        "Classify and (optionally) capture a sales lead. "
        "Returns a recommended next action."
    )

    def run(
        self,
        ctx: ToolContext,
        *,
        message: str,
        name: str | None = None,
        email: str | None = None,
        company: str | None = None,
        force_capture: bool = False,
        **_: Any,
    ) -> ToolResult:
        started = time.monotonic()
        classification = lead_service.classify_lead(message, name=name)
        derived_email = email or lead_service.extract_email(message)
        derived_name = name or _guess_name(message) or "Unknown Lead"

        should_capture = force_capture or _wants_capture(message)
        lead_id: str | None = None
        captured = False
        if should_capture:
            lead = lead_service.create_lead(
                ctx.session,
                principal=ctx.principal,
                name=derived_name,
                email=derived_email,
                company=company,
                source="chat",
                urgency=classification.urgency,
                intent=classification.intent,
                pain_point=classification.pain_point,
                summary=classification.summary,
                recommended_next_action=classification.recommended_next_action,
            )
            lead_id = lead.id
            captured = True

        duration_ms = int((time.monotonic() - started) * 1000)
        return ToolResult(
            tool_name=self.name,
            input_summary=f"lead message: {message[:120]}",
            output_summary=(
                f"urgency={classification.urgency} intent={classification.intent or 'unknown'} "
                f"captured={captured}"
            ),
            output={
                "captured": captured,
                "lead_id": lead_id,
                "name": derived_name,
                "email": derived_email,
                "urgency": classification.urgency,
                "intent": classification.intent,
                "pain_point": classification.pain_point,
                "summary": classification.summary,
                "recommended_next_action": classification.recommended_next_action,
            },
            duration_ms=duration_ms,
            usage={"captured": captured, "urgency": classification.urgency},
        )


def _wants_capture(message: str) -> bool:
    lowered = (message or "").lower()
    return any(trigger in lowered for trigger in _CAPTURE_TRIGGERS)


_NAME_RE = re.compile(
    r"\b(?:from|name is|i am|this is|met with|talked to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    re.IGNORECASE,
)


def _guess_name(message: str) -> str | None:
    match = _NAME_RE.search(message or "")
    return match.group(1).strip().title() if match else None
