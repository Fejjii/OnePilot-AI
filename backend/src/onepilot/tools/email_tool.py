"""Email draft tool.

Produces a structured :class:`EmailDraft`. Never sends to Gmail directly.
Send / Gmail draft creation requires human approval via the approval workflow.
"""

from __future__ import annotations

import time
from typing import Any

from onepilot.core.config import get_settings
from onepilot.services import email_service, gmail_service
from onepilot.tools.base import Tool, ToolContext, ToolResult


class EmailDraftTool(Tool):
    name = "email.draft"
    description = (
        "Draft a structured email (subject + body) for the user. Never sends. "
        "Gmail actions require human approval before any external email operation."
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

        settings = ctx.settings or get_settings()
        approval_required = action != "draft_only"
        approval_action = gmail_service.resolve_approval_action_type(
            action,
            force_send=action == "send" and settings.GMAIL_SEND_ENABLED,
        )

        proposed_payload = gmail_service.build_approval_payload(
            subject=outcome.draft.subject,
            body=outcome.draft.body,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            tone=outcome.draft.tone,
            action_type=approval_action,
        )

        return ToolResult(
            tool_name=self.name,
            input_summary=f"draft email for context: {context[:120]}",
            output_summary=f"subject={outcome.draft.subject[:80]}",
            output={
                "draft": outcome.draft.model_dump(),
                "model": outcome.model,
                "fallback_used": outcome.fallback_used,
                "gmail_action_pending": approval_required,
            },
            duration_ms=duration_ms,
            approval_required=approval_required,
            approval_action_type=approval_action,
            approval_title=f"Gmail action: {outcome.draft.subject[:80]}",
            approval_payload=proposed_payload,
            approval_risk="high" if approval_action == "gmail_send_email" else "medium",
            safety_flags=["fallback_used"] if outcome.fallback_used else [],
            usage={"model": outcome.model, "fallback_used": outcome.fallback_used},
        )
