from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingsProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str, model: str | None = None) -> list[float]: ...

    @property
    @abstractmethod
    def dimension(self) -> int: ...
