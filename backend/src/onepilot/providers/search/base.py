from __future__ import annotations

from abc import ABC, abstractmethod


class SearchProvider(ABC):
    @abstractmethod
    def search_web(
        self,
        query: str,
        num_results: int = 5,
        *,
        language: str | None = None,
        region: str | None = None,
    ) -> list[dict]: ...
