"""Workspace insights tool — reads leads, approvals, and conversations."""

from __future__ import annotations

import time
from typing import Any

from onepilot.core.constants import UsageFeature
from onepilot.services import usage_service, workspace_insights_service
from onepilot.tools.base import Tool, ToolContext, ToolResult


class WorkspaceInsightsTool(Tool):
    name = "workspace.insights"
    description = (
        "Summarize seeded workspace activity: leads, pending approvals, and conversations."
    )

    def run(
        self,
        ctx: ToolContext,
        *,
        message: str,
        **_: Any,
    ) -> ToolResult:
        started = time.monotonic()
        payload = workspace_insights_service.build_insights(
            ctx.session, principal=ctx.principal, query=message
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        usage_service.record(
            ctx.session,
            organization_id=ctx.principal.organization_id,
            user_id=ctx.principal.user_id,
            feature=UsageFeature.TOOL_CALLS.value,
            provider="workspace_insights",
            tool_calls=1,
            fallback_used=False,
            latency_ms=duration_ms,
            metadata={"focus": payload.get("focus")},
        )
        return ToolResult(
            tool_name=self.name,
            input_summary=f"workspace insights: {message[:120]}",
            output_summary=(
                f"leads={payload['lead_count']} pending={payload['pending_approvals']} "
                f"conversations={payload['conversation_count']}"
            ),
            output=payload,
            duration_ms=duration_ms,
            usage={
                "provider": "workspace_insights",
                "tool_calls": 1,
                "fallback_used": False,
            },
        )
