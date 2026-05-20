from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from onepilot.providers.email.base import EmailProvider
from onepilot.schemas.gmail import GmailActionResult, GmailProviderStatus


class MockEmailProvider(EmailProvider):
    """In-memory email provider for tests and demos."""

    def __init__(self) -> None:
        self._drafts: dict[str, dict] = {}
        self._sent: list[dict] = []

    def get_status(self) -> GmailProviderStatus:
        return GmailProviderStatus(
            configured=False,
            mode="mock",
            active=True,
            fallback_used=True,
            capabilities={
                "create_draft": True,
                "send_email": True,
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
        draft_id = f"draft_{uuid.uuid4().hex[:8]}"
        to_list = [p.strip() for p in to.split(",") if p.strip()]
        draft = {
            "id": draft_id,
            "to": to,
            "subject": subject,
            "body": body,
            "reply_to": reply_to,
            "cc": cc or [],
            "bcc": bcc or [],
            "status": "draft",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._drafts[draft_id] = draft
        result = GmailActionResult(
            provider="gmail",
            mode="mock",
            action="create_draft",
            status="success",
            draft_id=draft_id,
            recipient_count=len(to_list) + len(cc or []) + len(bcc or []),
            created_at=datetime.now(UTC),
            fallback_used=True,
        )
        return {**draft, **result.model_dump(mode="json")}

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict[str, Any]:
        draft = self.create_draft(to, subject, body, cc=cc, bcc=bcc)
        draft_id = str(draft.get("draft_id") or draft.get("id") or "")
        return self.send_approved_email(draft_id)

    def send_draft(self, draft_id: str) -> dict[str, Any]:
        return self.send_approved_email(draft_id)

    def send_approved_email(self, draft_id: str) -> dict[str, Any]:
        draft = self._drafts.pop(draft_id, None)
        if draft is None:
            result = GmailActionResult(
                provider="gmail",
                mode="mock",
                action="send_draft",
                status="error",
                draft_id=draft_id,
                fallback_used=True,
                error_code="draft_not_found",
                safe_error_message="Draft not found.",
            )
            return result.model_dump(mode="json")

        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        draft["status"] = "sent"
        draft["sent_at"] = datetime.now(UTC).isoformat()
        draft["message_id"] = message_id
        self._sent.append(draft)
        result = GmailActionResult(
            provider="gmail",
            mode="mock",
            action="send_draft",
            status="success",
            draft_id=draft_id,
            message_id=message_id,
            recipient_count=1,
            created_at=datetime.now(UTC),
            fallback_used=True,
        )
        return {**draft, **result.model_dump(mode="json")}

    def list_drafts(self, limit: int = 10) -> list[dict]:
        return list(self._drafts.values())[:limit]
