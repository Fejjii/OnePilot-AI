"""Tests for speech transcription endpoint."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from onepilot.providers.speech.openai_speech import OpenAISpeechProvider
from onepilot.providers.speech.base import TranscriptionResponse


def _register(client: TestClient, *, suffix: str) -> str:
    """Helper to register a test user and return token."""
    resp = client.post(
        "/auth/register",
        json={
            "email": f"speech{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Speech User",
            "organization_name": f"SpeechOrg{suffix}",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    """Helper to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}


class TestSpeechTranscription:
    """Tests for POST /speech/transcribe endpoint."""
    
    def test_unauthenticated_request_rejected(self, client: TestClient) -> None:
        """Unauthenticated requests should be rejected."""
        audio_data = b"fake audio data"
        files = {"audio": ("test.webm", BytesIO(audio_data), "audio/webm")}
        
        resp = client.post("/speech/transcribe", files=files)
        
        assert resp.status_code == 401
    
    def test_unsupported_mime_type_rejected(self, client: TestClient) -> None:
        """Unsupported MIME types should be rejected."""
        token = _register(client, suffix="_mime")
        audio_data = b"fake audio data"
        files = {"audio": ("test.txt", BytesIO(audio_data), "text/plain")}
        
        resp = client.post("/speech/transcribe", files=files, headers=_h(token))
        
        assert resp.status_code == 422
        body = resp.json()
        assert "Unsupported audio format" in body["message"]
    
    def test_file_too_large_rejected(self, client: TestClient) -> None:
        """Files larger than 25MB should be rejected."""
        token = _register(client, suffix="_large")
        # Create a 26MB fake audio file
        audio_data = b"x" * (26 * 1024 * 1024)
        files = {"audio": ("test.webm", BytesIO(audio_data), "audio/webm")}
        
        resp = client.post("/speech/transcribe", files=files, headers=_h(token))
        
        assert resp.status_code == 422
        body = resp.json()
        assert "too large" in body["message"]
    
    @patch.dict("os.environ", {}, clear=True)
    def test_openai_missing_returns_error(self, client: TestClient) -> None:
        """Should return error when OpenAI is not configured."""
        token = _register(client, suffix="_nokey")
        audio_data = b"fake audio data"
        files = {"audio": ("test.webm", BytesIO(audio_data), "audio/webm")}
        
        resp = client.post("/speech/transcribe", files=files, headers=_h(token))
        
        assert resp.status_code == 503
        body = resp.json()
        assert "requires OpenAI configuration" in body["message"]
