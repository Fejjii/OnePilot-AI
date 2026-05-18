"""Tests for OpenAI provider selection and API calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from onepilot.core.config import Settings
from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers import get_embeddings_provider, get_llm_provider, reset_provider_cache
from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
from onepilot.providers.embeddings.openai_embeddings import OpenAIEmbeddingsProvider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.providers.llm.openai_provider import OpenAILLMProvider


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset provider cache before each test."""
    reset_provider_cache()
    yield
    reset_provider_cache()


class TestOpenAILLMProvider:
    """Test OpenAI LLM provider with mocked API."""
    
    def test_chat_calls_openai_api(self):
        """Test that chat method calls OpenAI API with correct parameters."""
        with patch("onepilot.providers.llm.openai_provider.OpenAI") as mock_openai_cls:
            # Setup mock
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.model = "gpt-4o-mini"
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            
            mock_client.chat.completions.create.return_value = mock_response
            
            # Create provider and call
            provider = OpenAILLMProvider(api_key="test-key", default_model="gpt-4o-mini")
            result = provider.chat(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7,
                max_tokens=100,
            )
            
            # Verify API was called correctly
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["max_tokens"] == 100
            
            # Verify response
            assert result.content == "Test response"
            assert result.model == "gpt-4o-mini"
            assert result.input_tokens == 10
            assert result.output_tokens == 20
    
    def test_chat_raises_on_api_error(self):
        """Test that API errors are wrapped in ProviderUnavailableError."""
        with patch("onepilot.providers.llm.openai_provider.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            
            provider = OpenAILLMProvider(api_key="test-key")
            
            with pytest.raises(ProviderUnavailableError, match="API Error"):
                provider.chat([{"role": "user", "content": "Hello"}])
    
    def test_chat_structured_uses_json_mode(self):
        """Test that structured chat uses JSON response format."""
        with patch("onepilot.providers.llm.openai_provider.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.model = "gpt-4o-mini"
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"result": "success"}'
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            
            mock_client.chat.completions.create.return_value = mock_response
            
            provider = OpenAILLMProvider(api_key="test-key")
            result = provider.chat_structured(
                messages=[{"role": "user", "content": "Hello"}],
                response_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            )
            
            # Verify JSON mode was used
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["response_format"] == {"type": "json_object"}
            assert result.content == '{"result": "success"}'


class TestOpenAIEmbeddingsProvider:
    """Test OpenAI embeddings provider with mocked API."""
    
    def test_embed_calls_openai_api(self):
        """Test that embed method calls OpenAI API with correct parameters."""
        with patch("onepilot.providers.embeddings.openai_embeddings.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            
            # Setup mock response
            mock_response = MagicMock()
            mock_data1 = MagicMock()
            mock_data1.index = 0
            mock_data1.embedding = [0.1, 0.2, 0.3]
            mock_data2 = MagicMock()
            mock_data2.index = 1
            mock_data2.embedding = [0.4, 0.5, 0.6]
            mock_response.data = [mock_data1, mock_data2]
            
            mock_client.embeddings.create.return_value = mock_response
            
            # Create provider and call
            provider = OpenAIEmbeddingsProvider(
                api_key="test-key",
                default_model="text-embedding-3-small",
                dim=1536,
            )
            result = provider.embed(["text1", "text2"])
            
            # Verify API was called correctly
            mock_client.embeddings.create.assert_called_once()
            call_kwargs = mock_client.embeddings.create.call_args[1]
            assert call_kwargs["model"] == "text-embedding-3-small"
            assert call_kwargs["input"] == ["text1", "text2"]
            assert call_kwargs["dimensions"] == 1536
            
            # Verify response
            assert len(result) == 2
            assert result[0] == [0.1, 0.2, 0.3]
            assert result[1] == [0.4, 0.5, 0.6]
    
    def test_embed_query_calls_embed(self):
        """Test that embed_query wraps embed for single text."""
        with patch("onepilot.providers.embeddings.openai_embeddings.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            
            mock_response = MagicMock()
            mock_data = MagicMock()
            mock_data.index = 0
            mock_data.embedding = [0.1, 0.2, 0.3]
            mock_response.data = [mock_data]
            
            mock_client.embeddings.create.return_value = mock_response
            
            provider = OpenAIEmbeddingsProvider(api_key="test-key")
            result = provider.embed_query("single text")
            
            # Verify single text was wrapped in list
            call_kwargs = mock_client.embeddings.create.call_args[1]
            assert call_kwargs["input"] == ["single text"]
            assert result == [0.1, 0.2, 0.3]
    
    def test_embed_raises_on_api_error(self):
        """Test that API errors are wrapped in ProviderUnavailableError."""
        with patch("onepilot.providers.embeddings.openai_embeddings.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.embeddings.create.side_effect = Exception("API Error")
            
            provider = OpenAIEmbeddingsProvider(api_key="test-key")
            
            with pytest.raises(ProviderUnavailableError, match="API Error"):
                provider.embed(["text"])


class TestProviderSelection:
    """Test provider selection logic based on configuration."""
    
    def test_llm_uses_openai_when_key_exists(self):
        """Test that OpenAI LLM is used when API key is configured."""
        with patch("onepilot.providers.llm.openai_provider.OpenAI"):
            settings = Settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="gpt-4o-mini")
            provider = get_llm_provider(settings)
            assert isinstance(provider, OpenAILLMProvider)
            assert not isinstance(provider, FallbackLLMProvider)
    
    def test_llm_uses_fallback_when_no_key(self):
        """Test that fallback LLM is used when API key is missing."""
        settings = Settings(OPENAI_API_KEY="")
        provider = get_llm_provider(settings)
        assert isinstance(provider, FallbackLLMProvider)
    
    def test_llm_uses_fallback_on_initialization_error(self):
        """Test that fallback is used if OpenAI initialization fails."""
        with patch("onepilot.providers.llm.openai_provider.OpenAI") as mock_openai_cls:
            mock_openai_cls.side_effect = Exception("Connection error")
            
            settings = Settings(OPENAI_API_KEY="test-key")
            provider = get_llm_provider(settings)
            assert isinstance(provider, FallbackLLMProvider)
    
    def test_embeddings_uses_openai_when_key_exists(self):
        """Test that OpenAI embeddings are used when API key is configured."""
        with patch("onepilot.providers.embeddings.openai_embeddings.OpenAI"):
            settings = Settings(
                OPENAI_API_KEY="test-key",
                OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
            )
            provider = get_embeddings_provider(settings)
            assert isinstance(provider, OpenAIEmbeddingsProvider)
            assert not isinstance(provider, FallbackEmbeddingsProvider)
    
    def test_embeddings_uses_fallback_when_no_key(self):
        """Test that fallback embeddings are used when API key is missing."""
        settings = Settings(OPENAI_API_KEY="")
        provider = get_embeddings_provider(settings)
        assert isinstance(provider, FallbackEmbeddingsProvider)
    
    def test_embeddings_uses_fallback_on_initialization_error(self):
        """Test that fallback is used if OpenAI embeddings initialization fails."""
        with patch("onepilot.providers.embeddings.openai_embeddings.OpenAI") as mock_openai_cls:
            mock_openai_cls.side_effect = Exception("Connection error")
            
            settings = Settings(OPENAI_API_KEY="test-key")
            provider = get_embeddings_provider(settings)
            assert isinstance(provider, FallbackEmbeddingsProvider)
    
    def test_provider_caching(self):
        """Test that providers are cached across calls."""
        with patch("onepilot.providers.llm.openai_provider.OpenAI"):
            settings = Settings(OPENAI_API_KEY="test-key")
            provider1 = get_llm_provider(settings)
            provider2 = get_llm_provider(settings)
            assert provider1 is provider2  # Same instance
