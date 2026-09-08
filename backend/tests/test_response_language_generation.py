"""Explicit response-language preference must change generated content.

English prompts with language_preference fr/de/es must produce French/German/
Spanish bodies and surrounding prose, not only the approval footnote.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from sqlalchemy.orm import Session

from onepilot.agents.workflow import run_agent
from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import Intent, LanguageCode, LanguagePreference, PlanCode, Role
from onepilot.providers.llm.base import LLMResponse
from onepilot.schemas.web_search import WebSearchCitation, WebSearchResponse
from onepilot.security.auth import Principal
from onepilot.services import email_service
from onepilot.services.fallback_answer import synthesize_answer
from onepilot.services.language_service import (
    resolve_response_language,
    response_language_instruction,
)
from onepilot.services.reranker import RerankHit
from onepilot.services.response_i18n import response_copy
from onepilot.services.web_synthesis import (
    maybe_llm_polish,
    synthesize_combined,
    synthesize_web_only,
)
from tests.test_chat_endpoint import _h, _register


ENGLISH_EMAIL = (
    "Draft a follow-up email to sarah.chen@brightline.io about scheduling an intro call."
)
ENGLISH_WEB = "Search the web for the latest OpenAI news and summarize the three most relevant developments."
ENGLISH_RAG = "What services does NovaEdge Solutions offer?"

LANGUAGE_MARKERS = {
    LanguagePreference.FR: ("Cordialement", "Bonjour", "Destinataire", "Résumé"),
    LanguagePreference.DE: ("Mit freundlichen Grüßen", "Hallo", "Empfänger", "Zusammenfassung"),
    LanguagePreference.ES: ("Un cordial saludo", "Hola", "Destinatario", "Resumen"),
}

ENGLISH_BODY_MARKERS = (
    "I wanted to follow up",
    "Best regards,\nThe OnePilot team",
    "Suggested next step:",
)


def _principal() -> Principal:
    return Principal(
        user_id="usr_lang",
        organization_id="org_lang",
        role=Role.OWNER,
        plan_code=PlanCode.BUSINESS,
    )


def _web_response() -> WebSearchResponse:
    return WebSearchResponse(
        query=ENGLISH_WEB,
        citations=[
            WebSearchCitation(
                title="OpenAI launches GPT-5 with improved reasoning",
                url="https://openai.com/index/gpt-5",
                snippet="OpenAI launched GPT-5, describing stronger reasoning.",
                source="openai.com",
                published_date="2026-08-20",
                rank=1,
                relevance_score=0.9,
            )
        ],
        provider_mode="live",
        fallback_used=False,
        result_count=1,
    )


class TestLanguageInstructionContract:
    def test_instruction_requires_output_language_even_if_prompt_differs(self) -> None:
        text = response_language_instruction(LanguageCode.FR)
        lowered = text.lower()
        assert "french" in lowered
        assert "even if" in lowered
        assert "email addresses" in lowered
        assert "urls" in lowered

    @pytest.mark.parametrize(
        ("preference", "expected"),
        [
            (LanguagePreference.FR, LanguageCode.FR),
            (LanguagePreference.DE, LanguageCode.DE),
            (LanguagePreference.ES, LanguageCode.ES),
        ],
    )
    def test_explicit_preference_overrides_english_detection(
        self, preference: LanguagePreference, expected: LanguageCode
    ) -> None:
        lang = resolve_response_language(preference, LanguageCode.EN, 0.95)
        assert lang == expected


class TestEmailExplicitPreference:
    @pytest.mark.parametrize("preference", ["fr", "de", "es"])
    def test_fallback_draft_uses_preference_not_prompt_language(
        self, preference: str
    ) -> None:
        copy = response_copy(preference)
        subject, body = email_service._fallback_draft(  # noqa: SLF001
            ENGLISH_EMAIL,
            "professional",
            "Sarah Chen",
            {
                "name": "Sarah Chen",
                "company": "Brightline Analytics",
                "pain_point": "Support team overwhelmed during product launches",
                "recommended_next_action": "Schedule discovery call",
            },
            preference,
        )
        assert "Brightline Analytics" in body
        assert "Sarah Chen" in body
        assert "sarah.chen@brightline.io" not in subject
        assert copy.email_signoff.split("\n")[0] in body
        for english in ENGLISH_BODY_MARKERS:
            assert english not in body
        assert "I wanted to follow up" not in body

    def test_llm_prompt_includes_required_output_language(
        self, db_session: Session
    ) -> None:
        llm = MagicMock()
        llm.chat.return_value = LLMResponse(
            content="Subject: Suivi\n\nBonjour Sarah,\n\nCordialement,\nL'équipe OnePilot",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            finish_reason="stop",
        )
        outcome = email_service.draft_email(
            db_session,
            principal=_principal(),
            context=ENGLISH_EMAIL,
            recipient_name="Sarah Chen",
            recipient_email="sarah.chen@brightline.io",
            settings=Settings(),
            llm=llm,
            enforce_quota=False,
            response_language="fr",
        )
        system = llm.chat.call_args.kwargs["messages"][0]["content"]
        user = llm.chat.call_args.kwargs["messages"][1]["content"]
        assert "French" in system
        assert "even if" in system.lower()
        assert "Required output language: French" in user
        assert "sarah.chen@brightline.io" in user
        assert "Bonjour" in outcome.draft.body
        assert "Cordialement" in outcome.draft.body

    def test_explicit_subject_is_preserved(self) -> None:
        _, body = email_service._fallback_draft(  # noqa: SLF001
            'Draft an email with subject "Q3 Brightline recap" saying we should talk.',
            "professional",
            None,
            None,
            "fr",
        )
        subject, _ = email_service._fallback_draft(  # noqa: SLF001
            'Draft an email with subject "Q3 Brightline recap" saying we should talk.',
            "professional",
            None,
            None,
            "fr",
        )
        assert subject == "Q3 Brightline recap"
        assert "we should talk" in body.lower()
        assert "Cordialement" in body


class TestWebAndRagExplicitPreference:
    @pytest.mark.parametrize("preference", ["fr", "de", "es"])
    def test_web_synthesis_localizes_headings_and_keeps_source_literals(
        self, preference: str
    ) -> None:
        copy = response_copy(preference)
        text = synthesize_web_only(
            query=ENGLISH_WEB,
            web=_web_response(),
            configured=True,
            response_language=preference,
        )
        assert f"## {copy.summary_heading}" in text
        assert f"## {copy.top_findings_heading}" in text
        assert f"## {copy.sources_heading}" in text
        assert "OpenAI launches GPT-5 with improved reasoning" in text
        assert "https://openai.com/index/gpt-5" in text
        assert "## Summary" not in text or preference == "en"

    @pytest.mark.parametrize("preference", ["fr", "de", "es"])
    def test_web_user_facing_answer_uses_preference_not_english_snippets(
        self, preference: str
    ) -> None:
        copy = response_copy(preference)
        draft = synthesize_web_only(
            query=ENGLISH_WEB,
            web=_web_response(),
            configured=True,
            response_language=preference,
        )
        result = maybe_llm_polish(
            query=ENGLISH_WEB,
            draft=draft,
            settings=Settings(OPENAI_API_KEY="", SERPER_API_KEY="test-serper"),
            citations=_web_response().citations,
            response_language=preference,
        )
        generated = result.text.split(f"## {copy.sources_heading}", 1)[0]
        assert f"## {copy.summary_heading}" in result.text
        assert "OpenAI launched GPT-5, describing stronger reasoning" not in generated
        assert "OpenAI launches GPT-5 with improved reasoning" in result.text
        assert "https://openai.com/index/gpt-5" in result.text
        assert copy.web_see_original_excerpt in generated
        sources = result.text.split(f"## {copy.sources_heading}", 1)[1]
        assert "OpenAI launched GPT-5, describing stronger reasoning" in sources

    @pytest.mark.parametrize("preference", ["fr", "de", "es"])
    def test_web_and_knowledge_user_facing_answer_uses_preference(
        self, preference: str
    ) -> None:
        copy = response_copy(preference)
        internal = {
            "fr": "NovaEdge Solutions fournit une automatisation du support.",
            "de": "NovaEdge Solutions bietet Automatisierung für den Kundensupport.",
            "es": "NovaEdge Solutions ofrece automatización de soporte al cliente.",
        }[preference]
        draft = synthesize_combined(
            query=ENGLISH_WEB,
            web=_web_response(),
            internal_answer=internal,
            internal_weak=False,
            configured=True,
            response_language=preference,
        )
        result = maybe_llm_polish(
            query=ENGLISH_WEB,
            draft=draft,
            settings=Settings(OPENAI_API_KEY=""),
            citations=_web_response().citations,
            response_language=preference,
        )
        generated = result.text.split(f"## {copy.evidence_heading}", 1)[0]
        assert f"## {copy.summary_heading}" in result.text
        assert internal in result.text
        assert "OpenAI launched GPT-5, describing stronger reasoning" not in generated
        assert "https://openai.com/index/gpt-5" in result.text
        assert copy.combined_research_for.split("{")[0].strip() in result.text

    @pytest.mark.parametrize("preference", ["fr", "de", "es"])
    def test_rag_fallback_localizes_headings_and_keeps_document_title(
        self, preference: str
    ) -> None:
        copy = response_copy(preference)
        chunk = MagicMock()
        chunk.content = (
            "NovaEdge Solutions provides AI-powered customer support automation. "
            "Lead qualification is included in the Growth plan."
        )
        hit = RerankHit(
            chunk=chunk,
            document_title="NovaEdge Services Overview",
            vector_score=0.9,
            rerank_score=0.9,
            signals={},
        )
        text = synthesize_answer(
            ENGLISH_RAG, [hit], response_language=preference
        )
        assert f"## {copy.summary_heading}" in text
        assert "NovaEdge Services Overview" in text
        assert copy.rag_next_action in text
        if preference != "en":
            assert "## Summary" not in text


class TestChatApiExplicitPreference:
    @pytest.mark.parametrize(
        ("preference", "markers"),
        [
            ("fr", LANGUAGE_MARKERS[LanguagePreference.FR]),
            ("de", LANGUAGE_MARKERS[LanguagePreference.DE]),
            ("es", LANGUAGE_MARKERS[LanguagePreference.ES]),
        ],
    )
    def test_english_email_prompt_generates_preferred_language_body(
        self,
        client: TestClient,
        preference: str,
        markers: tuple[str, ...],
    ) -> None:
        token = _register(client, suffix=f"_pref_{preference}")
        resp = client.post(
            "/chat",
            json={
                "message": ENGLISH_EMAIL,
                "language_preference": preference,
            },
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["detected_language"] == "en"
        assert data["response_language"] == preference
        assert data["language_preference"] == preference
        text = data["final_response"]
        assert any(marker in text for marker in markers[:3])
        assert "I wanted to follow up" not in text
        footnote = {
            "fr": "Approbation en attente",
            "de": "Genehmigung ausstehend",
            "es": "Aprobación pendiente",
        }[preference]
        assert footnote in text
        body_without_footnote = text.split("*")[0]
        assert any(
            marker in body_without_footnote for marker in markers[:3]
        ), text

    @pytest.mark.parametrize("preference", ["fr", "de", "es"])
    def test_english_web_prompt_uses_localized_headings(
        self, client: TestClient, preference: str
    ) -> None:
        token = _register(client, suffix=f"_web_{preference}")
        resp = client.post(
            "/chat",
            json={
                "message": ENGLISH_WEB,
                "language_preference": preference,
            },
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["response_language"] == preference
        copy = response_copy(preference)
        text = data["final_response"]
        assert (
            f"## {copy.summary_heading}" in text
            or f"## {copy.top_findings_heading}" in text
            or copy.web_unconfigured_summary[:40] in text
            or copy.summary_heading in text
        )


def _live_web_response(query: str) -> WebSearchResponse:
    return WebSearchResponse(
        query=query,
        citations=[
            WebSearchCitation(
                title="OpenAI launches GPT-5 with improved reasoning",
                url="https://openai.com/index/gpt-5",
                snippet="OpenAI launched GPT-5, describing stronger reasoning.",
                source="openai.com",
                published_date="2026-08-20",
                rank=1,
                relevance_score=0.9,
            ),
            WebSearchCitation(
                title="OpenAI adds EU data residency for ChatGPT Enterprise",
                url="https://www.reuters.com/openai-eu-residency",
                snippet="OpenAI announced EU data residency options for ChatGPT Enterprise.",
                source="reuters.com",
                published_date="2026-09-01",
                rank=2,
                relevance_score=0.88,
            ),
        ],
        provider_mode="live",
        fallback_used=False,
        latency_ms=8,
        result_count=2,
    )


def _patch_live_web_search(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_search(*_args, **kwargs):
        request = kwargs.get("request")
        query = getattr(request, "query", ENGLISH_WEB)
        return _live_web_response(query)

    monkeypatch.setattr(
        "onepilot.tools.web_search_tool.web_search_service.search_web",
        _fake_search,
    )


class TestWebWorkflowExplicitPreference:
    @pytest.mark.parametrize("preference", ["fr", "de", "es"])
    def test_english_web_search_final_answer_uses_response_language(
        self, client_with_session, monkeypatch: pytest.MonkeyPatch, preference: str
    ) -> None:
        client, session = client_with_session
        token = _register(client, suffix=f"_web_wf_{preference}")
        claims = jose_jwt.get_unverified_claims(token)
        _patch_live_web_search(monkeypatch)
        settings = get_settings().model_copy(
            update={"SERPER_API_KEY": "test-serper-key", "OPENAI_API_KEY": ""}
        )
        state = run_agent(
            session=session,
            principal=Principal(
                user_id=claims["sub"],
                organization_id=claims["org"],
                role=Role.OWNER,
                plan_code=PlanCode.FREE,
            ),
            settings=settings,
            conversation_id=f"conv_web_lang_{preference}",
            message=ENGLISH_WEB,
            language_preference=preference,
        )
        copy = response_copy(preference)
        text = state.final_response or ""
        generated = text.split(f"## {copy.sources_heading}", 1)[0]
        assert state.intent == Intent.WEB_SEARCH
        assert state.response_language == preference
        assert f"## {copy.summary_heading}" in text
        assert "OpenAI launched GPT-5, describing stronger reasoning" not in generated
        assert "https://openai.com/index/gpt-5" in text
        assert "OpenAI launches GPT-5 with improved reasoning" in text

    @pytest.mark.parametrize("preference", ["fr", "de", "es"])
    def test_english_web_and_knowledge_final_answer_uses_response_language(
        self, client_with_session, monkeypatch: pytest.MonkeyPatch, preference: str
    ) -> None:
        client, session = client_with_session
        token = _register(client, suffix=f"_webkb_wf_{preference}")
        claims = jose_jwt.get_unverified_claims(token)
        _patch_live_web_search(monkeypatch)
        settings = get_settings().model_copy(
            update={"SERPER_API_KEY": "test-serper-key", "OPENAI_API_KEY": ""}
        )
        state = run_agent(
            session=session,
            principal=Principal(
                user_id=claims["sub"],
                organization_id=claims["org"],
                role=Role.OWNER,
                plan_code=PlanCode.FREE,
            ),
            settings=settings,
            conversation_id=f"conv_webkb_lang_{preference}",
            message=(
                "Find recent OpenAI news and compare them with "
                "NovaEdge Solutions services."
            ),
            language_preference=preference,
        )
        copy = response_copy(preference)
        text = state.final_response or ""
        generated = text.split(f"## {copy.evidence_heading}", 1)[0]
        assert state.intent == Intent.WEB_AND_KNOWLEDGE
        assert state.response_language == preference
        assert f"## {copy.summary_heading}" in text
        assert "OpenAI launched GPT-5, describing stronger reasoning" not in generated
        assert "https://openai.com/index/gpt-5" in text
        assert copy.combined_research_for.split("{")[0].strip() in text
