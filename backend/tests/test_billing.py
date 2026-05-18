"""Billing, cost calculator, and mock Stripe tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from onepilot.providers.billing.mock_stripe_provider import MockStripeProvider
from onepilot.services.cost_calculator import calculate_usage_cost


def _register(client: TestClient, *, suffix: str) -> str:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"billing{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Billing User",
            "organization_name": f"BillingOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestCostCalculator:
    def test_chat_token_cost(self) -> None:
        result = calculate_usage_cost(
            feature="chat_messages",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
        assert result.estimated_cost > 0
        assert result.currency == "USD"
        assert result.price_source == "pricing_config"
        assert "token_pricing" in result.calculation_breakdown

    def test_embedding_cost(self) -> None:
        result = calculate_usage_cost(
            feature="rag_queries",
            provider="openai",
            model="text-embedding-3-small",
            embedding_tokens=1_000_000,
        )
        assert result.estimated_cost > 0
        assert result.calculation_breakdown["token_pricing"]["embedding_tokens"] == 1_000_000

    def test_speech_transcription_cost(self) -> None:
        result = calculate_usage_cost(
            feature="speech_transcription",
            provider="openai",
            model="whisper-1",
            audio_seconds=60.0,
        )
        assert result.estimated_cost > 0
        assert "speech" in result.calculation_breakdown

    def test_fallback_cost_is_zero(self) -> None:
        result = calculate_usage_cost(
            feature="chat_messages",
            provider="FallbackLLMProvider",
            model="gpt-4o-mini",
            input_tokens=10_000,
            output_tokens=5_000,
            fallback_used=True,
        )
        assert result.estimated_cost == 0.0
        assert result.price_source == "fallback_zero"


class TestMockStripeProvider:
    def test_checkout_and_portal(self) -> None:
        provider = MockStripeProvider()
        session = provider.create_checkout_session("org_1", "pro")
        assert session["mock"] is True
        assert "url" in session

        portal = provider.get_customer_portal_url("org_1")
        assert portal["mock"] is True
        assert "billing.mock.example.com" in portal["url"]

        preview = provider.get_invoice_preview("org_1", "pro")
        assert preview["mock"] is True


class TestBillingEndpoints:
    def test_billing_summary_org_scoped(self, client: TestClient) -> None:
        token_a = _register(client, suffix="_a")
        token_b = _register(client, suffix="_b")
        r1 = client.get("/billing/summary", headers=_h(token_a))
        assert r1.status_code == 200
        org1 = r1.json()["organization_id"]

        r2 = client.get("/billing/summary", headers=_h(token_b))
        assert r2.status_code == 200
        org2 = r2.json()["organization_id"]
        assert org1 != org2

    def test_invoice_preview_line_items(self, client: TestClient) -> None:
        token = _register(client, suffix="_inv")
        resp = client.get("/billing/invoice-preview", headers=_h(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["mock_stripe"] is True
        assert len(data["line_items"]) >= 2
        assert data["base_plan_price_cents"] >= 0
        assert "total_estimated_due_cents" in data

    def test_billing_plans(self, client: TestClient) -> None:
        token = _register(client, suffix="_plans")
        resp = client.get("/billing/plans", headers=_h(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_plan"] == "free"
        assert data["entitlements"]["included_chat_messages"] > 0
        assert len(data["available_plans"]) == 4

    def test_usage_summary_includes_cost(self, client: TestClient) -> None:
        token = _register(client, suffix="_usage")
        resp = client.get("/usage/summary", headers=_h(token))
        assert resp.status_code == 200
        assert "total_estimated_cost" in resp.json()
