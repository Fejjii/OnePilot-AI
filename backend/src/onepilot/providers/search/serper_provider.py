from __future__ import annotations

import os

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.search.base import SearchProvider


class SerperSearchProvider(SearchProvider):
    """Serper.dev-backed web search provider."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("SERPER_API_KEY", "")
        if not self._api_key:
            raise ProviderUnavailableError("Serper API key not configured")

    def search_web(self, query: str, num_results: int = 5) -> list[dict]:
        raise NotImplementedError("Serper search_web not yet implemented")
