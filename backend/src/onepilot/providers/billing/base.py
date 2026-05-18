from __future__ import annotations

from abc import ABC, abstractmethod


class BillingProvider(ABC):
    @abstractmethod
    def get_subscription(self, organization_id: str) -> dict | None: ...

    @abstractmethod
    def create_checkout_session(self, organization_id: str, plan_code: str) -> dict: ...

    @abstractmethod
    def cancel_subscription(self, subscription_id: str) -> dict: ...

    def get_customer_portal_url(self, organization_id: str) -> dict:
        """Return a customer portal session (mock or live)."""
        raise NotImplementedError

    def get_invoice_preview(self, organization_id: str, plan_code: str) -> dict:
        """Return provider-side invoice preview metadata."""
        raise NotImplementedError
