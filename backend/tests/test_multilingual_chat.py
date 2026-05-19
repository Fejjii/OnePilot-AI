"""Integration tests for multilingual chat behavior."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from onepilot.core.constants import LanguagePreference, MessageClass
from onepilot.core.config import Settings
from onepilot.schemas.chat import ChatRequest
from onepilot.security.auth import Principal
from onepilot.tools.base import ToolContext
from onepilot.tools.general_chat_tool import GeneralChatTool


def test_chat_request_language_preference_default() -> None:
    req = ChatRequest(message="Hello")
    assert req.language_preference == LanguagePreference.AUTO


def test_chat_request_language_preference_explicit() -> None:
    req = ChatRequest(message="Hello", language_preference=LanguagePreference.DE)
    assert req.language_preference == LanguagePreference.DE


class TestGeneralChatMultilingual:
    @pytest.fixture
    def ctx(self) -> ToolContext:
        from onepilot.core.constants import PlanCode, Role

        return ToolContext(
            session=Mock(),
            principal=Principal(
                user_id="u1",
                organization_id="o1",
                role=Role.MEMBER,
                plan_code=PlanCode.FREE,
            ),
            settings=Settings(
                DATABASE_URL="sqlite:///:memory:",
                SECRET_KEY="test",
                OPENAI_API_KEY="",
            ),
        )

    def test_capability_response_german(self, ctx: ToolContext) -> None:
        tool = GeneralChatTool()
        result = tool.run(
            ctx,
            message="Was können Sie tun?",
            message_class=MessageClass.CAPABILITY_OR_HELP,
            response_language="de",
        )
        assert "Wissen" in result.output["reply"] or "helfen" in result.output["reply"]

    def test_capability_response_english(self, ctx: ToolContext) -> None:
        tool = GeneralChatTool()
        result = tool.run(
            ctx,
            message="What can you do?",
            message_class=MessageClass.CAPABILITY_OR_HELP,
            response_language="en",
        )
        assert "Knowledge" in result.output["reply"]


class TestChatEndpointLanguageFields:
    def test_chat_response_includes_language_fields(
        self, client: TestClient
    ) -> None:
        from tests.test_chat_endpoint import _h, _register

        token = _register(client, suffix="_lang")
        resp = client.post(
            "/chat",
            json={
                "message": "Welche Integrationen unterstützt NovaEdge?",
                "language_preference": "auto",
            },
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["detected_language"] == "de"
        assert data["response_language"] == "de"
        assert data["language_preference"] == "auto"
        assert any(s["step"] == "resolve_language" for s in data["trace_steps"])

    def test_explicit_language_preference_overrides_detection(
        self, client: TestClient
    ) -> None:
        from tests.test_chat_endpoint import _h, _register

        token = _register(client, suffix="_lang_en")
        resp = client.post(
            "/chat",
            json={
                "message": "Welche Integrationen?",
                "language_preference": "en",
            },
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["detected_language"] == "de"
        assert data["response_language"] == "en"
        assert data["language_preference"] == "en"


class TestRAGMultilingual:
    def test_rag_tool_passes_response_language(self) -> None:
        from onepilot.tools.rag_tool import RAGTool

        tool = RAGTool()
        ctx = Mock()
        ctx.session = Mock()
        ctx.principal = Mock()
        ctx.principal.organization_id = "org"
        ctx.principal.user_id = "user"
        ctx.settings = Settings(
            DATABASE_URL="sqlite:///:memory:",
            SECRET_KEY="test",
            OPENAI_API_KEY="",
        )

        with patch("onepilot.tools.rag_tool.rag_service.answer") as mock_answer:
            from onepilot.services.rag_service import AnswerOutcome

            mock_answer.return_value = AnswerOutcome(
                query="test",
                answer="Antwort",
                confidence=0.8,
                hits=[],
                weak_evidence=False,
                fallback_used=True,
                model="test",
            )
            tool.run(
                ctx,
                query="Welche Integrationen?",
                response_language="de",
                detected_language="de",
            )
            mock_answer.assert_called_once()
            call_kwargs = mock_answer.call_args.kwargs
            assert call_kwargs["response_language"] == "de"
            assert call_kwargs["detected_language"] == "de"


class TestConversationLanguageMetadata:
    def test_conversation_returns_language_metadata(
        self, client: TestClient
    ) -> None:
        from tests.test_chat_endpoint import _h, _register

        token = _register(client, suffix="_conv_lang")
        chat_resp = client.post(
            "/chat",
            json={
                "message": "Welche Integrationen unterstützt NovaEdge?",
                "language_preference": "auto",
            },
            headers=_h(token),
        )
        assert chat_resp.status_code == 200, chat_resp.text
        body = chat_resp.json()
        conv_id = body["conversation_id"]
        assert body["detected_language"] == "de"
        assert body["response_language"] == "de"

        detail = client.get(f"/conversations/{conv_id}", headers=_h(token))
        assert detail.status_code == 200, detail.text
        assistant_msgs = [
            m for m in detail.json()["messages"] if m["role"] == "assistant"
        ]
        assert assistant_msgs
        meta = assistant_msgs[-1]
        assert meta.get("detected_language") == "de"
        assert meta.get("response_language") == "de"
        assert meta.get("language_preference") == "auto"
