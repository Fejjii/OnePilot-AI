from __future__ import annotations

from abc import ABC, abstractmethod


class CRMProvider(ABC):
    @abstractmethod
    def get_lead(self, lead_id: str) -> dict | None: ...

    @abstractmethod
    def create_lead_note(self, lead_id: str, note: str) -> dict: ...

    @abstractmethod
    def update_lead_status(self, lead_id: str, status: str) -> dict: ...

    @abstractmethod
    def search_leads(self, query: str, limit: int = 10) -> list[dict]: ...
