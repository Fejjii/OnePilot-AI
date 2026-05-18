"""Tests for /knowledge/answer (grounded answers with citations)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from onepilot.services.rag_service import WEAK_EVIDENCE_ANSWER


def _register(client: TestClient, *, suffix: str) -> str:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"ans{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Answer User",
            "organization_name": f"AnsOrg{suffix}",
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload(client: TestClient, token: str, name: str, body: bytes) -> None:
    files = {"file": (name, io.BytesIO(body), "text/markdown")}
    resp = client.post("/documents/upload", files=files, headers=_h(token))
    assert resp.status_code == 200, resp.text


_FAQ = b"""# Customer FAQ

## How do I cancel my subscription?
Email support to cancel. Cancellations take effect at the end of the current
billing period. Refunds follow the refund policy document.

## How do you handle hallucinations?
The agent will not answer when retrieval evidence is weak. It returns a
weak-evidence message and forwards to a human teammate.
"""


class TestAnswerConfident:
    def test_returns_answer_and_citations(self, client: TestClient) -> None:
        token = _register(client, suffix="_conf")
        _upload(client, token, "faq.md", _FAQ)
        resp = client.post(
            "/knowledge/answer",
            json={"query": "How do I cancel my subscription?"},
            headers=_h(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"]
        assert body["weak_evidence"] is False
        assert body["citations"]
        first = body["citations"][0]
        assert "chunk_id" in first
        assert first["document_title"] == "Customer FAQ"
        assert body["confidence"] > 0

    def test_fallback_used_when_no_openai(self, client: TestClient) -> None:
        token = _register(client, suffix="_fb")
        _upload(client, token, "faq.md", _FAQ)
        resp = client.post(
            "/knowledge/answer",
            json={"query": "How do you handle hallucinations?"},
            headers=_h(token),
        )
        body = resp.json()
        assert body["fallback_used"] is True


class TestAnswerWeakEvidence:
    def test_weak_evidence_returns_safe_message(self, client: TestClient) -> None:
        token = _register(client, suffix="_weak")
        resp = client.post(
            "/knowledge/answer",
            json={"query": "How tall is Mount Everest?"},
            headers=_h(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["weak_evidence"] is True
        assert body["answer"] == WEAK_EVIDENCE_ANSWER
        assert body["citations"] == []


class TestAnswerTenantIsolation:
    def test_answer_cannot_use_other_tenant_docs(self, client: TestClient) -> None:
        token_a = _register(client, suffix="_isoA")
        token_b = _register(client, suffix="_isoB")
        _upload(client, token_a, "faq.md", _FAQ)

        resp = client.post(
            "/knowledge/answer",
            json={"query": "How do I cancel my subscription?"},
            headers=_h(token_b),
        )
        body = resp.json()
        assert body["weak_evidence"] is True
        assert body["citations"] == []
