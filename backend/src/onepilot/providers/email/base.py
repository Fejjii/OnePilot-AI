from __future__ import annotations

from abc import ABC, abstractmethod


class EmailProvider(ABC):
    @abstractmethod
    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
        *,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict: ...

    @abstractmethod
    def send_approved_email(self, draft_id: str) -> dict: ...

    @abstractmethod
    def list_drafts(self, limit: int = 10) -> list[dict]: ...

    def get_status(self) -> dict:
        """Return safe provider status (no secrets)."""
        return {"mode": "unknown", "configured": False}

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict:
        raise NotImplementedError("send_email not implemented for this provider")

    def send_draft(self, draft_id: str) -> dict:
        return self.send_approved_email(draft_id)
