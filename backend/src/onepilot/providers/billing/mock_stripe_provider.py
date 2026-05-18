from __future__ import annotations

import uuid
from datetime import UTC, datetime

from onepilot.providers.billing.base import BillingProvider


class MockStripeProvider(BillingProvider):
    """In-memory billing provider for tests and demos."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, dict] = {}
        self._checkouts: list[dict] = []

    def get_subscription(self, organization_id: str) -> dict | None:
        return self._subscriptions.get(organization_id)

    def create_checkout_session(self, organization_id: str, plan_code: str) -> dict:
        session_id = f"cs_{uuid.uuid4().hex[:12]}"
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        subscription = {
            "id": sub_id,
            "organization_id": organization_id,
            "plan_code": plan_code,
            "status": "active",
            "created_at": now,
            "provider": "mock_stripe",
        }
        self._subscriptions[organization_id] = subscription

        session = {
            "id": session_id,
            "subscription_id": sub_id,
            "organization_id": organization_id,
            "plan_code": plan_code,
            "url": f"https://checkout.mock.example.com/{session_id}",
            "created_at": now,
            "mock": True,
        }
        self._checkouts.append(session)
        return session

    def cancel_subscription(self, subscription_id: str) -> dict:
        for _org_id, sub in self._subscriptions.items():
            if sub["id"] == subscription_id:
                sub["status"] = "canceled"
                sub["canceled_at"] = datetime.now(UTC).isoformat()
                return sub
        return {"error": "Subscription not found", "subscription_id": subscription_id}

    def get_customer_portal_url(self, organization_id: str) -> dict:
        portal_id = f"bpc_{uuid.uuid4().hex[:12]}"
        return {
            "id": portal_id,
            "organization_id": organization_id,
            "url": f"https://billing.mock.example.com/portal/{portal_id}",
            "mock": True,
            "provider": "mock_stripe",
        }

    def get_invoice_preview(self, organization_id: str, plan_code: str) -> dict:
        return {
            "organization_id": organization_id,
            "plan_code": plan_code,
            "status": "draft",
            "mock": True,
            "provider": "mock_stripe",
            "message": "Stripe integration mocked in this capstone",
        }
