"""Multilingual RAG retrieval and confidence tests."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from onepilot.core.constants import LanguageCode
from onepilot.services.language_service import (
    build_english_retrieval_queries,
    cap_confidence_for_weak_evidence,
    detect_language_heuristic,
)
_SERVICES_OVERVIEW = b"""# NovaEdge Solutions - Services Overview

## Core Services

NovaEdge Solutions provides AI-powered customer support automation.

### Customer Support Automation
Automatically handle common customer inquiries.

### Lead Qualification
Intelligent lead scoring and qualification.

### Email Workflow Automation
Automate repetitive email tasks and customer communications.

### Internal Knowledge Search
Search across your knowledge base from conversations.

### Appointment Booking
Schedule meetings and appointments with customers.
"""

_INTEGRATION_GUIDE = b"""# Integration Guide - HubSpot, Gmail, Google Calendar

## Supported Integrations

NovaEdge Solutions integrates with your existing tools.

### HubSpot Integration
Connect your HubSpot CRM to sync contacts and deals.

### Gmail Integration
Integrate with Gmail / Google Workspace for email management.

### Google Calendar Integration
Sync meetings and appointments with Google Calendar.
"""


def _register(client: TestClient, *, suffix: str) -> str:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"mlrag{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "ML RAG User",
            "organization_name": f"MLRagOrg{suffix}",
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


@pytest.fixture
def indexed_client(client: TestClient) -> tuple[TestClient, str]:
    token = _register(client, suffix="_ml")
    _upload(client, token, "services_overview.md", _SERVICES_OVERVIEW)
    _upload(client, token, "integration_guide.md", _INTEGRATION_GUIDE)
    return client, token


class TestMultilingualDetection:
    def test_german_integration_query_is_de_not_fr(self) -> None:
        result = detect_language_heuristic(
            "Welche Integrationen unterstützt NovaEdge Solutions?"
        )
        assert result.language == LanguageCode.DE
        assert result.language != LanguageCode.FR


class TestMultilingualRetrieval:
    def test_german_integrations_retrieves_integration_guide(
        self, indexed_client: tuple[TestClient, str]
    ) -> None:
        client, token = indexed_client
        query = "Welche Integrationen unterstützt NovaEdge Solutions?"
        resp = client.post(
            "/knowledge/search",
            json={"query": query, "top_k": 5},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        titles = [h["document_title"] for h in body.get("results", [])]
        assert any("Integration Guide" in t for t in titles), titles

    def test_french_services_retrieves_services_overview(
        self, indexed_client: tuple[TestClient, str]
    ) -> None:
        client, token = indexed_client
        query = "Quels services propose NovaEdge Solutions?"
        resp = client.post(
            "/knowledge/search",
            json={"query": query, "top_k": 5},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        titles = [h["document_title"] for h in resp.json().get("results", [])]
        assert any("Services Overview" in t for t in titles), titles

    def test_spanish_integrations_retrieves_integration_guide(
        self, indexed_client: tuple[TestClient, str]
    ) -> None:
        client, token = indexed_client
        query = "Qué integraciones admite NovaEdge Solutions?"
        resp = client.post(
            "/knowledge/search",
            json={"query": query, "top_k": 5},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        titles = [h["document_title"] for h in resp.json().get("results", [])]
        assert any("Integration Guide" in t for t in titles), titles


class TestMultilingualChatEndpoint:
    def test_german_chat_response_language(
        self, indexed_client: tuple[TestClient, str]
    ) -> None:
        client, token = indexed_client
        resp = client.post(
            "/chat",
            json={
                "message": "Welche Integrationen unterstützt NovaEdge Solutions?",
                "language_preference": "auto",
            },
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["detected_language"] == "de"
        assert data["response_language"] == "de"
        assert data["language_preference"] == "auto"

    def test_explicit_german_preference_on_english_input(
        self, indexed_client: tuple[TestClient, str]
    ) -> None:
        client, token = indexed_client
        resp = client.post(
            "/chat",
            json={
                "message": "What integrations are supported?",
                "language_preference": "de",
            },
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["response_language"] == "de"
        assert data["language_preference"] == "de"


class TestWeakEvidenceConfidence:
    def test_weak_evidence_caps_confidence(self) -> None:
        assert cap_confidence_for_weak_evidence(0.85, weak_evidence=True) <= 0.6
