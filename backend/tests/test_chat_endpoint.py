"""Tests for the /chat endpoint and conversation persistence."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, *, suffix: str) -> str:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"chat{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Chat User",
            "organization_name": f"ChatOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestChatBasic:
    def test_chat_returns_conversation_and_intent(self, client: TestClient) -> None:
        token = _register(client, suffix="_basic")
        resp = client.post(
            "/chat",
            json={"message": "Hey there, how's your day?"},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["conversation_id"].startswith("conv_")
        assert body["message_id"].startswith("msg_")
        assert body["intent"] == "general_assistant"
        assert body["final_response"]
        assert body["approval_required"] is False
        assert any(s["step"] == "classify_intent" for s in body["trace_steps"])

    def test_chat_persists_messages_across_turns(self, client: TestClient) -> None:
        token = _register(client, suffix="_multi")
        first = client.post(
            "/chat",
            json={"message": "Hello!"},
            headers=_h(token),
        ).json()
        conv_id = first["conversation_id"]

        second = client.post(
            "/chat",
            json={"message": "Thanks for the welcome.", "conversation_id": conv_id},
            headers=_h(token),
        )
        assert second.status_code == 200, second.text
        assert second.json()["conversation_id"] == conv_id

        detail = client.get(
            f"/conversations/{conv_id}", headers=_h(token)
        )
        assert detail.status_code == 200, detail.text
        messages = detail.json()["messages"]
        # Two user turns + two assistant turns.
        assert len(messages) == 4
        roles = [m["role"] for m in messages]
        assert roles == ["user", "assistant", "user", "assistant"]

    def test_chat_blocks_out_of_scope(self, client: TestClient) -> None:
        token = _register(client, suffix="_oos")
        resp = client.post(
            "/chat",
            json={"message": "Tell me a joke about programming."},
            headers=_h(token),
        )
        body = resp.json()
        assert body["intent"] == "out_of_scope"
        assert "out_of_scope" in body["safety_flags"]

    def test_chat_creates_approval_for_send_email(self, client: TestClient) -> None:
        token = _register(client, suffix="_send")
        resp = client.post(
            "/chat",
            json={
                "message": "Draft and send an email to Bob about the pricing update.",
                "context": {"action": "send"},
            },
            headers=_h(token),
        )
        body = resp.json()
        assert body["intent"] == "email_drafting"
        assert body["approval_required"] is True
        assert body["approval_id"] and body["approval_id"].startswith("apv_")

    def test_unknown_conversation_id_returns_404(self, client: TestClient) -> None:
        token = _register(client, suffix="_404")
        resp = client.post(
            "/chat",
            json={"message": "hi there!", "conversation_id": "conv_does_not_exist"},
            headers=_h(token),
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "NOT_FOUND"


class TestConversationListing:
    def test_list_conversations_paginates(self, client: TestClient) -> None:
        token = _register(client, suffix="_list")
        for i in range(3):
            client.post(
                "/chat",
                json={"message": f"Hello message {i}"},
                headers=_h(token),
            )
        resp = client.get("/conversations", headers=_h(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 3
        assert len(body["items"]) >= 3


class TestQuotaEnforcement:
    def test_chat_messages_count_against_quota(self, client: TestClient) -> None:
        token = _register(client, suffix="_quota")
        client.post("/chat", json={"message": "hi please"}, headers=_h(token))
        usage = client.get("/usage/summary", headers=_h(token)).json()
        chat_quota = next(q for q in usage["quotas"] if q["feature"] == "chat_messages")
        assert chat_quota["used"] >= 1
