"""Google Calendar business logic — validates payloads and calls the calendar provider."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import UsageFeature
from onepilot.core.errors import ValidationError
from onepilot.core.logging import get_logger
from onepilot.providers import get_calendar_provider
from onepilot.providers.calendar.mock_calendar_provider import MockCalendarProvider
from onepilot.providers.calendar.time_parser import parse_calendar_window
from onepilot.repositories.models import ApprovalRequest
from onepilot.schemas.calendar import (
    CalendarApprovalPayload,
    CalendarAvailabilityRequest,
    CalendarCreateEventRequest,
    CalendarCreateEventResult,
    CalendarSlotSuggestionRequest,
)
from onepilot.security.auth import Principal
from onepilot.services import audit_service, usage_service

log = get_logger(__name__)

_AVAILABILITY_INTENT = re.compile(
    r"\b(am i free|are we free|availability|available|busy|free tomorrow|free next)\b",
    re.IGNORECASE,
)
_SUGGEST_SLOTS_INTENT = re.compile(
    r"\b(suggest|propose|offer|recommend).{0,30}\b(slot|time|times)\b",
    re.IGNORECASE,
)
_SCHEDULE_INTENT = re.compile(
    r"\b(schedule|book a|book (the|an?)|set up a|create a).{0,40}\b(meeting|call|appointment)\b",
    re.IGNORECASE,
)
_DURATION_MINUTES = re.compile(r"\b(\d{1,3})\s*(?:minute|min)\b", re.IGNORECASE)
_MAX_SLOTS = re.compile(r"\b(\d{1,2})\s+(?:meeting )?slots?\b", re.IGNORECASE)


def infer_calendar_tool(message: str, context: dict | None = None) -> str:
    """Return tool name suffix: check_availability, suggest_slots, or create_event_request."""
    ctx = context or {}
    explicit = ctx.get("calendar_tool")
    if explicit in {"check_availability", "suggest_slots", "create_event_request"}:
        return str(explicit)

    if _SUGGEST_SLOTS_INTENT.search(message):
        return "suggest_slots"
    if _AVAILABILITY_INTENT.search(message) and not _SCHEDULE_INTENT.search(message):
        return "check_availability"
    if _SCHEDULE_INTENT.search(message):
        return "create_event_request"
    return "suggest_slots"


def resolve_approval_action_type() -> str:
    return "calendar_create_event"


def _default_timezone(settings: Settings) -> str:
    return settings.GOOGLE_CALENDAR_DEFAULT_TIMEZONE or "Europe/Berlin"


def _parse_time_window(
    message: str, settings: Settings
) -> tuple[datetime, datetime, str, str]:
    """Best-effort window from message cues; returns (min, max, query_type, label)."""
    parsed = parse_calendar_window(
        message,
        timezone=_default_timezone(settings),
        lookahead_days=int(settings.GOOGLE_CALENDAR_LOOKAHEAD_DAYS),
        slot_duration_minutes=int(settings.GOOGLE_CALENDAR_SLOT_DURATION_MINUTES),
    )
    return parsed.time_min, parsed.time_max, parsed.query_type, parsed.label


def _localize_slot_for_display(
    utc_naive: datetime, *, timezone: str
) -> datetime:
    """Convert UTC-naive API timestamps to local wall-clock for user-facing output."""
    tz = ZoneInfo(timezone)
    return utc_naive.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)


def _parse_duration_minutes(message: str, settings: Settings) -> int:
    match = _DURATION_MINUTES.search(message)
    if match:
        return max(15, min(480, int(match.group(1))))
    return int(settings.GOOGLE_CALENDAR_SLOT_DURATION_MINUTES)


def _parse_max_slots(message: str) -> int:
    match = _MAX_SLOTS.search(message)
    if match:
        return max(1, min(20, int(match.group(1))))
    return 3


def _infer_summary(message: str, context: dict | None = None) -> str:
    ctx = context or {}
    if ctx.get("meeting_summary"):
        return str(ctx["meeting_summary"])[:200]
    if "lead" in message.lower():
        return "Follow-up meeting with high priority lead"
    return "OnePilot scheduled meeting"


def _infer_attendees(context: dict | None) -> list[str]:
    ctx = context or {}
    raw = ctx.get("attendees") or ctx.get("recipient_email")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()][:10]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def build_approval_payload(
    *,
    summary: str,
    start_time: datetime,
    end_time: datetime,
    timezone: str,
    attendees: list[str] | None = None,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str | None = None,
    action_type: str = "calendar_create_event",
    reason: str = "",
) -> dict:
    try:
        payload = CalendarApprovalPayload(
            action_type=action_type,  # type: ignore[arg-type]
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            attendees=attendees or [],  # type: ignore[arg-type]
            description=description,
            location=location,
            calendar_id=calendar_id,
            reason=reason,
        )
    except PydanticValidationError as exc:
        raise ValidationError(f"Invalid calendar approval payload: {exc}") from exc
    return payload.model_dump(mode="json")


def get_availability(
    session: Session,
    *,
    principal: Principal,
    message: str,
    context: dict | None = None,
    settings: Settings | None = None,
) -> dict:
    cfg = settings or get_settings()
    time_min, time_max, query_type, window_label = _parse_time_window(message, cfg)
    try:
        request = CalendarAvailabilityRequest(
            time_min=time_min,
            time_max=time_max,
            timezone=_default_timezone(cfg),
            workday_start=cfg.GOOGLE_CALENDAR_WORKDAY_START,
            workday_end=cfg.GOOGLE_CALENDAR_WORKDAY_END,
            slot_duration_minutes=int(cfg.GOOGLE_CALENDAR_SLOT_DURATION_MINUTES),
            calendar_id=cfg.GOOGLE_CALENDAR_ID or "primary",
        )
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc

    provider = get_calendar_provider(cfg)
    raw = provider.get_availability(
        request.time_min,
        request.time_max,
        timezone=request.timezone,
        workday_start=request.workday_start,
        workday_end=request.workday_end,
        slot_duration_minutes=request.slot_duration_minutes,
        calendar_id=request.calendar_id,
        query_type=query_type,
    )
    raw["query_type"] = query_type
    raw["window_label"] = window_label
    raw["time_min"] = request.time_min.isoformat()
    raw["time_max"] = request.time_max.isoformat()
    _track_usage(
        session,
        principal,
        UsageFeature.CALENDAR_AVAILABILITY.value,
        raw,
        settings=cfg,
    )
    _record_audit(
        session,
        principal,
        event="calendar.availability_checked",
        result=raw,
    )
    return raw


def suggest_slots(
    session: Session,
    *,
    principal: Principal,
    message: str,
    context: dict | None = None,
    settings: Settings | None = None,
) -> dict:
    cfg = settings or get_settings()
    time_min, time_max, _, window_label = _parse_time_window(message, cfg)
    duration = _parse_duration_minutes(message, cfg)
    max_slots = _parse_max_slots(message)
    try:
        request = CalendarSlotSuggestionRequest(
            time_min=time_min,
            time_max=time_max,
            timezone=_default_timezone(cfg),
            duration_minutes=duration,
            max_slots=max_slots,
            workday_start=cfg.GOOGLE_CALENDAR_WORKDAY_START,
            workday_end=cfg.GOOGLE_CALENDAR_WORKDAY_END,
            calendar_id=cfg.GOOGLE_CALENDAR_ID or "primary",
        )
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc

    provider = get_calendar_provider(cfg)
    raw = provider.suggest_slots(
        request.time_min,
        request.time_max,
        timezone=request.timezone,
        duration_minutes=request.duration_minutes,
        max_slots=request.max_slots,
        workday_start=request.workday_start,
        workday_end=request.workday_end,
        calendar_id=request.calendar_id,
    )
    _track_usage(
        session,
        principal,
        UsageFeature.CALENDAR_SUGGEST_SLOTS.value,
        raw,
        settings=cfg,
    )
    _record_audit(
        session,
        principal,
        event="calendar.slots_suggested",
        result=raw,
    )
    raw["window_label"] = window_label
    return raw


def prepare_event_approval(
    session: Session,
    *,
    principal: Principal,
    message: str,
    context: dict | None = None,
    settings: Settings | None = None,
) -> dict:
    cfg = settings or get_settings()
    time_min, time_max, query_type, window_label = _parse_time_window(message, cfg)
    duration = _parse_duration_minutes(message, cfg)
    timezone = _default_timezone(cfg)
    provider = get_calendar_provider(cfg)

    if query_type == "specific":
        start_time = time_min
        parsed_duration = (time_max - time_min).total_seconds() / 60
        if parsed_duration >= duration:
            end_time = time_max
        else:
            end_time = start_time + timedelta(minutes=duration)
        suggestion = {"mode": getattr(provider, "_mode", "mock"), "suggested_slots": []}
    elif window_label == "tomorrow afternoon":
        start_time = time_min.replace(hour=13, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=duration)
        suggestion = provider.suggest_slots(
            time_min,
            time_max,
            timezone=timezone,
            duration_minutes=duration,
            max_slots=1,
            workday_start=cfg.GOOGLE_CALENDAR_WORKDAY_START,
            workday_end=cfg.GOOGLE_CALENDAR_WORKDAY_END,
            calendar_id=cfg.GOOGLE_CALENDAR_ID or "primary",
        )
        slots = suggestion.get("suggested_slots") or []
        if slots:
            start_raw = (
                slots[0].get("start_time")
                if isinstance(slots[0], dict)
                else slots[0].start_time
            )
            end_raw = (
                slots[0].get("end_time")
                if isinstance(slots[0], dict)
                else slots[0].end_time
            )
            start_time = datetime.fromisoformat(
                str(start_raw).replace("Z", "+00:00")
            ).replace(tzinfo=None)
            end_time = datetime.fromisoformat(
                str(end_raw).replace("Z", "+00:00")
            ).replace(tzinfo=None)
    else:
        suggestion = provider.suggest_slots(
            time_min,
            time_max,
            timezone=timezone,
            duration_minutes=duration,
            max_slots=1,
            workday_start=cfg.GOOGLE_CALENDAR_WORKDAY_START,
            workday_end=cfg.GOOGLE_CALENDAR_WORKDAY_END,
            calendar_id=cfg.GOOGLE_CALENDAR_ID or "primary",
        )
        slots = suggestion.get("suggested_slots") or []
        if slots:
            start_raw = (
                slots[0].get("start_time")
                if isinstance(slots[0], dict)
                else slots[0].start_time
            )
            end_raw = (
                slots[0].get("end_time")
                if isinstance(slots[0], dict)
                else slots[0].end_time
            )
            start_time = datetime.fromisoformat(
                str(start_raw).replace("Z", "+00:00")
            ).replace(tzinfo=None)
            end_time = datetime.fromisoformat(
                str(end_raw).replace("Z", "+00:00")
            ).replace(tzinfo=None)
        else:
            start_time = time_min.replace(hour=10, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(minutes=duration)

    payload = build_approval_payload(
        summary=_infer_summary(message, context),
        start_time=start_time,
        end_time=end_time,
        timezone=_default_timezone(cfg),
        attendees=_infer_attendees(context),
        description=f"Proposed from agent request: {message[:500]}",
        calendar_id=cfg.GOOGLE_CALENDAR_ID or "primary",
        action_type=resolve_approval_action_type(),
        reason="Calendar event creation requires human approval.",
    )
    _track_usage(
        session,
        principal,
        UsageFeature.CALENDAR_APPROVAL_CREATED.value,
        {"status": "pending", "mode": suggestion.get("mode", "mock")},
        settings=cfg,
    )
    _record_audit(
        session,
        principal,
        event="calendar.approval_created",
        result={"status": "pending", "summary": payload.get("summary")},
    )
    display_start = _localize_slot_for_display(start_time, timezone=timezone)
    display_end = _localize_slot_for_display(end_time, timezone=timezone)
    return {
        "approval_payload": payload,
        "selected_slot": {
            "start_time": display_start.isoformat(),
            "end_time": display_end.isoformat(),
        },
        "provider_mode": suggestion.get("mode", "mock"),
        "timezone": timezone,
        "fallback_used": bool(suggestion.get("fallback_used")),
        "approval_status": "pending",
    }


def execute_approval_action(
    session: Session,
    *,
    principal: Principal,
    approval: ApprovalRequest,
    settings: Settings | None = None,
) -> dict:
    """Run calendar event creation after human approval."""
    cfg = settings or get_settings()
    if not cfg.GOOGLE_CALENDAR_CREATE_ENABLED:
        return CalendarCreateEventResult(
            mode="live",
            status="error",
            error_code="create_disabled",
            safe_error_message="Calendar event creation is disabled in server configuration.",
        ).model_dump(mode="json")

    payload_raw = dict(approval.proposed_payload or {})
    try:
        req = CalendarCreateEventRequest(
            summary=str(payload_raw.get("summary") or "Meeting"),
            start_time=payload_raw["start_time"],
            end_time=payload_raw["end_time"],
            timezone=str(payload_raw.get("timezone") or _default_timezone(cfg)),
            attendees=payload_raw.get("attendees") or [],
            description=payload_raw.get("description"),
            location=payload_raw.get("location"),
            calendar_id=payload_raw.get("calendar_id") or cfg.GOOGLE_CALENDAR_ID,
        )
    except (KeyError, PydanticValidationError) as exc:
        result = CalendarCreateEventResult(
            status="error",
            error_code="validation_error",
            safe_error_message="Invalid calendar fields in approval payload.",
        ).model_dump(mode="json")
        _record_audit(session, principal, event="calendar.provider_failed", result=result)
        return result

    provider = get_calendar_provider(cfg)
    raw = provider.create_event(
        req.summary,
        req.start_time,
        req.end_time,
        timezone=req.timezone,
        attendees=[str(a) for a in req.attendees],
        description=req.description,
        location=req.location,
        calendar_id=req.calendar_id,
    )
    result = _normalize_provider_result(raw)
    feature = (
        UsageFeature.CALENDAR_CREATE_EVENT.value
        if result.get("status") == "success"
        else UsageFeature.CALENDAR_APPROVAL_EXECUTED.value
    )
    _track_usage(session, principal, feature, result, settings=cfg)
    event_name = (
        "calendar.event_created"
        if result.get("status") == "success"
        else "calendar.provider_failed"
    )
    _record_audit(session, principal, event=event_name, result=result)
    return result


def _normalize_provider_result(raw: dict) -> dict:
    if "status" in raw and "provider" in raw:
        return dict(raw)
    return CalendarCreateEventResult(
        mode="mock" if raw.get("fallback_used") else "live",
        status="success" if not raw.get("error") else "error",
        event_id=raw.get("event_id") or raw.get("id"),
        summary=raw.get("summary"),
        fallback_used=bool(raw.get("fallback_used")),
        safe_error_message=raw.get("error") or raw.get("safe_error_message"),
        error_code=raw.get("error_code"),
    ).model_dump(mode="json")


def _track_usage(
    session: Session,
    principal: Principal,
    feature: str,
    result: dict,
    *,
    settings: Settings,
) -> None:
    provider = get_calendar_provider(settings)
    provider_name = "google_calendar"
    if isinstance(provider, MockCalendarProvider):
        provider_name = "google_calendar_mock"
    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=feature,
        provider=provider_name,
        tool_calls=1,
        fallback_used=bool(result.get("fallback_used")),
        metadata={"status": result.get("status"), "mode": result.get("mode")},
    )


def _record_audit(
    session: Session,
    principal: Principal,
    *,
    event: str,
    result: dict,
) -> None:
    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action=event,
        resource_type="calendar_event",
        resource_id=str(result.get("event_id") or ""),
        detail={
            "status": result.get("status"),
            "mode": result.get("mode"),
            "error_code": result.get("error_code"),
            "summary": result.get("summary"),
        },
    )
    if result.get("status") == "error":
        log.warning(
            "calendar_action_failed",
            error_code=result.get("error_code"),
        )
