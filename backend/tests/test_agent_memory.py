"""OP-012: agent memory recall, persist, isolation, and safety."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.agents.workflow import run_agent
from onepilot.core.config import get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.errors import ValidationError
from onepilot.core.ids import new_id
from onepilot.repositories.models import Organization, Subscription
from onepilot.security.auth import Principal
from onepilot.services import agent_memory, memory_service
import pytest


def _org_principal(session: Session, *, suffix: str) -> Principal:
    org_id = new_id("org")
    user_id = f"usr_{suffix}"
    session.add(Organization(id=org_id, name=f"Org{suffix}", slug=f"org-{suffix}"))
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
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


def _register(client: TestClient, *, suffix: str) -> tuple[str, str, str]:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"amem{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Memory User",
            "organization_name": f"MemAgentOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    from jose import jwt as jose_jwt

    payload = jose_jwt.get_unverified_claims(token)
    return token, payload["org"], payload["sub"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestMemorySafety:
    def test_rejects_secret_values(self, db_session: Session) -> None:
        principal = _org_principal(db_session, suffix="sec")
        with pytest.raises(ValidationError):
            memory_service.write_memory(
                db_session,
                principal=principal,
                scope="user",
                key="api_note",
                value="token = sk-abcdefghijklmnopqrstuvwxyz0123456789",
                settings=get_settings(),
            )

    def test_rejects_sensitive_keys(self, db_session: Session) -> None:
        principal = _org_principal(db_session, suffix="key")
        with pytest.raises(ValidationError):
            memory_service.write_memory(
                db_session,
                principal=principal,
                scope="user",
                key="gmail_password",
                value="not-a-secret-looking-value",
                settings=get_settings(),
            )

    def test_prompt_size_limits(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        principal = _org_principal(db_session, suffix="lim")
        settings = get_settings()
        monkeypatch.setattr(settings, "AGENT_MEMORY_MAX_ITEMS", 2)
        monkeypatch.setattr(settings, "AGENT_MEMORY_MAX_CHARS", 80)
        for i in range(5):
            memory_service.write_memory(
                db_session,
                principal=principal,
                scope="user",
                key=f"pref_tone_{i}",
                value=f"prefer formal tone option {i} for emails",
                settings=settings,
            )
        items = memory_service.retrieve_relevant_memory(
            db_session,
            principal=principal,
            query="what tone do I prefer for emails?",
            settings=settings,
        )
        assert len(items) <= 2
        used = sum(len(i.key) + len(i.value) + 8 for i in items)
        assert used <= settings.AGENT_MEMORY_MAX_CHARS


class TestMemoryRetrieval:
    def test_relevant_retrieval_and_exclusion(self, db_session: Session) -> None:
        principal = _org_principal(db_session, suffix="rel")
        settings = get_settings()
        memory_service.write_memory(
            db_session,
            principal=principal,
            scope="user",
            key="pref_email_tone",
            value="always use a warm friendly email tone",
            settings=settings,
        )
        memory_service.write_memory(
            db_session,
            principal=principal,
            scope="user",
            key="lunch_order",
            value="vegetarian burrito on Fridays",
            settings=settings,
        )
        items = memory_service.retrieve_relevant_memory(
            db_session,
            principal=principal,
            query="What email tone should I use?",
            settings=settings,
        )
        keys = {i.key for i in items}
        assert "pref_email_tone" in keys
        assert "lunch_order" not in keys

    def test_unavailable_store_fallback(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        principal = _org_principal(db_session, suffix="fail")
        settings = get_settings()

        def _boom(*_a, **_k):  # type: ignore[no-untyped-def]
            raise RuntimeError("db down")

        monkeypatch.setattr(
            "onepilot.services.memory_service.MemoryItemRepository.list_for_agent_context",
            _boom,
        )
        items = memory_service.retrieve_relevant_memory(
            db_session,
            principal=principal,
            query="tone preference",
            settings=settings,
        )
        assert items == []


class TestMemoryIsolation:
    def test_tenant_isolation(self, db_session: Session) -> None:
        a = _org_principal(db_session, suffix="ta")
        b = _org_principal(db_session, suffix="tb")
        settings = get_settings()
        memory_service.write_memory(
            db_session,
            principal=a,
            scope="user",
            key="pref_tone",
            value="org A prefers formal tone",
            settings=settings,
        )
        items = memory_service.retrieve_relevant_memory(
            db_session,
            principal=b,
            query="formal tone preference",
            settings=settings,
        )
        assert items == []

    def test_user_isolation_within_org(self, db_session: Session) -> None:
        owner = _org_principal(db_session, suffix="ua")
        settings = get_settings()
        other = Principal(
            user_id="usr_other",
            organization_id=owner.organization_id,
            role=Role.MEMBER,
            plan_code=PlanCode.FREE,
        )
        memory_service.write_memory(
            db_session,
            principal=owner,
            scope="user",
            key="pref_tone",
            value="owner prefers short replies",
            settings=settings,
        )
        items = memory_service.retrieve_relevant_memory(
            db_session,
            principal=other,
            query="short replies preference",
            settings=settings,
        )
        assert items == []


class TestDemoIsolation:
    def test_shared_demo_tenant_disables_agent_memory(
        self, db_session: Session
    ) -> None:
        settings = get_settings()
        principal = Principal(
            user_id=settings.DEV_USER_ID,
            organization_id=settings.DEV_ORG_ID,
            role=Role.OWNER,
            plan_code=PlanCode.BUSINESS,
        )
        # Ensure org exists for FK if needed — write path may not require org row
        # for agent_memory_enabled check.
        enabled, reason = memory_service.agent_memory_enabled(
            db_session, principal=principal, settings=settings
        )
        assert enabled is False
        assert reason == "shared_demo_tenant"

    def test_demo_start_clears_user_memory(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PUBLIC_DEMO_ENABLED", "true")
        get_settings.cache_clear()
        try:
            # First start creates the shared demo tenant.
            first = client.post("/demo/start")
            assert first.status_code == 200, first.text
            token = first.json()["access_token"]

            leaked = client.post(
                "/memory",
                json={
                    "scope": "user",
                    "key": "pref_leaked",
                    "value": "visitor A secret preference about pricing",
                },
                headers=_h(token),
            )
            assert leaked.status_code == 200, leaked.text

            # Next demo session must wipe prior visitor memories.
            second = client.post("/demo/start")
            assert second.status_code == 200, second.text
            token2 = second.json()["access_token"]

            remaining = client.get("/memory/user/pref_leaked", headers=_h(token2))
            assert remaining.status_code == 404
        finally:
            monkeypatch.delenv("PUBLIC_DEMO_ENABLED", raising=False)
            get_settings.cache_clear()


class TestDeletionAndControls:
    def test_clear_and_disable(
        self, client_with_session: tuple[TestClient, Session]
    ) -> None:
        client, session = client_with_session
        token, org_id, user_id = _register(client, suffix="_clr")
        settings = get_settings()
        principal = Principal(
            user_id=user_id,
            organization_id=org_id,
            role=Role.OWNER,
            plan_code=PlanCode.FREE,
        )
        memory_service.write_memory(
            session,
            principal=principal,
            scope="user",
            key="pref_tone",
            value="prefer concise answers",
            settings=settings,
        )
        session.commit()

        clear = client.delete("/memory", headers=_h(token))
        assert clear.status_code == 200, clear.text
        assert clear.json()["deleted_count"] >= 1

        disable = client.post(
            "/memory/preferences",
            json={"disabled": True},
            headers=_h(token),
        )
        assert disable.status_code == 200, disable.text
        assert disable.json()["user_disabled"] is True
        assert disable.json()["agent_memory_enabled"] is False

        status = client.get("/memory/status", headers=_h(token))
        assert status.status_code == 200
        assert status.json()["reason"] == "user_disabled"


class TestAgentWorkflowMemory:
    def test_recall_before_generation(
        self, client_with_session: tuple[TestClient, Session]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_wf")
        settings = get_settings()
        principal = Principal(
            user_id=user_id,
            organization_id=org_id,
            role=Role.OWNER,
            plan_code=PlanCode.FREE,
        )
        memory_service.write_memory(
            session,
            principal=principal,
            scope="user",
            key="pref_tone",
            value="prefer concise formal tone in replies",
            settings=settings,
        )
        session.commit()

        state = run_agent(
            session=session,
            principal=principal,
            settings=settings,
            conversation_id="conv_mem",
            message="What tone should you use when emailing customers?",
            history=[],
        )
        assert state.memory_enabled is True
        assert state.memory_item_count >= 1
        assert "Stored memory" in state.memory_block
        assert "pref_tone" in state.memory_block
        assert any(step.step == "recall_memory" for step in state.trace_steps)

    def test_persist_explicit_remember(
        self, client_with_session: tuple[TestClient, Session]
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_ps")
        settings = get_settings()
        principal = Principal(
            user_id=user_id,
            organization_id=org_id,
            role=Role.OWNER,
            plan_code=PlanCode.FREE,
        )
        state = run_agent(
            session=session,
            principal=principal,
            settings=settings,
            conversation_id="conv_persist",
            message="Please remember that I prefer bullet-point summaries.",
            history=[],
        )
        assert any(step.step == "persist_memory" for step in state.trace_steps)
        items = memory_service.retrieve_relevant_memory(
            session,
            principal=principal,
            query="bullet-point summaries preference",
            settings=settings,
        )
        assert any("bullet" in i.value.lower() for i in items)

    def test_extract_candidates_only_explicit(self) -> None:
        assert agent_memory.extract_explicit_memory_candidates(
            "What is our escalation policy?"
        ) == []
        found = agent_memory.extract_explicit_memory_candidates(
            "Remember that our timezone is Europe/Berlin"
        )
        assert len(found) == 1
        assert "Europe/Berlin" in found[0].value
