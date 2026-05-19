"""Tests for safe runtime model configuration endpoint."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

_SECRET_PATTERN = re.compile(
    r"(sk-[a-zA-Z0-9]{10,}|api[_-]?key|secret|password|token\s*[:=])",
    re.IGNORECASE,
)


def test_runtime_config_returns_model_names(client: TestClient) -> None:
    response = client.get("/runtime/config")
    assert response.status_code == 200

    data = response.json()
    assert data["chat_model"] == "gpt-4o-mini"
    assert data["embedding_model"] == "text-embedding-3-small"
    assert data["speech_model"] == "whisper-1"
    assert data["configuration_source"] == "environment"
    assert "cost_note" in data
    assert len(data["cost_note"]) > 0


def test_runtime_config_status_without_openai_key(client: TestClient) -> None:
    """Test env defaults: no OpenAI key in test conftest."""
    response = client.get("/runtime/config")
    assert response.status_code == 200

    data = response.json()
    assert data["llm_status"] == "missing"
    assert data["embeddings_status"] == "missing"
    assert data["speech_status"] == "missing"
    assert data["fallback_active"] is True
    assert data["provider_mode"] in {"demo", "mixed", "live"}


def test_runtime_config_does_not_expose_secrets(client: TestClient) -> None:
    response = client.get("/runtime/config")
    assert response.status_code == 200

    payload = response.text
    assert "OPENAI_API_KEY" not in payload
    assert _SECRET_PATTERN.search(payload) is None

    allowed_keys = {
        "chat_model",
        "embedding_model",
        "speech_model",
        "llm_status",
        "embeddings_status",
        "speech_status",
        "fallback_active",
        "provider_mode",
        "cost_note",
        "configuration_source",
    }
    assert set(response.json().keys()) == allowed_keys
