from __future__ import annotations

import os

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.crm.base import CRMProvider


class HubSpotProvider(CRMProvider):
    """HubSpot-backed CRM provider."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("HUBSPOT_API_KEY", "")
        if not self._api_key:
            raise ProviderUnavailableError("HubSpot API key not configured")

    def get_lead(self, lead_id: str) -> dict | None:
        raise NotImplementedError("HubSpot get_lead not yet implemented")

    def create_lead_note(self, lead_id: str, note: str) -> dict:
        raise NotImplementedError("HubSpot create_lead_note not yet implemented")

    def update_lead_status(self, lead_id: str, status: str) -> dict:
        raise NotImplementedError("HubSpot update_lead_status not yet implemented")

    def search_leads(self, query: str, limit: int = 10) -> list[dict]:
        raise NotImplementedError("HubSpot search_leads not yet implemented")
