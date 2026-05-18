from __future__ import annotations

from openai import OpenAI

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.embeddings.base import EmbeddingsProvider


OPENAI_EMBEDDINGS_IMPLEMENTED = True


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    """OpenAI text-embedding-backed embeddings provider."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "text-embedding-3-small",
        dim: int = 1536,
    ) -> None:
        if not api_key:
            raise ProviderUnavailableError("OpenAI API key not configured")
        self._api_key = api_key
        self._default_model = default_model
        self._dimension = dim
        self._client = OpenAI(api_key=api_key)

    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def model(self) -> str:
        return self._default_model

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of text strings to embed
            model: Model to use (defaults to configured model)
            
        Returns:
            List of embedding vectors
            
        Raises:
            ProviderUnavailableError: If API call fails
        """
        if not texts:
            return []
        
        try:
            response = self._client.embeddings.create(
                model=model or self._default_model,
                input=texts,
                dimensions=self._dimension,
            )
            
            # Sort by index to maintain order
            embeddings = sorted(response.data, key=lambda e: e.index)
            return [e.embedding for e in embeddings]
        except Exception as exc:
            raise ProviderUnavailableError(f"OpenAI embeddings API call failed: {exc}") from exc

    def embed_query(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding for a single query text.
        
        Args:
            text: Text string to embed
            model: Model to use (defaults to configured model)
            
        Returns:
            Embedding vector
            
        Raises:
            ProviderUnavailableError: If API call fails
        """
        results = self.embed([text], model=model)
        return results[0] if results else []
