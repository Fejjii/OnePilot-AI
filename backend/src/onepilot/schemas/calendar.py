"""Google Calendar schemas — strict validation for provider I/O and approvals."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

_MAX_SUMMARY = 200
_MAX_DESCRIPTION = 4000
_MAX_LOCATION = 500
_MAX_ATTENDEES = 10
_MAX_SLOTS = 20
_MIN_DURATION_MINUTES = 15
_MAX_DURATION_MINUTES = 480

_CALENDAR_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._@\-]+$")


CalendarStatusReason = Literal[
    "missing_google_client_id",
    "missing_google_client_secret",
    "missing_refresh_token",
    "missing_calendar_scope",
    "calendar_api_disabled_or_forbidden",
    "invalid_refresh_token",
    "token_refresh_failed",
    "calendar_api_error",
    "timezone_error",
    "unknown",
]


class CalendarProviderStatus(BaseModel):
    """Safe calendar provider status for diagnostics."""

    model_config = ConfigDict(extra="forbid")

    configured: bool = False
    mode: Literal["live", "mock", "missing", "unhealthy"] = "missing"
    active: bool = False
    fallback_used: bool = True
    calendar_id: str = "primary"
    create_enabled: bool = False
    status_reason: CalendarStatusReason | None = None
    scope_check_ok: bool | None = None
    capabilities: dict[str, bool] = Field(
        default_factory=lambda: {
            "availability_check": True,
            "suggest_slots": True,
            "create_event": False,
            "requires_approval_for_create": True,
        }
    )
    purpose: str = "Availability checks and approval-gated event creation"


class CalendarEventAttendee(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    optional: bool = False


class CalendarEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    attendees: list[str] = Field(default_factory=list)
    location: str | None = None
    description: str | None = None


class CalendarAvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_min: datetime
    time_max: datetime
    timezone: str = "Europe/Berlin"
    workday_start: str = "09:00"
    workday_end: str = "17:00"
    slot_duration_minutes: int = Field(default=30, ge=_MIN_DURATION_MINUTES, le=_MAX_DURATION_MINUTES)
    calendar_id: str | None = None

    @field_validator("calendar_id")
    @classmethod
    def _sanitize_calendar_id(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        if not _CALENDAR_ID_PATTERN.match(cleaned):
            raise ValueError("Invalid calendar_id format")
        return cleaned

    @model_validator(mode="after")
    def _validate_range(self) -> CalendarAvailabilityRequest:
        if self.time_min >= self.time_max:
            raise ValueError("time_min must be before time_max")
        return self


class CalendarSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_time: datetime
    end_time: datetime
    available: bool = True


class CalendarAvailabilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "google_calendar"
    mode: Literal["live", "mock", "missing", "unhealthy"] = "mock"
    timezone: str
    busy_events: list[CalendarEvent] = Field(default_factory=list)
    available_slots: list[CalendarSlot] = Field(default_factory=list)
    fallback_used: bool = False
    latency_ms: int = 0
    status: Literal["success", "error"] = "success"
    error_code: str | None = None
    safe_error_message: str | None = None


class CalendarSlotSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_min: datetime
    time_max: datetime
    timezone: str = "Europe/Berlin"
    duration_minutes: int = Field(default=30, ge=_MIN_DURATION_MINUTES, le=_MAX_DURATION_MINUTES)
    max_slots: int = Field(default=3, ge=1, le=_MAX_SLOTS)
    workday_start: str = "09:00"
    workday_end: str = "17:00"
    calendar_id: str | None = None

    @field_validator("calendar_id")
    @classmethod
    def _sanitize_calendar_id(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        if not _CALENDAR_ID_PATTERN.match(cleaned):
            raise ValueError("Invalid calendar_id format")
        return cleaned

    @model_validator(mode="after")
    def _validate_range(self) -> CalendarSlotSuggestionRequest:
        if self.time_min >= self.time_max:
            raise ValueError("time_min must be before time_max")
        return self


class CalendarSlotSuggestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "google_calendar"
    mode: Literal["live", "mock", "missing", "unhealthy"] = "mock"
    timezone: str
    suggested_slots: list[CalendarSlot] = Field(default_factory=list)
    fallback_used: bool = False
    latency_ms: int = 0
    status: Literal["success", "error"] = "success"
    error_code: str | None = None
    safe_error_message: str | None = None


class CalendarCreateEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=_MAX_SUMMARY)
    start_time: datetime
    end_time: datetime
    timezone: str = "Europe/Berlin"
    attendees: list[EmailStr] = Field(default_factory=list, max_length=_MAX_ATTENDEES)
    description: str | None = Field(default=None, max_length=_MAX_DESCRIPTION)
    location: str | None = Field(default=None, max_length=_MAX_LOCATION)
    calendar_id: str | None = None

    @field_validator("calendar_id")
    @classmethod
    def _sanitize_calendar_id(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        if not _CALENDAR_ID_PATTERN.match(cleaned):
            raise ValueError("Invalid calendar_id format")
        return cleaned

    @model_validator(mode="after")
    def _validate_times(self) -> CalendarCreateEventRequest:
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        duration = (self.end_time - self.start_time).total_seconds() / 60
        if duration < _MIN_DURATION_MINUTES or duration > _MAX_DURATION_MINUTES:
            raise ValueError("Event duration out of allowed range")
        return self


class CalendarCreateEventResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "google_calendar"
    mode: Literal["live", "mock", "missing", "unhealthy"] = "mock"
    action: str = "create_event"
    status: Literal["success", "error"] = "success"
    event_id: str | None = None
    summary: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    timezone: str | None = None
    attendee_count: int = 0
    fallback_used: bool = False
    error_code: str | None = None
    safe_error_message: str | None = None


class CalendarApprovalPayload(BaseModel):
    """Payload stored on approval requests for calendar event creation."""

    model_config = ConfigDict(extra="forbid")

    action_type: Literal[
        "schedule_meeting",
        "calendar_create_event",
        "google_calendar_create_event",
    ] = "calendar_create_event"
    summary: str = Field(min_length=1, max_length=_MAX_SUMMARY)
    start_time: datetime
    end_time: datetime
    timezone: str = "Europe/Berlin"
    attendees: list[EmailStr] = Field(default_factory=list, max_length=_MAX_ATTENDEES)
    description: str | None = Field(default=None, max_length=_MAX_DESCRIPTION)
    location: str | None = Field(default=None, max_length=_MAX_LOCATION)
    calendar_id: str | None = None
    risk_level: str = "medium"
    reason: str = ""

    @field_validator("calendar_id")
    @classmethod
    def _sanitize_calendar_id(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        if not _CALENDAR_ID_PATTERN.match(cleaned):
            raise ValueError("Invalid calendar_id format")
        return cleaned

    @model_validator(mode="after")
    def _validate_times(self) -> CalendarApprovalPayload:
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self
