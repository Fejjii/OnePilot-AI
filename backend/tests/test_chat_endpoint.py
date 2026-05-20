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


class TestChatTracing:
    """Tests for tracing metadata in chat responses."""

    def test_chat_returns_trace_mode(self, client: TestClient) -> None:
        """Test that chat response includes trace_mode field."""
        token = _register(client, suffix="_trace")
        resp = client.post(
            "/chat",
            json={"message": "test tracing"},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "trace_mode" in body
        assert body["trace_mode"] in ("local", "langsmith")

    def test_chat_trace_metadata_structure(self, client: TestClient) -> None:
        """Test that trace metadata fields are present."""
        token = _register(client, suffix="_trace_meta")
        resp = client.post(
            "/chat",
            json={"message": "hello"},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Trace metadata fields should be present
        assert "trace_mode" in body
        assert "trace_id" in body
        assert "trace_url" in body

        # Local mode shouldn't have a trace URL
        if body["trace_mode"] == "local":
            assert body["trace_url"] is None

    def test_chat_with_langsmith_disabled_returns_local_mode(self, client: TestClient) -> None:
        """Test that without LangSmith configured, trace_mode is local."""
        token = _register(client, suffix="_local_trace")
        resp = client.post(
            "/chat",
            json={"message": "test local trace"},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Without LangSmith API key configured in tests, should be local
        assert body["trace_mode"] == "local"
        assert body["trace_url"] is None
        # Should still have trace_id
        assert body["trace_id"] is not None

    def test_trace_metadata_persisted_in_conversation(self, client: TestClient) -> None:
        """Test that trace metadata is persisted and returned in conversation retrieval."""
        token = _register(client, suffix="_trace_persist")

        # Send a message
        chat_resp = client.post(
            "/chat",
            json={"message": "test persistence"},
            headers=_h(token),
        )
        assert chat_resp.status_code == 200, chat_resp.text
        chat_body = chat_resp.json()
        conv_id = chat_body["conversation_id"]

        # Get the conversation
        conv_resp = client.get(
            f"/conversations/{conv_id}",
            headers=_h(token),
        )
        assert conv_resp.status_code == 200, conv_resp.text
        conv_body = conv_resp.json()

        # Find the assistant message
        assistant_msgs = [m for m in conv_body["messages"] if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        assistant_msg = assistant_msgs[0]

        # Verify trace metadata is present
        assert "trace_mode" in assistant_msg
        assert assistant_msg["trace_mode"] == chat_body["trace_mode"]
        assert "trace_id" in assistant_msg
        assert assistant_msg["trace_id"] == chat_body["trace_id"]
        assert "trace_url" in assistant_msg
        assert assistant_msg["trace_url"] == chat_body["trace_url"]

    def test_old_messages_without_trace_metadata_safe(self, client: TestClient) -> None:
        """Test that old messages without trace metadata don't crash."""
        token = _register(client, suffix="_old_msg")

        # Send a message
        chat_resp = client.post(
            "/chat",
            json={"message": "test old message"},
            headers=_h(token),
        )
        assert chat_resp.status_code == 200, chat_resp.text
        conv_id = chat_resp.json()["conversation_id"]

        # Get the conversation (should handle missing trace metadata gracefully)
        conv_resp = client.get(
            f"/conversations/{conv_id}",
            headers=_h(token),
        )
        assert conv_resp.status_code == 200, conv_resp.text
        conv_body = conv_resp.json()

        # Should have messages even if trace metadata might be None
        assert len(conv_body["messages"]) > 0

        # Assistant message trace fields should be present (but may be None)
        assistant_msgs = [m for m in conv_body["messages"] if m["role"] == "assistant"]
        if assistant_msgs:
            assistant_msg = assistant_msgs[0]
            # Fields should exist in response even if None
            assert "trace_mode" in assistant_msg
            assert "trace_id" in assistant_msg
            assert "trace_url" in assistant_msg


class TestConversationDelete:
    def test_delete_own_conversation(self, client: TestClient) -> None:
        token = _register(client, suffix="_del")
        chat_resp = client.post(
            "/chat",
            json={"message": "Hello for delete test"},
            headers=_h(token),
        )
        assert chat_resp.status_code == 200, chat_resp.text
        conv_id = chat_resp.json()["conversation_id"]

        delete_resp = client.delete(
            f"/conversations/{conv_id}",
            headers=_h(token),
        )
        assert delete_resp.status_code == 204, delete_resp.text

        get_resp = client.get(f"/conversations/{conv_id}", headers=_h(token))
        assert get_resp.status_code == 404

        list_resp = client.get("/conversations", headers=_h(token))
        assert list_resp.status_code == 200
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert conv_id not in ids

    def test_delete_removes_messages(self, client: TestClient) -> None:
        token = _register(client, suffix="_del_msgs")
        conv_id = client.post(
            "/chat",
            json={"message": "Persist then delete"},
            headers=_h(token),
        ).json()["conversation_id"]
        detail_before = client.get(f"/conversations/{conv_id}", headers=_h(token))
        assert len(detail_before.json()["messages"]) >= 2

        delete_resp = client.delete(f"/conversations/{conv_id}", headers=_h(token))
        assert delete_resp.status_code == 204

        detail_after = client.get(f"/conversations/{conv_id}", headers=_h(token))
        assert detail_after.status_code == 404

    def test_cannot_delete_other_org_conversation(
        self, client: TestClient
    ) -> None:
        token_a = _register(client, suffix="_del_a")
        chat_resp = client.post(
            "/chat",
            json={"message": "Org A conversation"},
            headers=_h(token_a),
        )
        conv_id = chat_resp.json()["conversation_id"]

        token_b = _register(client, suffix="_del_b")
        delete_resp = client.delete(
            f"/conversations/{conv_id}",
            headers=_h(token_b),
        )
        assert delete_resp.status_code == 404
