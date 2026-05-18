from __future__ import annotations

from abc import ABC, abstractmethod


class BillingProvider(ABC):
    @abstractmethod
    def get_subscription(self, organization_id: str) -> dict | None: ...

    @abstractmethod
    def create_checkout_session(self, organization_id: str, plan_code: str) -> dict: ...

    @abstractmethod
    def cancel_subscription(self, subscription_id: str) -> dict: ...
