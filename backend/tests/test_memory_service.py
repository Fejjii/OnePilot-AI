"""Tests for memory service and /memory endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.core.constants import PlanCode, Role
from onepilot.core.errors import NotFoundError, ValidationError
from onepilot.core.ids import new_id
from onepilot.repositories.models import Organization, Subscription
from onepilot.security.auth import Principal
from onepilot.services import memory_service


def _principal(session: Session) -> Principal:
    org_id = new_id("org")
    session.add(Organization(id=org_id, name="MemOrg", slug=f"mem-{org_id[:8]}"))
    session.add(
        Subscription(
            id=new_id("sub"),
            organization_id=org_id,
            plan_code=PlanCode.FREE,
            status="active",
        )
    )
    session.flush()
    return Principal(
        user_id="usr_mem",
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


class TestMemoryService:
    def test_write_and_read(self, db_session: Session) -> None:
        principal = _principal(db_session)
        memory_service.write_memory(
            db_session,
            principal=principal,
            scope="user",
            key="preferred_tone",
            value="warm",
        )
        item = memory_service.read_memory(
            db_session, principal=principal, scope="user", key="preferred_tone"
        )
        assert item is not None
        assert item.value == "warm"

    def test_write_updates_existing_value(self, db_session: Session) -> None:
        principal = _principal(db_session)
        memory_service.write_memory(
            db_session, principal=principal, scope="user", key="tz", value="UTC"
        )
        memory_service.write_memory(
            db_session, principal=principal, scope="user", key="tz", value="Europe/Paris"
        )
        item = memory_service.read_memory(
            db_session, principal=principal, scope="user", key="tz"
        )
        assert item is not None
        assert item.value == "Europe/Paris"

    def test_ttl_expires(self, db_session: Session) -> None:
        principal = _principal(db_session)
        item = memory_service.write_memory(
            db_session,
            principal=principal,
            scope="agent",
            key="temp",
            value="x",
            ttl_seconds=60,
        )
        assert item.expires_at is not None
        # Force expiry.
        item.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db_session.flush()
        gone = memory_service.read_memory(
            db_session, principal=principal, scope="agent", key="temp"
        )
        assert gone is None

    def test_delete_memory_not_found(self, db_session: Session) -> None:
        principal = _principal(db_session)
        with pytest.raises(NotFoundError):
            memory_service.delete_memory(
                db_session, principal=principal, scope="user", key="ghost"
            )

    def test_invalid_scope_raises(self, db_session: Session) -> None:
        principal = _principal(db_session)
        with pytest.raises(ValidationError):
            memory_service.write_memory(
                db_session,
                principal=principal,
                scope="invalid_scope",
                key="x",
                value="y",
            )

    def test_organization_scope_has_no_user_id(self, db_session: Session) -> None:
        principal = _principal(db_session)
        item = memory_service.write_memory(
            db_session,
            principal=principal,
            scope="organization",
            key="brand_voice",
            value="warm",
        )
        assert item.user_id is None


class TestMemoryEndpoints:
    def _register(self, client: TestClient, *, suffix: str) -> str:
        resp = client.post(
            "/auth/register",
            json={
                "email": f"mem{suffix}@example.com",
                "password": "strongpass123",
                "full_name": "Mem User",
                "organization_name": f"MemOrg{suffix}",
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    def _h(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_write_read_delete(self, client: TestClient) -> None:
        token = self._register(client, suffix="_crud")
        write = client.post(
            "/memory",
            json={"scope": "user", "key": "tone", "value": "formal"},
            headers=self._h(token),
        )
        assert write.status_code == 200, write.text

        read = client.get("/memory/user/tone", headers=self._h(token))
        assert read.status_code == 200
        assert read.json()["value"] == "formal"

        delete = client.delete("/memory/user/tone", headers=self._h(token))
        assert delete.status_code == 204

        missing = client.get("/memory/user/tone", headers=self._h(token))
        assert missing.status_code == 404
