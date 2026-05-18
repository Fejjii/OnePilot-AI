from __future__ import annotations

import os

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.email.base import EmailProvider


class GmailProvider(EmailProvider):
    """Gmail API-backed email provider."""

    def __init__(self, credentials_json: str | None = None) -> None:
        self._credentials = credentials_json or os.environ.get("GMAIL_CREDENTIALS_JSON", "")
        if not self._credentials:
            raise ProviderUnavailableError("Gmail credentials not configured")

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> dict:
        raise NotImplementedError("Gmail create_draft not yet implemented")

    def send_approved_email(self, draft_id: str) -> dict:
        raise NotImplementedError("Gmail send_approved_email not yet implemented")

    def list_drafts(self, limit: int = 10) -> list[dict]:
        raise NotImplementedError("Gmail list_drafts not yet implemented")
