"""Google Calendar tools — availability, slot suggestions, and approval-gated event requests."""

from __future__ import annotations

import time
from typing import Any

from onepilot.services import calendar_service
from onepilot.services.calendar_format import format_availability_response, format_suggestion_response
from onepilot.tools.base import Tool, ToolContext, ToolResult


def _format_proposal_output(raw: dict) -> str:
    payload = raw.get("approval_payload") or {}
    slot = raw.get("selected_slot") or {}
    lines = [
        f"Meeting proposal: {payload.get('summary', 'Meeting')}",
        f"Proposed time: {slot.get('start_time')} – {slot.get('end_time')} ({payload.get('timezone')})",
        f"Provider mode: {raw.get('provider_mode', 'mock')}",
        "This event will be created only after human approval.",
    ]
    attendees = payload.get("attendees") or []
    if attendees:
        lines.append(f"Attendees: {', '.join(str(a) for a in attendees)}")
    return "\n".join(lines)


class CalendarCheckAvailabilityTool(Tool):
    name = "calendar.check_availability"
    description = "Check Google Calendar availability for a time window without creating events."

    def run(
        self,
        ctx: ToolContext,
        *,
        message: str,
        context: dict | None = None,
        **_: Any,
    ) -> ToolResult:
        started = time.monotonic()
        raw = calendar_service.get_availability(
            ctx.session,
            principal=ctx.principal,
            message=message,
            context=context,
            settings=ctx.settings,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        return ToolResult(
            tool_name=self.name,
            input_summary=f"availability check: {message[:120]}",
            output_summary=(
                f"mode={raw.get('mode')} slots={len(raw.get('available_slots') or [])} "
                f"conflicts={raw.get('conflict_count', 0)} busy={raw.get('has_conflicts', False)}"
            ),
            output={
                **raw,
                "provider_mode": raw.get("mode"),
                "latency_ms": duration_ms,
                "approval_required": False,
            },
            duration_ms=duration_ms,
            approval_required=False,
            usage={"feature": "calendar_availability", "fallback_used": raw.get("fallback_used")},
        )


class CalendarSuggestSlotsTool(Tool):
    name = "calendar.suggest_slots"
    description = "Suggest meeting time slots from Google Calendar availability."

    def run(
        self,
        ctx: ToolContext,
        *,
        message: str,
        context: dict | None = None,
        **_: Any,
    ) -> ToolResult:
        started = time.monotonic()
        raw = calendar_service.suggest_slots(
            ctx.session,
            principal=ctx.principal,
            message=message,
            context=context,
            settings=ctx.settings,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        return ToolResult(
            tool_name=self.name,
            input_summary=f"slot suggestion: {message[:120]}",
            output_summary=f"mode={raw.get('mode')} suggested={len(raw.get('suggested_slots') or [])}",
            output={
                **raw,
                "provider_mode": raw.get("mode"),
                "latency_ms": duration_ms,
                "approval_required": False,
            },
            duration_ms=duration_ms,
            approval_required=False,
            usage={"feature": "calendar_suggest_slots", "fallback_used": raw.get("fallback_used")},
        )


class CalendarCreateEventRequestTool(Tool):
    name = "calendar.create_event_request"
    description = (
        "Prepare a Google Calendar meeting proposal. Creates an approval request; "
        "never creates calendar events directly."
    )

    def run(
        self,
        ctx: ToolContext,
        *,
        message: str,
        context: dict | None = None,
        **_: Any,
    ) -> ToolResult:
        started = time.monotonic()
        raw = calendar_service.prepare_event_approval(
            ctx.session,
            principal=ctx.principal,
            message=message,
            context=context,
            settings=ctx.settings,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        approval_action = calendar_service.resolve_approval_action_type()
        payload = raw.get("approval_payload") or {}
        return ToolResult(
            tool_name=self.name,
            input_summary=f"meeting proposal: {message[:120]}",
            output_summary=f"proposal={payload.get('summary', '')[:80]}",
            output={
                **raw,
                "provider_mode": raw.get("provider_mode"),
                "latency_ms": duration_ms,
                "approval_required": True,
            },
            duration_ms=duration_ms,
            approval_required=True,
            approval_action_type=approval_action,
            approval_title=f"Calendar event: {payload.get('summary', 'Meeting')[:80]}",
            approval_payload=payload,
            approval_risk="medium",
            usage={"feature": "calendar_approval_created", "fallback_used": raw.get("fallback_used")},
        )
