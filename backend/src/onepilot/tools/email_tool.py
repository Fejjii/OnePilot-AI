"""Email draft tool.

Produces a structured :class:`EmailDraft`. Always proposes an approval; never
sends. Optionally pulls grounding citations from the RAG tool when context
sounds like an FAQ/knowledge question.
"""

from __future__ import annotations

import time
from typing import Any

from onepilot.services import email_service
from onepilot.tools.base import Tool, ToolContext, ToolResult


class EmailDraftTool(Tool):
    name = "email.draft"
    description = (
        "Draft a structured email (subject + body) for the user. Never sends. "
        "Always proposes an approval gate when the user implies sending."
    )

    def run(
        self,
        ctx: ToolContext,
        *,
        context: str,
        tone: str = "professional",
        recipient_name: str | None = None,
        recipient_email: str | None = None,
        action: str = "draft_only",
        citations: list[dict] | None = None,
        **_: Any,
    ) -> ToolResult:
        started = time.monotonic()
        outcome = email_service.draft_email(
            ctx.session,
            principal=ctx.principal,
            context=context,
            tone=tone,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            citations=citations,
            settings=ctx.settings,
        )
        duration_ms = int((time.monotonic() - started) * 1000)

        # Approval is required when the user wants to actually send; for
        # draft-only we still *propose* one so the user can opt-in from the UI
        # without re-drafting.
        approval_required = action != "draft_only"
        approval_action = "send_email"

        proposed_payload = {
            "subject": outcome.draft.subject,
            "body": outcome.draft.body,
            "tone": outcome.draft.tone,
            "recipient_name": recipient_name,
            "recipient_email": recipient_email,
        }

        return ToolResult(
            tool_name=self.name,
            input_summary=f"draft email for context: {context[:120]}",
            output_summary=f"subject={outcome.draft.subject[:80]}",
            output={
                "draft": outcome.draft.model_dump(),
                "model": outcome.model,
                "fallback_used": outcome.fallback_used,
            },
            duration_ms=duration_ms,
            approval_required=approval_required,
            approval_action_type=approval_action,
            approval_title=f"Send email: {outcome.draft.subject[:80]}",
            approval_payload=proposed_payload,
            approval_risk="medium",
            safety_flags=["fallback_used"] if outcome.fallback_used else [],
            usage={"model": outcome.model, "fallback_used": outcome.fallback_used},
        )
