from __future__ import annotations

import pytest

from onepilot.core.config import Settings
from onepilot.providers import get_embeddings_provider, get_llm_provider
from onepilot.providers.crm.mock_hubspot_provider import MockHubSpotProvider
from onepilot.providers.email.mock_email_provider import MockEmailProvider
from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
from onepilot.providers.llm.base import LLMResponse
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.providers.vector.memory_vector_provider import MemoryVectorProvider


class TestFallbackLLMProvider:
    def test_chat_returns_llm_response(self) -> None:
        provider = FallbackLLMProvider()
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.chat(messages)
        assert isinstance(result, LLMResponse)
        assert result.content
        assert result.finish_reason == "stop"
        assert provider.call_count == 1


class TestFallbackEmbeddingsProvider:
    def test_embed_returns_correct_dimensions(self) -> None:
        provider = FallbackEmbeddingsProvider()
        vectors = provider.embed(["hello", "world"])
        assert len(vectors) == 2
        assert all(len(v) == provider.dimension for v in vectors)
        assert all(isinstance(x, float) for v in vectors for x in v)


class TestProviderSelection:
    def test_openai_providers_used_when_key_exists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that OpenAI providers are used when API key is configured."""
        from unittest.mock import patch
        from onepilot.providers.embeddings.openai_embeddings import OpenAIEmbeddingsProvider
        from onepilot.providers.llm.openai_provider import OpenAILLMProvider
        from onepilot.providers import reset_provider_cache
        
        reset_provider_cache()
        
        # Mock OpenAI client to avoid actual API calls
        with patch("onepilot.providers.llm.openai_provider.OpenAI"), \
             patch("onepilot.providers.embeddings.openai_embeddings.OpenAI"):
            monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
            settings = Settings(OPENAI_API_KEY="sk-test-openai-key")

            embeddings = get_embeddings_provider(settings)
            llm = get_llm_provider(settings)

            # OpenAI providers should be used when key exists and mocked
            assert isinstance(embeddings, OpenAIEmbeddingsProvider)
            assert isinstance(llm, OpenAILLMProvider)
            
            # Verify they're not fallback providers
            assert not isinstance(embeddings, FallbackEmbeddingsProvider)
            assert not isinstance(llm, FallbackLLMProvider)
        
        reset_provider_cache()
    
    def test_fallback_providers_used_when_no_key(self) -> None:
        """Test that fallback providers are used when API key is missing."""
        from onepilot.providers import reset_provider_cache
        
        reset_provider_cache()
        
        settings = Settings(OPENAI_API_KEY="")
        
        embeddings = get_embeddings_provider(settings)
        llm = get_llm_provider(settings)
        
        # Fallback providers should be used when no key
        assert isinstance(embeddings, FallbackEmbeddingsProvider)
        assert isinstance(llm, FallbackLLMProvider)
        
        reset_provider_cache()


class TestMemoryVectorProvider:
    def test_upsert_and_search(self) -> None:
        provider = MemoryVectorProvider()
        provider.ensure_collection("test", dimension=3)

        provider.upsert(
            collection="test",
            ids=["a", "b"],
            vectors=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            payloads=[{"label": "x"}, {"label": "y"}],
        )
        results = provider.search("test", vector=[1.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0].id == "a"
        assert results[0].payload["label"] == "x"
        assert results[0].score > 0.9


class TestMockHubSpotProvider:
    def test_create_and_retrieve_note(self) -> None:
        provider = MockHubSpotProvider()
        note = provider.create_lead_note("lead_001", "Follow up next week")
        assert "id" in note
        assert note["text"] == "Follow up next week"

        lead = provider.get_lead("lead_001")
        assert lead is not None
        assert any(n["text"] == "Follow up next week" for n in lead["notes"])


class TestMockEmailProvider:
    def test_create_draft(self) -> None:
        provider = MockEmailProvider()
        draft = provider.create_draft(
            to="bob@example.com",
            subject="Meeting",
            body="Let's meet at 3pm",
        )
        assert "id" in draft
        assert draft["subject"] == "Meeting"
        assert draft["body"] == "Let's meet at 3pm"
        assert draft["status"] == "draft"
