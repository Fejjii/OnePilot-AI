"""Last-mile recruiter-demo quality: calendar title, Gmail HITL, web synthesis, NovaEdge."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from onepilot.agents.workflow import run_agent
from onepilot.core.config import get_settings
from onepilot.core.constants import Intent, PlanCode, Role
from onepilot.providers.calendar.mock_calendar_provider import MockCalendarProvider
from onepilot.providers.email.gmail_provider import GmailProvider
from onepilot.providers.email.mock_email_provider import MockEmailProvider
from onepilot.schemas.web_search import WebSearchCitation, WebSearchResponse
from onepilot.security.auth import Principal
from onepilot.services.calendar_intent import extract_meeting_title
from onepilot.services.calendar_service import prepare_event_approval
from onepilot.services.lead_service import extract_email

CALENDAR_PROMPT = (
    'Schedule a 30-minute meeting tomorrow at 3 PM titled "OnePilot Live Calendar Test"'
)
EMAIL_PROMPT = (
    "Draft an email to [fejjii.sofiene@gmail.com] with subject\n"
    '"OnePilot Private Demo Test" saying that this is a test of\n'
    "OnePilot's approval-gated Gmail integration."
)
WEB_PROMPT = (
    "Search the web for the latest OpenAI news and summarize the three most "
    "relevant developments with sources."
)
EXPECTED_TITLE = "OnePilot Live Calendar Test"
EXPECTED_EMAIL = "fejjii.sofiene@gmail.com"

TITLE_VARIANTS = (
    CALENDAR_PROMPT,
    'Schedule a 30-minute meeting tomorrow at 3 PM titled "OnePilot Live Calendar Test".',
    "Schedule a 30-minute meeting tomorrow at 3 PM titled “OnePilot Live Calendar Test”",
    "Schedule a 30-minute meeting tomorrow at 3 PM titled OnePilot Live Calendar Test",
    'Schedule a 30-minute meeting tomorrow at 3 PM titled "OnePilot Live Calendar Test',
)


def _register(client: TestClient, *, suffix: str) -> tuple[str, str, str]:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"lastmile{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Last Mile User",
            "organization_name": f"LastMile{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    payload = jose_jwt.get_unverified_claims(token)
    return token, payload["org"], payload["sub"]


def _principal(org_id: str, user_id: str) -> Principal:
    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fail_if_called(label: str):
    def _inner(*_args, **_kwargs):
        raise AssertionError(f"{label} must not run before approval")

    return _inner


class TestCalendarTitlePreservation:
    def test_title_syntax_variants(self) -> None:
        for prompt in TITLE_VARIANTS:
            assert extract_meeting_title(prompt) == EXPECTED_TITLE, prompt

    def test_unquoted_title_does_not_consume_datetime(self) -> None:
        prompt = "Schedule a meeting titled OnePilot Live Calendar Test tomorrow at 3 PM"
        assert extract_meeting_title(prompt) == EXPECTED_TITLE

    def test_prepare_approval_payload_uses_explicit_title(self) -> None:
        for prompt in TITLE_VARIANTS:
            result = prepare_event_approval(
                MagicMock(),
                principal=MagicMock(),
                message=prompt,
                settings=get_settings(),
            )
            assert result["approval_payload"]["summary"] == EXPECTED_TITLE, prompt
            assert result["approval_status"] == "pending"

    def test_chat_api_preserves_title_in_response_and_approval(
        self, client_with_session, monkeypatch
    ) -> None:
        client, _session = client_with_session
        token, _org_id, _user_id = _register(client, suffix="_cal_title")
        monkeypatch.setattr(MockCalendarProvider, "create_event", _fail_if_called("calendar.create"))

        chat = client.post(
            "/chat",
            json={"message": CALENDAR_PROMPT},
            headers=_h(token),
        )
        assert chat.status_code == 200, chat.text
        body = chat.json()
        assert body["intent"] == "calendar_scheduling"
        assert body["approval_required"] is True
        assert body["approval_id"]
        text = body["final_response"] or ""
        assert EXPECTED_TITLE in text
        assert "OnePilot scheduled meeting" not in text
        tz = ZoneInfo("Europe/Berlin")
        tomorrow = (datetime.now(tz) + timedelta(days=1)).date()
        assert "15:00" in text
        assert "15:30" in text
        assert f"{tomorrow.day} {tomorrow.strftime('%B')}" in text or "15:00" in text

        approval = client.get(
            f"/approvals/{body['approval_id']}", headers=_h(token)
        ).json()
        assert approval["proposed_payload"]["summary"] == EXPECTED_TITLE


class TestGmailRecipientAndHitl:
    def test_extract_email_wrappers(self) -> None:
        assert extract_email(f"to [{EXPECTED_EMAIL}]") == EXPECTED_EMAIL
        assert extract_email(f"to <{EXPECTED_EMAIL}>") == EXPECTED_EMAIL
        assert extract_email(f"to ({EXPECTED_EMAIL})") == EXPECTED_EMAIL
        assert extract_email(f"to {EXPECTED_EMAIL}") == EXPECTED_EMAIL

    def test_chat_api_explicit_recipient_pending_no_provider_create(
        self, client_with_session, monkeypatch
    ) -> None:
        client, _session = client_with_session
        token, _org_id, _user_id = _register(client, suffix="_gmail_hitl")
        settings = get_settings()
        assert settings.GMAIL_SEND_ENABLED is False

        gmail_creates: list[object] = []
        mock_creates: list[object] = []
        send_calls: list[object] = []

        def _gmail_create(*args, **kwargs):
            gmail_creates.append((args, kwargs))
            raise AssertionError("Live Gmail create_draft ran before approval")

        def _mock_create(self, *args, **kwargs):
            mock_creates.append((args, kwargs))
            raise AssertionError("Mock Gmail create_draft ran before approval")

        def _send(*args, **kwargs):
            send_calls.append((args, kwargs))
            raise AssertionError("Gmail send must stay disabled")

        monkeypatch.setattr(GmailProvider, "create_draft", _gmail_create)
        monkeypatch.setattr(MockEmailProvider, "create_draft", _mock_create)
        monkeypatch.setattr(GmailProvider, "send_email", _send)
        monkeypatch.setattr(MockEmailProvider, "send_email", _send)
        monkeypatch.setattr(
            "onepilot.tools.email_tool.gmail_service.is_live_gmail_provider",
            lambda *_a, **_k: True,
        )

        chat = client.post("/chat", json={"message": EMAIL_PROMPT}, headers=_h(token))
        assert chat.status_code == 200, chat.text
        body = chat.json()
        assert body["intent"] == "email_drafting"
        assert body["approval_required"] is True
        assert body["approval_id"]
        text = body["final_response"] or ""
        assert EXPECTED_EMAIL in text
        assert "Not specified" not in text
        assert "OnePilot Private Demo Test" in text
        assert "approval-gated Gmail" in text or "approval-gated gmail" in text.lower()
        assert "pending" in text.lower()
        assert not gmail_creates
        assert not mock_creates
        assert not send_calls

        approval = client.get(
            f"/approvals/{body['approval_id']}", headers=_h(token)
        ).json()
        assert approval["action_type"] == "gmail_create_draft"
        assert EXPECTED_EMAIL in approval["proposed_payload"].get("to", [])
        assert approval["proposed_payload"]["subject"] == "OnePilot Private Demo Test"

        original_mock = MockEmailProvider.create_draft

        def _mock_create_ok(self, *args, **kwargs):
            mock_creates.append((args, kwargs))
            return original_mock(self, *args, **kwargs)

        monkeypatch.setattr(MockEmailProvider, "create_draft", _mock_create_ok)

        fake_live = MagicMock()
        fake_live.create_draft.return_value = {
            "status": "success",
            "draft_id": "draft_live_hitl",
            "provider": "gmail",
            "mode": "live",
            "action": "create_draft",
        }
        fake_live.send_email.side_effect = AssertionError("send must stay disabled")
        monkeypatch.setattr(
            "onepilot.services.gmail_service.resolve_email_provider_for_org",
            lambda *_a, **_k: fake_live,
        )

        decided = client.post(
            f"/approvals/{body['approval_id']}/decision",
            json={"status": "approved"},
            headers=_h(token),
        )
        assert decided.status_code == 200, decided.text
        execution = decided.json()["proposed_payload"].get("_execution", {})
        assert execution.get("status") == "success"
        assert execution.get("draft_id") == "draft_live_hitl"
        assert execution.get("action") == "create_draft"
        fake_live.create_draft.assert_called_once()
        fake_live.send_email.assert_not_called()
        assert not send_calls


class TestWebSearchAnswerQuality:
    def test_agent_uses_retrieved_findings_not_meta_copy(
        self, client_with_session, monkeypatch
    ) -> None:
        client, session = client_with_session
        _token, org_id, user_id = _register(client, suffix="_web_quality")
        citations = [
            WebSearchCitation(
                title="OpenAI launches GPT-5 with improved reasoning",
                url="https://openai.com/index/gpt-5",
                snippet="OpenAI launched GPT-5 with stronger reasoning for assistants.",
                source="openai.com",
                published_date="2026-08-20",
                rank=2,
                relevance_score=0.9,
            ),
            WebSearchCitation(
                title="OpenAI adds EU data residency",
                url="https://www.reuters.com/openai-eu-residency",
                snippet="OpenAI announced EU data residency for ChatGPT Enterprise.",
                source="reuters.com",
                published_date="2026-09-01",
                rank=1,
                relevance_score=0.88,
            ),
            WebSearchCitation(
                title="OpenAI expands custom-chip training",
                url="https://techcrunch.com/openai-custom-chips",
                snippet="OpenAI expanded a cloud partnership to train on custom chips.",
                source="techcrunch.com",
                published_date="2026-07-15",
                rank=3,
                relevance_score=0.8,
            ),
        ]

        def _fake_search(*_args, **kwargs):
            request = kwargs.get("request")
            query = getattr(request, "query", WEB_PROMPT)
            return WebSearchResponse(
                query=query,
                citations=citations,
                provider_mode="live",
                fallback_used=False,
                latency_ms=8,
                result_count=len(citations),
            )

        monkeypatch.setattr(
            "onepilot.tools.web_search_tool.web_search_service.search_web",
            _fake_search,
        )
        settings = get_settings().model_copy(
            update={"SERPER_API_KEY": "test-serper-key", "OPENAI_API_KEY": ""}
        )
        state = run_agent(
            session=session,
            principal=_principal(org_id, user_id),
            settings=settings,
            conversation_id="conv_web_last_mile",
            message=WEB_PROMPT,
            history=[],
        )
        assert state.intent == Intent.WEB_SEARCH
        text = state.final_response or ""
        lowered = text.lower()
        assert "## Summary" in text
        assert "## Top findings" in text
        assert "## Sources" in text
        assert "rewrite the brief" not in lowered
        assert "research brief" not in lowered
        assert "GPT-5" in text
        assert "https://openai.com/index/gpt-5" in text
        assert "https://www.reuters.com/openai-eu-residency" in text
        assert "https://evil.example/fake" not in text
        assert "1." in text and "2." in text and "3." in text


class TestPublicDemoNovaEdgeAndSafety:
    def test_demo_start_seeds_novaedge_rag_answer(
        self, client: TestClient, monkeypatch
    ) -> None:
        monkeypatch.setenv("PUBLIC_DEMO_ENABLED", "true")
        get_settings.cache_clear()
        start = client.post("/demo/start")
        assert start.status_code == 200, start.text
        token = start.json()["access_token"]
        docs = client.get("/documents", headers=_h(token)).json()
        assert docs["total"] == 19
        titles = {item["title"] for item in docs["items"]}
        assert any("NovaEdge" in title for title in titles)

        answer = client.post(
            "/knowledge/answer",
            json={"query": "What services does NovaEdge Solutions offer?"},
            headers=_h(token),
        )
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["answer"]
        assert body["citations"]
        joined = " ".join(
            citation.get("document_title", "") for citation in body["citations"]
        )
        assert "NovaEdge" in joined or "NovaEdge" in (body["answer"] or "")

        chat = client.post(
            "/chat",
            json={"message": "What services does NovaEdge Solutions offer?"},
            headers=_h(token),
        )
        assert chat.status_code == 200, chat.text
        chat_body = chat.json()
        assert chat_body["intent"] == "knowledge_search"
        assert chat_body["citations"]
        assert "NovaEdge" in (chat_body["final_response"] or "")

    def test_public_demo_never_calls_live_google(
        self, client: TestClient, monkeypatch
    ) -> None:
        monkeypatch.setenv("PUBLIC_DEMO_ENABLED", "true")
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "public-should-not-use")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "public-should-not-use")
        monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "public-should-not-use")
        get_settings.cache_clear()
        start = client.post("/demo/start")
        assert start.status_code == 200, start.text
        token = start.json()["access_token"]
        settings = get_settings()
        assert settings.PUBLIC_DEMO_ENABLED is True
        assert settings.GMAIL_SEND_ENABLED is False

        monkeypatch.setattr(
            GmailProvider, "create_draft", _fail_if_called("live gmail create_draft")
        )
        monkeypatch.setattr(
            GmailProvider, "send_email", _fail_if_called("live gmail send")
        )
        monkeypatch.setattr(
            MockCalendarProvider,
            "create_event",
            _fail_if_called("calendar create before approval"),
        )

        email = client.post(
            "/chat",
            json={"message": EMAIL_PROMPT},
            headers=_h(token),
        )
        assert email.status_code == 200, email.text
        assert email.json()["approval_required"] is True
        assert email.json()["approval_id"]

        calendar = client.post(
            "/chat",
            json={"message": CALENDAR_PROMPT},
            headers=_h(token),
        )
        assert calendar.status_code == 200, calendar.text
        assert calendar.json()["approval_required"] is True
        assert EXPECTED_TITLE in (calendar.json()["final_response"] or "")
