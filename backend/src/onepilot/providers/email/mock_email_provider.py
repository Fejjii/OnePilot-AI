from __future__ import annotations

import uuid
from datetime import UTC, datetime

from onepilot.providers.email.base import EmailProvider


class MockEmailProvider(EmailProvider):
    """In-memory email provider for tests and demos."""

    def __init__(self) -> None:
        self._drafts: dict[str, dict] = {}
        self._sent: list[dict] = []

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> dict:
        draft_id = f"draft_{uuid.uuid4().hex[:8]}"
        draft = {
            "id": draft_id,
            "to": to,
            "subject": subject,
            "body": body,
            "reply_to": reply_to,
            "status": "draft",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._drafts[draft_id] = draft
        return draft

    def send_approved_email(self, draft_id: str) -> dict:
        draft = self._drafts.pop(draft_id, None)
        if draft is None:
            return {"error": "Draft not found", "draft_id": draft_id}
        draft["status"] = "sent"
        draft["sent_at"] = datetime.now(UTC).isoformat()
        self._sent.append(draft)
        return draft

    def list_drafts(self, limit: int = 10) -> list[dict]:
        return list(self._drafts.values())[:limit]
