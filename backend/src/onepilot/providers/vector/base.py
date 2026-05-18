from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VectorSearchResult:
    id: str
    score: float
    payload: dict


class VectorProvider(ABC):
    @abstractmethod
    def upsert(
        self,
        collection: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> int: ...

    @abstractmethod
    def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]: ...

    @abstractmethod
    def delete(self, collection: str, ids: list[str]) -> None: ...

    @abstractmethod
    def ensure_collection(self, collection: str, dimension: int) -> None: ...
