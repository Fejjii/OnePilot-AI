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
    ) -> dict: ...

    @abstractmethod
    def send_approved_email(self, draft_id: str) -> dict: ...

    @abstractmethod
    def list_drafts(self, limit: int = 10) -> list[dict]: ...
