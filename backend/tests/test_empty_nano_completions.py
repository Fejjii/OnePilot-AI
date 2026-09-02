"""Regression tests for empty gpt-5-nano completions (OP-023).

Nano can spend max_completion_tokens on hidden reasoning and return empty
message.content. RAG must stay grounded; email drafts must never 422.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import PlanCode, Role
from onepilot.providers.llm.base import LLMResponse
from onepilot.repositories.models import DocumentChunk
from onepilot.schemas.gmail import EmailApprovalPayload
from onepilot.security.auth import Principal
from onepilot.services import email_service, gmail_service, rag_service
from onepilot.services.rag_service import WEAK_EVIDENCE_ANSWER, SearchHit, SearchOutcome


class _EmptyNanoLLM:
    """Live-shaped provider that returns Nano's empty completion."""

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        return LLMResponse(
            content="",
            model="gpt-5-nano-2025-08-07",
            input_tokens=80,
            output_tokens=512,
            finish_reason="length",
        )


class _FixedLLM:
    def __init__(self, content: str, model: str = "gpt-5-nano-2025-08-07") -> None:
        self._content = content
        self._model = model

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        return LLMResponse(
            content=self._content,
            model=self._model,
            input_tokens=40,
            output_tokens=64,
            finish_reason="stop",
        )


def _principal() -> Principal:
    return Principal(
        user_id="usr_nano",
        organization_id="org_nano",
        role=Role.OWNER,
        plan_code=PlanCode.BUSINESS,
    )


def _escalation_hit() -> SearchHit:
    chunk = DocumentChunk(
        id="chunk_escalation",
        organization_id="org_nano",
        document_id="doc_escalation",
        ordinal=0,
        section="Escalation Policy",
        content=(
            "P1 incidents must be acknowledged within 15 minutes. "
            "Escalate to the on-call manager after 30 minutes without a response. "
            "Customer-facing outages require a status update every 30 minutes."
        ),
        token_count=48,
    )
    return SearchHit(
        chunk=chunk,
        score=1.0,
        document_title="Escalation Policy",
        vector_score=1.0,
        signals={"title": 0.95, "keyword": 0.8},
    )


def _strong_search() -> SearchOutcome:
    return SearchOutcome(
        query="What does our knowledge base say about the escalation policy?",
        hits=[_escalation_hit()],
        weak_evidence=False,
        fallback_used=False,
    )


def _register(client: TestClient, *, suffix: str) -> str:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"nano{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Nano User",
            "organization_name": f"NanoOrg{suffix}",
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


class TestRagEmptyNanoCompletion:
    def test_strong_evidence_empty_model_output_is_grounded(
        self, db_session: Session
    ) -> None:
        query = "What does our knowledge base say about the escalation policy?"
        with patch(
            "onepilot.services.rag_service.search", return_value=_strong_search()
        ):
            outcome = rag_service.answer(
                db_session,
                principal=_principal(),
                query=query,
                settings=Settings(),
                llm=_EmptyNanoLLM(),  # type: ignore[arg-type]
            )

        assert outcome.weak_evidence is False
        assert outcome.hits
        assert outcome.hits[0].document_title == "Escalation Policy"
        assert outcome.answer
        assert outcome.answer != WEAK_EVIDENCE_ANSWER
        assert "forwarding this to a human teammate" not in outcome.answer.lower()
        assert "Escalation Policy" in outcome.answer
        assert "15 minutes" in outcome.answer or "on-call" in outcome.answer.lower()

    def test_non_empty_completion_is_used_as_answer(
        self, db_session: Session
    ) -> None:
        grounded = (
            "## Summary\nP1 incidents are acknowledged in 15 minutes [Escalation Policy]."
        )
        with patch(
            "onepilot.services.rag_service.search", return_value=_strong_search()
        ):
            outcome = rag_service.answer(
                db_session,
                principal=_principal(),
                query="escalation policy",
                settings=Settings(),
                llm=_FixedLLM(grounded),  # type: ignore[arg-type]
            )

        assert outcome.weak_evidence is False
        assert outcome.answer == grounded
        assert outcome.model == "gpt-5-nano-2025-08-07"


class TestEmailEmptyNanoCompletion:
    def test_empty_model_output_yields_non_empty_draft(
        self, db_session: Session
    ) -> None:
        context = (
            "Draft a follow-up email to our most promising lead about "
            "scheduling an intro call."
        )
        outcome = email_service.draft_email(
            db_session,
            principal=_principal(),
            context=context,
            recipient_name="Alex Rivera",
            recipient_email="alex@example.com",
            settings=Settings(),
            llm=_EmptyNanoLLM(),  # type: ignore[arg-type]
            enforce_quota=False,
        )

        assert outcome.draft.body.strip()
        assert outcome.draft.subject.strip()
        payload = gmail_service.build_approval_payload(
            subject=outcome.draft.subject,
            body=outcome.draft.body,
            recipient_email="alex@example.com",
            recipient_name="Alex Rivera",
            tone=outcome.draft.tone,
        )
        parsed = EmailApprovalPayload.model_validate(payload)
        assert len(parsed.body) >= 1
        assert parsed.subject
        assert outcome.draft.approval_required is True

    def test_non_empty_completion_is_parsed(
        self, db_session: Session
    ) -> None:
        content = (
            "Subject: Intro call with NovaEdge\n\n"
            "Hi Alex,\n\nWould next Tuesday work for a 20-minute intro call?\n\n"
            "Best regards,\nThe NovaEdge team"
        )
        outcome = email_service.draft_email(
            db_session,
            principal=_principal(),
            context="Draft a follow-up email about scheduling an intro call.",
            recipient_name="Alex",
            settings=Settings(),
            llm=_FixedLLM(content),  # type: ignore[arg-type]
            enforce_quota=False,
        )
        assert outcome.draft.subject == "Intro call with NovaEdge"
        assert "next Tuesday" in outcome.draft.body
        assert outcome.draft.approval_required is True


class TestEmailDraftChatEmptyNano:
    def test_starter_prompt_returns_200_with_approval(
        self, client: TestClient
    ) -> None:
        token = _register(client, suffix="_email_empty")
        empty = _EmptyNanoLLM()
        with patch(
            "onepilot.services.email_service.get_llm_provider", return_value=empty
        ):
            resp = client.post(
                "/chat",
                json={
                    "message": (
                        "Draft a follow-up email to our most promising lead "
                        "about scheduling an intro call."
                    )
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["approval_required"] is True
        assert body["approval_id"]
        assert body["final_response"]
        assert "Invalid email approval payload" not in (body["final_response"] or "")
