from __future__ import annotations

import os

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.billing.base import BillingProvider


class StripeProvider(BillingProvider):
    """Stripe-backed billing provider."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("STRIPE_SECRET_KEY", "")
        if not self._api_key:
            raise ProviderUnavailableError("Stripe secret key not configured")

    def get_subscription(self, organization_id: str) -> dict | None:
        raise NotImplementedError("Stripe get_subscription not yet implemented")

    def create_checkout_session(self, organization_id: str, plan_code: str) -> dict:
        raise NotImplementedError("Stripe create_checkout_session not yet implemented")

    def cancel_subscription(self, subscription_id: str) -> dict:
        raise NotImplementedError("Stripe cancel_subscription not yet implemented")
