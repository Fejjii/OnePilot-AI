from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from onepilot.core.errors import ProviderUnavailableError
from onepilot.core.logging import get_logger
from onepilot.providers.email.base import EmailProvider
from onepilot.providers.email.gmail_auth import GoogleOAuthClient
from onepilot.providers.email.gmail_mime import build_raw_message
from onepilot.schemas.gmail import GmailActionResult, GmailProviderStatus

log = get_logger(__name__)

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailProvider(EmailProvider):
    """Gmail API-backed email provider (OAuth refresh-token flow)."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        timeout_seconds: float = 20.0,
        send_enabled: bool = False,
    ) -> None:
        if not all((client_id, client_secret, refresh_token)):
            raise ProviderUnavailableError("Gmail OAuth credentials not configured")
        self._oauth = GoogleOAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        )
        self._timeout = timeout_seconds
        self._send_enabled = send_enabled
        self._mode: str = "live"

    def get_status(self) -> GmailProviderStatus:
        return GmailProviderStatus(
            configured=True,
            mode="live",
            active=True,
            fallback_used=False,
            capabilities={
                "create_draft": True,
                "send_email": self._send_enabled,
                "requires_approval": True,
            },
        )

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
        *,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict[str, Any]:
        to_list = _split_addresses(to)
        cc_list = list(cc or [])
        bcc_list = list(bcc or [])
        result = self._create_draft_impl(
            to=to_list,
            subject=subject,
            body=body,
            cc=cc_list,
            bcc=bcc_list,
            reply_to=reply_to,
        )
        return result.model_dump(mode="json")

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self._send_enabled:
            return GmailActionResult(
                provider="gmail",
                mode="live",
                action="send_email",
                status="error",
                fallback_used=False,
                error_code="send_disabled",
                safe_error_message="Gmail send is disabled; use draft creation or enable send in config.",
            ).model_dump(mode="json")

        to_list = _split_addresses(to)
        result = self._send_impl(
            to=to_list,
            subject=subject,
            body=body,
            cc=list(cc or []),
            bcc=list(bcc or []),
        )
        return result.model_dump(mode="json")

    def send_draft(self, draft_id: str) -> dict[str, Any]:
        if not self._send_enabled:
            return GmailActionResult(
                provider="gmail",
                mode="live",
                action="send_draft",
                status="error",
                draft_id=draft_id,
                error_code="send_disabled",
                safe_error_message="Gmail send is disabled.",
            ).model_dump(mode="json")

        try:
            data = self._api_request(
                "POST",
                f"/drafts/send",
                json={"id": draft_id},
            )
        except Exception as exc:
            log.warning("gmail_send_draft_failed", draft_id=draft_id, error=str(exc))
            return GmailActionResult(
                provider="gmail",
                mode="live",
                action="send_draft",
                status="error",
                draft_id=draft_id,
                error_code="gmail_api_error",
                safe_error_message="Failed to send Gmail draft.",
            ).model_dump(mode="json")

        message_id = str((data or {}).get("id") or "")
        return GmailActionResult(
            provider="gmail",
            mode="live",
            action="send_draft",
            status="success",
            draft_id=draft_id,
            message_id=message_id or None,
            recipient_count=0,
            created_at=datetime.now(UTC),
            fallback_used=False,
        ).model_dump(mode="json")

    def send_approved_email(self, draft_id: str) -> dict[str, Any]:
        return self.send_draft(draft_id)

    def list_drafts(self, limit: int = 10) -> list[dict]:
        try:
            data = self._api_request("GET", "/drafts", params={"maxResults": limit})
        except Exception as exc:
            log.warning("gmail_list_drafts_failed", error=str(exc))
            return []
        drafts = data.get("drafts") if isinstance(data, dict) else []
        if not isinstance(drafts, list):
            return []
        return [{"id": d.get("id"), "message": d.get("message")} for d in drafts[:limit]]

    def _create_draft_impl(
        self,
        *,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str],
        bcc: list[str],
        reply_to: str | None,
    ) -> GmailActionResult:
        if not to:
            return _error_result("create_draft", "invalid_recipients", "At least one recipient is required.")
        try:
            raw = build_raw_message(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
            data = self._api_request("POST", "/drafts", json={"message": {"raw": raw}})
        except Exception as exc:
            log.warning("gmail_create_draft_failed", error=str(exc))
            return _error_result("create_draft", "gmail_api_error", "Failed to create Gmail draft.")

        draft_id = ""
        if isinstance(data, dict):
            draft_id = str(data.get("id") or "")
            message = data.get("message")
            if isinstance(message, dict) and not draft_id:
                draft_id = str(message.get("id") or "")

        return GmailActionResult(
            provider="gmail",
            mode="live",
            action="create_draft",
            status="success",
            draft_id=draft_id or None,
            recipient_count=len(to) + len(cc) + len(bcc),
            created_at=datetime.now(UTC),
            fallback_used=False,
        )

    def _send_impl(
        self,
        *,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str],
        bcc: list[str],
    ) -> GmailActionResult:
        if not to:
            return _error_result("send_email", "invalid_recipients", "At least one recipient is required.")
        try:
            raw = build_raw_message(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
            data = self._api_request("POST", "/messages/send", json={"raw": raw})
        except Exception as exc:
            log.warning("gmail_send_failed", error=str(exc))
            return _error_result("send_email", "gmail_api_error", "Failed to send Gmail message.")

        message_id = str((data or {}).get("id") or "") if isinstance(data, dict) else ""
        return GmailActionResult(
            provider="gmail",
            mode="live",
            action="send_email",
            status="success",
            message_id=message_id or None,
            recipient_count=len(to) + len(cc) + len(bcc),
            created_at=datetime.now(UTC),
            fallback_used=False,
        )

    def _api_request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        token = self._oauth.get_access_token()
        url = f"{_GMAIL_API}{path}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self._timeout) as client:
            response = client.request(method, url, headers=headers, json=json, params=params)
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            payload = response.json()
            return payload if isinstance(payload, dict) else {}


def _split_addresses(value: str) -> list[str]:
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


def _error_result(action: str, code: str, message: str) -> GmailActionResult:
    return GmailActionResult(
        provider="gmail",
        mode="live",
        action=action,
        status="error",
        fallback_used=False,
        error_code=code,
        safe_error_message=message,
    )
