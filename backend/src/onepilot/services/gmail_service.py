"""Gmail business logic — validates payloads and calls the email provider."""

from __future__ import annotations

import re

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import UsageFeature
from onepilot.core.errors import ValidationError
from onepilot.core.logging import get_logger
from onepilot.providers import get_email_provider
from onepilot.providers.email.mock_email_provider import MockEmailProvider
from onepilot.repositories.models import ApprovalRequest
from onepilot.schemas.gmail import (
    EmailApprovalPayload,
    EmailDraftRequest,
    EmailSendRequest,
    GmailActionResult,
)
from onepilot.security.auth import Principal
from onepilot.services import audit_service, usage_service

log = get_logger(__name__)

_DEFAULT_RECIPIENT = "lead@example.com"
_SEND_INTENT = re.compile(
    r"\b(draft\s+and\s+send|send\s+(this|an?|the)\s+email|send\s+email)\b",
    re.IGNORECASE,
)


def is_live_gmail_provider(settings: Settings | None = None) -> bool:
    """Return True when the configured email provider is live Gmail."""
    from onepilot.providers.email.gmail_provider import GmailProvider

    cfg = settings or get_settings()
    provider = get_email_provider(cfg)
    return isinstance(provider, GmailProvider)


def create_draft_direct(
    session: Session,
    *,
    principal: Principal,
    subject: str,
    body: str,
    recipient_email: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    settings: Settings | None = None,
) -> dict:
    """Create a Gmail draft immediately (demo mode with send disabled)."""
    payload = build_approval_payload(
        subject=subject,
        body=body,
        recipient_email=recipient_email,
        action_type="gmail_create_draft",
        cc=cc,
        bcc=bcc,
    )
    return _create_draft_from_payload(
        session,
        principal=principal,
        payload=payload,
        settings=settings or get_settings(),
    )


def infer_email_action(message: str, context: dict | None) -> str:
    """Return ``draft_only`` or ``send`` from explicit context or message cues."""
    ctx = context or {}
    explicit = ctx.get("action")
    if explicit in {"send", "draft_only"}:
        return str(explicit)
    if _SEND_INTENT.search(message):
        return "send"
    return "draft_only"


def resolve_approval_action_type(action: str, *, force_send: bool = False) -> str:
    """Map user intent to gated Gmail approval action types."""
    if force_send:
        return "gmail_send_email"
    if action == "send":
        return "gmail_create_draft"
    return "gmail_create_draft"


def build_approval_payload(
    *,
    subject: str,
    body: str,
    recipient_email: str | None,
    recipient_name: str | None = None,
    tone: str | None = None,
    action_type: str = "gmail_create_draft",
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict:
    to_addr = (recipient_email or "").strip() or _DEFAULT_RECIPIENT
    try:
        payload = EmailApprovalPayload(
            action_type=action_type,  # type: ignore[arg-type]
            to=[to_addr],
            subject=subject,
            body=body,
            cc=cc or [],
            bcc=bcc or [],
            recipient_name=recipient_name,
            tone=tone,
        )
    except PydanticValidationError as exc:
        raise ValidationError(f"Invalid email approval payload: {exc}") from exc
    return payload.model_dump(mode="json")


def execute_approval_action(
    session: Session,
    *,
    principal: Principal,
    approval: ApprovalRequest,
    settings: Settings | None = None,
) -> dict:
    """Run Gmail action after human approval. Never called before approval."""
    cfg = settings or get_settings()
    action = approval.action_type
    payload_raw = dict(approval.proposed_payload or {})

    if action in {"send_email", "gmail_create_draft"}:
        return _create_draft_from_payload(session, principal=principal, payload=payload_raw, settings=cfg)
    if action == "gmail_send_email":
        return _send_from_payload(session, principal=principal, payload=payload_raw, settings=cfg)

    return {
        "status": "skipped",
        "reason": f"No executor for action_type={action}",
    }


def _create_draft_from_payload(
    session: Session,
    *,
    principal: Principal,
    payload: dict,
    settings: Settings,
) -> dict:
    try:
        req = EmailDraftRequest(
            to=payload.get("to") or payload.get("recipient_email") or _DEFAULT_RECIPIENT,
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
            cc=payload.get("cc") or [],
            bcc=payload.get("bcc") or [],
        )
    except PydanticValidationError as exc:
        result = _validation_error_result("create_draft", exc)
        _record_execution_audit(session, principal, payload, result)
        return result

    provider = get_email_provider(settings)
    to_joined = ", ".join(str(a) for a in req.to)
    raw = provider.create_draft(
        to_joined,
        req.subject,
        req.body,
        cc=[str(c) for c in req.cc],
        bcc=[str(b) for b in req.bcc],
    )
    result = _normalize_provider_result(raw, default_action="create_draft")
    _track_usage(session, principal, UsageFeature.GMAIL_CREATE_DRAFT.value, result)
    _record_execution_audit(session, principal, payload, result, event="gmail.draft_created")
    return result


def _send_from_payload(
    session: Session,
    *,
    principal: Principal,
    payload: dict,
    settings: Settings,
) -> dict:
    if not settings.GMAIL_SEND_ENABLED:
        result = GmailActionResult(
            mode="live",
            action="send_email",
            status="error",
            error_code="send_disabled",
            safe_error_message="Gmail send is disabled in server configuration.",
        ).model_dump(mode="json")
        _record_execution_audit(session, principal, payload, result, event="gmail.send_blocked")
        return result

    try:
        req = EmailSendRequest(
            to=payload.get("to") or payload.get("recipient_email") or _DEFAULT_RECIPIENT,
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
            cc=payload.get("cc") or [],
            bcc=payload.get("bcc") or [],
        )
    except PydanticValidationError as exc:
        result = _validation_error_result("send_email", exc)
        _record_execution_audit(session, principal, payload, result)
        return result

    provider = get_email_provider(settings)
    to_joined = ", ".join(str(a) for a in req.to)
    if hasattr(provider, "send_email"):
        raw = provider.send_email(
            to_joined,
            req.subject,
            req.body,
            cc=[str(c) for c in req.cc],
            bcc=[str(b) for b in req.bcc],
        )
    else:
        draft_raw = provider.create_draft(to_joined, req.subject, req.body)
        draft_id = str(draft_raw.get("draft_id") or draft_raw.get("id") or "")
        raw = provider.send_approved_email(draft_id)

    result = _normalize_provider_result(raw, default_action="send_email")
    _track_usage(session, principal, UsageFeature.GMAIL_SEND_EMAIL.value, result)
    _record_execution_audit(session, principal, payload, result, event="gmail.email_sent")
    return result


def _normalize_provider_result(raw: dict, *, default_action: str) -> dict:
    if "status" in raw and "provider" in raw:
        return dict(raw)
    return GmailActionResult(
        provider="gmail",
        mode="mock" if raw.get("fallback_used") else "live",
        action=default_action,
        status="success" if not raw.get("error") else "error",
        draft_id=raw.get("draft_id") or raw.get("id"),
        message_id=raw.get("message_id"),
        recipient_count=raw.get("recipient_count", 1),
        fallback_used=bool(raw.get("fallback_used")),
        safe_error_message=raw.get("error") or raw.get("safe_error_message"),
        error_code=raw.get("error_code"),
    ).model_dump(mode="json")


def _validation_error_result(action: str, exc: PydanticValidationError) -> dict:
    return GmailActionResult(
        action=action,
        status="error",
        error_code="validation_error",
        safe_error_message="Invalid email fields in approval payload.",
    ).model_dump(mode="json")


def _track_usage(
    session: Session,
    principal: Principal,
    feature: str,
    result: dict,
) -> None:
    provider = get_email_provider()
    provider_name = "gmail"
    if isinstance(provider, MockEmailProvider):
        provider_name = "gmail_mock"
    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=feature,
        provider=provider_name,
        tool_calls=1,
        fallback_used=bool(result.get("fallback_used")),
        metadata={"action": result.get("action"), "status": result.get("status")},
    )


def _record_execution_audit(
    session: Session,
    principal: Principal,
    payload: dict,
    result: dict,
    *,
    event: str = "gmail.action_failed",
) -> None:
    status = result.get("status", "error")
    action_event = event if status == "success" else "gmail.action_failed"
    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action=action_event,
        resource_type="email",
        resource_id=str(result.get("draft_id") or result.get("message_id") or ""),
        detail={
            "action": result.get("action"),
            "status": status,
            "mode": result.get("mode"),
            "error_code": result.get("error_code"),
            "recipient_count": result.get("recipient_count"),
        },
    )
    if status != "success":
        log.warning(
            "gmail_action_failed",
            action=result.get("action"),
            error_code=result.get("error_code"),
        )
