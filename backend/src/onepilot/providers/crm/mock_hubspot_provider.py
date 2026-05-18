from __future__ import annotations

import uuid
from datetime import UTC, datetime

from onepilot.providers.crm.base import CRMProvider

_SEED_LEADS: list[dict] = [
    {
        "id": "lead_001",
        "name": "Acme Corp",
        "email": "contact@acme.example.com",
        "status": "new",
        "notes": [],
    },
    {
        "id": "lead_002",
        "name": "Globex Inc",
        "email": "info@globex.example.com",
        "status": "contacted",
        "notes": [],
    },
]


class MockHubSpotProvider(CRMProvider):
    """In-memory CRM provider for tests and demos."""

    def __init__(self) -> None:
        self._leads: dict[str, dict] = {ld["id"]: dict(ld) for ld in _SEED_LEADS}

    def get_lead(self, lead_id: str) -> dict | None:
        return self._leads.get(lead_id)

    def create_lead_note(self, lead_id: str, note: str) -> dict:
        lead = self._leads.get(lead_id)
        if lead is None:
            lead = {"id": lead_id, "name": "Unknown", "email": "", "status": "new", "notes": []}
            self._leads[lead_id] = lead
        entry = {
            "id": f"note_{uuid.uuid4().hex[:8]}",
            "text": note,
            "created_at": datetime.now(UTC).isoformat(),
        }
        lead.setdefault("notes", []).append(entry)
        return entry

    def update_lead_status(self, lead_id: str, status: str) -> dict:
        lead = self._leads.get(lead_id)
        if lead is None:
            lead = {"id": lead_id, "name": "Unknown", "email": "", "status": status, "notes": []}
            self._leads[lead_id] = lead
        else:
            lead["status"] = status
        return lead

    def search_leads(self, query: str, limit: int = 10) -> list[dict]:
        query_lower = query.lower()
        results: list[dict] = []
        for lead in self._leads.values():
            if query_lower in lead.get("name", "").lower() or query_lower in lead.get("email", "").lower():
                results.append(lead)
                if len(results) >= limit:
                    break
        return results
