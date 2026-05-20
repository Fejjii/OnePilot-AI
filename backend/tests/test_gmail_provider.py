"""Gmail provider, schemas, and approval-gated execution tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError as PydanticValidationError

from onepilot.core.config import Settings
from onepilot.core.constants import ApprovalStatus, PlanCode, Role
from onepilot.core.ids import new_id
from onepilot.providers import get_email_provider, reset_provider_cache
from onepilot.providers.email.gmail_auth import GoogleOAuthClient
from onepilot.providers.email.gmail_provider import GmailProvider
from onepilot.providers.email.mock_email_provider import MockEmailProvider
from onepilot.repositories.models import Organization, Subscription
from onepilot.schemas.gmail import EmailDraftRequest, EmailSendRequest
from onepilot.security.auth import Principal
from onepilot.services import approval_service, gmail_service


@pytest.fixture(autouse=True)
def _reset_email_provider() -> None:
    reset_provider_cache()
    yield
    reset_provider_cache()


class TestGmailSchemas:
    def test_invalid_email_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            EmailDraftRequest(to=["not-an-email"], subject="Hi", body="Body")

    def test_empty_subject_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            EmailDraftRequest(to=["a@example.com"], subject="", body="Body")

    def test_empty_body_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            EmailDraftRequest(to=["a@example.com"], subject="Hi", body="")

    def test_too_many_recipients_rejected(self) -> None:
        emails = [f"user{i}@example.com" for i in range(11)]
        with pytest.raises(PydanticValidationError):
            EmailDraftRequest(to=emails, subject="Hi", body="Body")

    def test_send_request_valid(self) -> None:
        req = EmailSendRequest(to=["lead@acme.io"], subject="Hello", body="Thanks")
        assert req.to == ["lead@acme.io"]


class TestGmailProviderSelection:
    def test_missing_credentials_returns_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_REFRESH_TOKEN", raising=False)
        settings = Settings(
            GOOGLE_CLIENT_ID="",
            GOOGLE_CLIENT_SECRET="",
            GOOGLE_REFRESH_TOKEN="",
            GMAIL_PROVIDER_MODE="auto",
        )
        provider = get_email_provider(settings)
        assert isinstance(provider, MockEmailProvider)

    def test_mock_mode_explicit(self) -> None:
        settings = Settings(
            GOOGLE_CLIENT_ID="id",
            GOOGLE_CLIENT_SECRET="secret",
            GOOGLE_REFRESH_TOKEN="refresh",
            GMAIL_PROVIDER_MODE="mock",
        )
        provider = get_email_provider(settings)
        assert isinstance(provider, MockEmailProvider)

    def test_live_mode_when_oauth_configured(self) -> None:
        settings = Settings(
            GOOGLE_CLIENT_ID="client-id",
            GOOGLE_CLIENT_SECRET="client-secret",
            GOOGLE_REFRESH_TOKEN="refresh-token",
            GMAIL_PROVIDER_MODE="auto",
        )
        provider = get_email_provider(settings)
        assert isinstance(provider, GmailProvider)

    def test_mock_create_draft_succeeds(self) -> None:
        provider = MockEmailProvider()
        result = provider.create_draft(
            to="bob@example.com",
            subject="Meeting",
            body="Let's meet",
        )
        assert result["status"] == "success"
        assert result.get("draft_id") or result.get("id")
        assert "access_token" not in str(result)
        assert "refresh_token" not in str(result)


class TestGmailOAuth:
    def test_token_refresh_mocked(self) -> None:
        client = GoogleOAuthClient(
            client_id="cid",
            client_secret="csecret",
            refresh_token="rtoken",
        )
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "ya29.test-access",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client
            token = client.get_access_token()
        assert token == "ya29.test-access"
        assert "rtoken" not in token


class TestGmailApprovalExecution:
    def _principal(self, session) -> Principal:
        org_id = new_id("org")
        session.add(Organization(id=org_id, name="GmailOrg", slug=f"gmail-{org_id[:8]}"))
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
            user_id="usr_gmail",
            organization_id=org_id,
            role=Role.OWNER,
            plan_code=PlanCode.FREE,
        )

    def test_gmail_not_executed_before_approval(self, db_session) -> None:
        principal = self._principal(db_session)
        apv = approval_service.create(
            db_session,
            principal=principal,
            action_type="gmail_create_draft",
            title="Draft email",
            proposed_payload={
                "to": ["lead@example.com"],
                "subject": "Hello",
                "body": "Body text",
            },
        )
        assert apv.status == ApprovalStatus.PENDING.value
        provider = MockEmailProvider()
        assert len(provider.list_drafts()) == 0

    def test_approving_executes_mock_draft(self, db_session) -> None:
        principal = self._principal(db_session)
        apv = approval_service.create(
            db_session,
            principal=principal,
            action_type="gmail_create_draft",
            title="Draft email",
            proposed_payload={
                "to": ["lead@example.com"],
                "subject": "NovaEdge services",
                "body": "Automation overview",
            },
        )
        decided = approval_service.decide(
            db_session,
            principal=principal,
            approval_id=apv.id,
            status=ApprovalStatus.APPROVED,
        )
        execution = decided.proposed_payload.get("_execution", {})
        assert execution.get("status") == "success"
        assert execution.get("draft_id")

    def test_rejecting_does_not_execute(self, db_session) -> None:
        principal = self._principal(db_session)
        apv = approval_service.create(
            db_session,
            principal=principal,
            action_type="gmail_create_draft",
            title="Draft email",
            proposed_payload={
                "to": ["lead@example.com"],
                "subject": "Hi",
                "body": "No send",
            },
        )
        approval_service.decide(
            db_session,
            principal=principal,
            approval_id=apv.id,
            status=ApprovalStatus.REJECTED,
        )
        assert "_execution" not in (apv.proposed_payload or {})


class TestGmailRouting:
    def test_infer_send_from_message(self) -> None:
        assert gmail_service.infer_email_action(
            "Draft and send an email to a lead about NovaEdge",
            {},
        ) == "send"

    def test_infer_draft_only(self) -> None:
        assert gmail_service.infer_email_action(
            "Draft an email to a lead about NovaEdge automation services",
            {},
        ) == "draft_only"
