"""Tests for the demo knowledge-base seeder and the /demo/seed endpoint."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


def _register(client: TestClient, *, suffix: str) -> str:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"seed{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Seed User",
            "organization_name": f"SeedOrg{suffix}",
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestDemoSeedEndpoint:
    def test_seed_creates_documents(self, client: TestClient) -> None:
        token = _register(client, suffix="_create")
        resp = client.post("/demo/seed", headers=_h(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["documents_created"] == 19
        assert body["documents_skipped"] == 0
        assert body["total_documents"] == 19
        assert body["total_chunks"] > 0
        assert body["vector_upsert_count"] >= 0

    def test_seed_is_idempotent(self, client: TestClient) -> None:
        token = _register(client, suffix="_idem")
        first = client.post("/demo/seed", headers=_h(token)).json()
        second = client.post("/demo/seed", headers=_h(token)).json()
        assert second["documents_created"] == 0
        assert second["documents_skipped"] == first["documents_created"]
        assert second["total_documents"] == first["total_documents"]

    def test_seeded_documents_are_searchable(self, client: TestClient) -> None:
        token = _register(client, suffix="_search")
        client.post("/demo/seed", headers=_h(token))
        resp = client.post(
            "/knowledge/search",
            json={"query": "How much does the Growth retainer cost?"},
            headers=_h(token),
        )
        body = resp.json()
        assert body["results"], body
        titles = {r["document_title"] for r in body["results"]}
        assert any("Pricing" in t for t in titles)

    def test_seeded_documents_support_grounded_answers(self, client: TestClient) -> None:
        token = _register(client, suffix="_answer")
        client.post("/demo/seed", headers=_h(token))
        resp = client.post(
            "/knowledge/answer",
            json={"query": "How much does the Growth plan cost per month?"},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["answer"]
        assert body["citations"], body
        assert any("Pricing" in citation["document_title"] for citation in body["citations"])

    def test_seed_docs_visible_via_get_documents(self, client: TestClient) -> None:
        """GET /documents with the seed token must return the seeded documents."""
        token = _register(client, suffix="_visibility")
        client.post("/demo/seed", headers=_h(token))
        resp = client.get("/documents", headers=_h(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 19


class TestDemoSetupEndpoint:
    def test_setup_returns_deterministic_ids(self, client: TestClient) -> None:
        """POST /demo/setup must return the configured DEV_ORG_ID / DEV_USER_ID."""
        resp = client.post("/demo/setup")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["organization_id"] == os.environ.get(
            "DEV_ORG_ID", "org_demo_onepilot"
        )
        assert body["user_id"] == os.environ.get("DEV_USER_ID", "usr_demo_admin")
        assert body["access_token"]

    def test_setup_is_idempotent(self, client: TestClient) -> None:
        """Calling /demo/setup twice must yield the same IDs (no duplicate rows)."""
        first = client.post("/demo/setup").json()
        second = client.post("/demo/setup").json()
        assert first["organization_id"] == second["organization_id"]
        assert first["user_id"] == second["user_id"]

    def test_setup_then_seed_then_documents_aligned(self, client: TestClient) -> None:
        """Full flow: setup → seed → GET /documents all use the same org."""
        setup = client.post("/demo/setup").json()
        token = setup["access_token"]
        org_id = setup["organization_id"]

        seed_resp = client.post("/demo/seed", headers=_h(token))
        assert seed_resp.status_code == 200, seed_resp.text
        assert seed_resp.json()["total_documents"] > 0

        docs_resp = client.get("/documents", headers=_h(token))
        assert docs_resp.status_code == 200, docs_resp.text
        body = docs_resp.json()
        assert body["total"] > 0, (
            f"GET /documents returned 0 for org {org_id} — tenant mismatch"
        )

    def test_setup_org_matches_configured_dev_org_id(self, client: TestClient) -> None:
        """The org returned by /demo/setup must match DEV_ORG_ID from settings."""
        import os
        expected_org = os.environ.get("DEV_ORG_ID", "org_demo_onepilot")
        setup = client.post("/demo/setup").json()
        assert setup["organization_id"] == expected_org, (
            f"setup org {setup['organization_id']} != DEV_ORG_ID {expected_org}"
        )

    def test_setup_blocked_in_production(self, client: TestClient, monkeypatch) -> None:
        """POST /demo/setup must return 403 in production."""
        monkeypatch.setenv("APP_ENV", "production")
        from onepilot.core.config import get_settings
        get_settings.cache_clear()
        try:
            resp = client.post("/demo/setup")
            assert resp.status_code == 403
        finally:
            monkeypatch.setenv("APP_ENV", "test")
            get_settings.cache_clear()
