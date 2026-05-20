"""Gmail action schemas — strict validation for provider I/O and approvals."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_MAX_RECIPIENTS = 10
_MAX_SUBJECT = 500
_MAX_BODY = 50_000

_EMAIL_LIST_SPLIT = re.compile(r"[,;\s]+")


class EmailAddress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: EmailStr


class EmailDraftRequest(BaseModel):
    """Validated input for Gmail draft creation."""

    model_config = ConfigDict(extra="forbid")

    to: list[EmailStr] = Field(min_length=1, max_length=_MAX_RECIPIENTS)
    subject: str = Field(min_length=1, max_length=_MAX_SUBJECT)
    body: str = Field(min_length=1, max_length=_MAX_BODY)
    cc: list[EmailStr] = Field(default_factory=list, max_length=_MAX_RECIPIENTS)
    bcc: list[EmailStr] = Field(default_factory=list, max_length=_MAX_RECIPIENTS)

    @field_validator("to", "cc", "bcc", mode="before")
    @classmethod
    def _normalize_recipient_lists(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [p.strip() for p in _EMAIL_LIST_SPLIT.split(value) if p.strip()]
            return parts
        return value


class EmailSendRequest(EmailDraftRequest):
    """Validated input for Gmail send (approval-gated only)."""


class GmailActionResult(BaseModel):
    """Normalized provider result — never includes tokens or secrets."""

    model_config = ConfigDict(extra="forbid")

    provider: str = "gmail"
    mode: Literal["live", "mock", "missing", "unhealthy"] = "mock"
    action: str
    draft_id: str | None = None
    message_id: str | None = None
    status: Literal["success", "error"] = "success"
    recipient_count: int = 0
    created_at: datetime | None = None
    fallback_used: bool = False
    error_code: str | None = None
    safe_error_message: str | None = None


class EmailDraftResult(GmailActionResult):
    action: str = "create_draft"


class EmailSendResult(GmailActionResult):
    action: str = "send_email"


class EmailApprovalPayload(BaseModel):
    """Payload stored on approval requests for Gmail actions."""

    model_config = ConfigDict(extra="forbid")

    action_type: Literal["gmail_create_draft", "gmail_send_email", "send_email"] = (
        "gmail_create_draft"
    )
    to: list[EmailStr] = Field(min_length=1, max_length=_MAX_RECIPIENTS)
    subject: str = Field(min_length=1, max_length=_MAX_SUBJECT)
    body: str = Field(min_length=1, max_length=_MAX_BODY)
    cc: list[EmailStr] = Field(default_factory=list, max_length=_MAX_RECIPIENTS)
    bcc: list[EmailStr] = Field(default_factory=list, max_length=_MAX_RECIPIENTS)
    recipient_name: str | None = None
    tone: str | None = None
    risk_level: str = "medium"
    reason: str = ""

    @field_validator("to", "cc", "bcc", mode="before")
    @classmethod
    def _normalize_lists(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            if not value.strip():
                return []
            parts = [p.strip() for p in _EMAIL_LIST_SPLIT.split(value) if p.strip()]
            return parts
        return value


class GmailProviderStatus(BaseModel):
    """Safe Gmail provider status for diagnostics."""

    configured: bool = False
    mode: Literal["live", "mock", "missing", "unhealthy"] = "missing"
    active: bool = False
    fallback_used: bool = True
    capabilities: dict[str, bool] = Field(
        default_factory=lambda: {
            "create_draft": True,
            "send_email": False,
            "requires_approval": True,
        }
    )
    purpose: str = "Gmail draft creation and approval-gated email sending"
