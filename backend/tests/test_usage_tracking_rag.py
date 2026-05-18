"""Tests for usage tracking around RAG and uploads."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy import select

from onepilot.core.constants import UsageFeature
from onepilot.repositories.models import AuditLog, UsageEvent, UsageQuota
from onepilot.security.auth import decode_access_token


def _register(client: TestClient, suffix: str) -> tuple[str, str]:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"usage{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Usage User",
            "organization_name": f"UsageOrg{suffix}",
        },
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    org_id = decode_access_token(token).organization_id
    return token, org_id


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload(client: TestClient, token: str) -> None:
    files = {"file": ("policy.md", io.BytesIO(b"# Policy\n\ncontent body"), "text/markdown")}
    resp = client.post("/documents/upload", files=files, headers=_h(token))
    assert resp.status_code == 200, resp.text


class TestUsageTrackingForRAG:
    def test_search_increments_quota(self, client_with_session) -> None:
        client, session = client_with_session
        token, org_id = _register(client, "_quota")
        _upload(client, token)
        client.post(
            "/knowledge/search",
            json={"query": "policy"},
            headers=_h(token),
        )
        quota = session.execute(
            select(UsageQuota).where(
                UsageQuota.organization_id == org_id,
                UsageQuota.feature == UsageFeature.RAG_QUERIES.value,
            )
        ).scalar_one_or_none()
        assert quota is not None
        assert quota.used >= 1

    def test_search_records_usage_event(self, client_with_session) -> None:
        client, session = client_with_session
        token, org_id = _register(client, "_event")
        _upload(client, token)
        client.post(
            "/knowledge/search",
            json={"query": "policy"},
            headers=_h(token),
        )
        events = session.execute(
            select(UsageEvent).where(
                UsageEvent.organization_id == org_id,
                UsageEvent.feature == UsageFeature.RAG_QUERIES.value,
            )
        ).scalars().all()
        assert events
        assert any(e.fallback_used for e in events)

    def test_upload_writes_audit_log(self, client_with_session) -> None:
        client, session = client_with_session
        token, org_id = _register(client, "_audit")
        _upload(client, token)
        logs = session.execute(
            select(AuditLog).where(
                AuditLog.organization_id == org_id,
                AuditLog.action == "document.uploaded",
            )
        ).scalars().all()
        assert logs
        first = logs[0]
        assert first.resource_type == "document"
        assert first.detail and first.detail.get("title") == "Policy"
