"""Tests for /knowledge/search semantic retrieval."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


def _register(client: TestClient, *, suffix: str) -> dict:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"ks{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Knowledge User",
            "organization_name": f"KSOrg{suffix}",
        },
    )
    assert resp.status_code == 200
    return resp.json()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload(client: TestClient, token: str, *, filename: str, body: bytes) -> str:
    files = {"file": (filename, io.BytesIO(body), "text/markdown")}
    resp = client.post("/documents/upload", files=files, headers=_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


_PRICING_DOC = b"""# Pricing Plans

## Essentials
The Essentials plan costs 1800 dollars per month and includes 2000 conversations.

## Growth
The Growth plan costs 3800 dollars per month and includes 10000 conversations.
"""

_REFUND_DOC = b"""# Refund Policy

## Pilots
Pilots are fully refundable in the first 7 days. After day 21 they are non-refundable.

## Retainers
Retainers cancel at the end of the current month. Annual prepay receives 75 percent refund.
"""


class TestSemanticSearch:
    def test_search_finds_pricing_chunk(self, client: TestClient) -> None:
        token = _register(client, suffix="_pricing")["access_token"]
        _upload(client, token, filename="pricing.md", body=_PRICING_DOC)
        _upload(client, token, filename="refund.md", body=_REFUND_DOC)

        resp = client.post(
            "/knowledge/search",
            json={"query": "How much does the Growth plan cost per month?"},
            headers=_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["results"], body
        top = body["results"][0]
        assert "growth" in top["content"].lower() or "3800" in top["content"]
        assert top["document_title"] == "Pricing Plans"
        assert top["score"] > 0

    def test_search_returns_citation_fields(self, client: TestClient) -> None:
        token = _register(client, suffix="_cite")["access_token"]
        _upload(client, token, filename="refund.md", body=_REFUND_DOC)
        resp = client.post(
            "/knowledge/search",
            json={"query": "refund pilot first week"},
            headers=_headers(token),
        )
        body = resp.json()
        result = body["results"][0]
        for key in ("chunk_id", "document_id", "document_title", "score", "section", "content"):
            assert key in result

    def test_search_is_tenant_scoped(self, client: TestClient) -> None:
        token_a = _register(client, suffix="_tenA")["access_token"]
        token_b = _register(client, suffix="_tenB")["access_token"]
        _upload(client, token_a, filename="pricing.md", body=_PRICING_DOC)

        resp = client.post(
            "/knowledge/search",
            json={"query": "Growth plan price"},
            headers=_headers(token_b),
        )
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_weak_evidence_flag_when_no_documents(self, client: TestClient) -> None:
        token = _register(client, suffix="_weak")["access_token"]
        resp = client.post(
            "/knowledge/search",
            json={"query": "Anything"},
            headers=_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["weak_evidence"] is True
        assert body["results"] == []

    def test_fallback_used_flag_present(self, client: TestClient) -> None:
        token = _register(client, suffix="_fb")["access_token"]
        _upload(client, token, filename="pricing.md", body=_PRICING_DOC)
        resp = client.post(
            "/knowledge/search",
            json={"query": "Growth plan price"},
            headers=_headers(token),
        )
        body = resp.json()
        assert body["fallback_used"] is True  # no OPENAI_API_KEY in tests

    def test_top_k_limits_results(self, client: TestClient) -> None:
        token = _register(client, suffix="_topk")["access_token"]
        _upload(client, token, filename="pricing.md", body=_PRICING_DOC)
        _upload(client, token, filename="refund.md", body=_REFUND_DOC)
        resp = client.post(
            "/knowledge/search",
            json={"query": "pricing", "top_k": 1},
            headers=_headers(token),
        )
        body = resp.json()
        assert len(body["results"]) <= 1
