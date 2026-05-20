"""Tests for the tool registry and individual tools."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.core.config import get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.errors import NotFoundError
from onepilot.security.auth import Principal
from onepilot.tools import registry
from onepilot.tools.base import ToolContext


def _principal(org_id: str, user_id: str) -> Principal:
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
            "email": f"tool{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Tool User",
            "organization_name": f"ToolOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    from jose import jwt as jose_jwt

    token = resp.json()["access_token"]
    claims = jose_jwt.get_unverified_claims(token)
    return token, claims["org"], claims["sub"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload(client: TestClient, token: str, body: bytes) -> None:
    resp = client.post(
        "/documents/upload",
        files={"file": ("policy.md", io.BytesIO(body), "text/markdown")},
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text


class TestRegistry:
    def test_default_tools_registered(self) -> None:
        assert {
            "rag.answer",
            "external.web_search",
            "email.draft",
            "calendar.check_availability",
            "calendar.suggest_slots",
            "calendar.create_event_request",
            "lead.support",
            "chat.general",
        }.issubset(set(registry.names()))

    def test_get_unknown_raises(self) -> None:
        import pytest

        with pytest.raises(NotFoundError):
            registry.get("nonexistent.tool")


class TestRAGTool:
    def test_rag_tool_returns_citations(
        self,
        client_with_session: tuple[TestClient, Session],
    ) -> None:
        client, session = client_with_session
        token, org_id, user_id = _register(client, suffix="_rag_tool")
        _upload(
            client,
            token,
            b"# Pricing\n\nThe Pro plan is $29 per month and includes 500 chat messages.",
        )
        result = registry.get("rag.answer").run(
            ToolContext(
                session=session,
                principal=_principal(org_id, user_id),
                settings=get_settings(),
            ),
            query="How much does the Pro plan cost?",
        )
        assert result.tool_name == "rag.answer"
        assert result.citations  # at least one citation
        assert "fallback_used" in result.safety_flags


class TestEmailTool:
    def test_email_tool_produces_draft_and_proposes_approval(
        self,
        client_with_session: tuple[TestClient, Session],
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_email_tool")
        result = registry.get("email.draft").run(
            ToolContext(
                session=session,
                principal=_principal(org_id, user_id),
                settings=get_settings(),
            ),
            context="Apologise for the delay and propose a 15-minute call.",
            tone="professional",
        )
        draft = result.output["draft"]
        assert draft["subject"]
        assert draft["body"]
        assert result.approval_required is False
        assert result.approval_action_type == "gmail_create_draft"


class TestLeadTool:
    def test_lead_tool_does_not_capture_without_trigger(
        self,
        client_with_session: tuple[TestClient, Session],
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_lead_tool")
        result = registry.get("lead.support").run(
            ToolContext(
                session=session,
                principal=_principal(org_id, user_id),
                settings=get_settings(),
            ),
            message="A prospect from Beta Corp wants to know our pricing.",
        )
        assert result.output["captured"] is False
        assert result.output["urgency"] in {"low", "medium", "high"}


class TestGeneralChatTool:
    def test_general_chat_returns_reply(
        self,
        client_with_session: tuple[TestClient, Session],
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_gen_tool")
        result = registry.get("chat.general").run(
            ToolContext(
                session=session,
                principal=_principal(org_id, user_id),
                settings=get_settings(),
            ),
            message="Hi there",
            history=[],
        )
        assert result.output["reply"]
        # The fallback provider always sets is_fallback=True without OPENAI_API_KEY.
        assert "fallback_used" in result.safety_flags
