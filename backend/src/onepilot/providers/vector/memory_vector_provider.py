from __future__ import annotations

import math
from dataclasses import dataclass, field

from onepilot.providers.vector.base import VectorProvider, VectorSearchResult


@dataclass
class _VectorRecord:
    id: str
    vector: list[float]
    payload: dict


@dataclass
class _Collection:
    dimension: int
    records: dict[str, _VectorRecord] = field(default_factory=dict)


class MemoryVectorProvider(VectorProvider):
    """In-memory vector store using brute-force cosine similarity."""

    def __init__(self) -> None:
        self._collections: dict[str, _Collection] = {}

    def ensure_collection(self, collection: str, dimension: int) -> None:
        if collection not in self._collections:
            self._collections[collection] = _Collection(dimension=dimension)
        elif self._collections[collection].dimension != dimension:
            # Dimension changed - recreate the collection (drop old vectors)
            self._collections[collection] = _Collection(dimension=dimension)

    def upsert(
        self,
        collection: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> int:
        col = self._get_collection(collection)
        for vid, vec, pay in zip(ids, vectors, payloads):
            col.records[vid] = _VectorRecord(id=vid, vector=vec, payload=pay)
        return len(ids)

    def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]:
        col = self._get_collection(collection)
        scored: list[tuple[float, _VectorRecord]] = []
        for rec in col.records.values():
            if filters and not _matches_filters(rec.payload, filters):
                continue
            score = _cosine_similarity(vector, rec.vector)
            scored.append((score, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            VectorSearchResult(
                id=str(
                    rec.payload.get("chunk_ulid")
                    or rec.payload.get("chunk_id")
                    or rec.id
                ),
                score=score,
                payload=rec.payload,
            )
            for score, rec in scored[:top_k]
        ]

    def delete(self, collection: str, ids: list[str]) -> None:
        col = self._get_collection(collection)
        for vid in ids:
            col.records.pop(vid, None)

    def _get_collection(self, name: str) -> _Collection:
        if name not in self._collections:
            self._collections[name] = _Collection(dimension=0)
        return self._collections[name]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot_val = _dot(a, b)
    norm_a = math.sqrt(_dot(a, a)) or 1.0
    norm_b = math.sqrt(_dot(b, b)) or 1.0
    return dot_val / (norm_a * norm_b)


def _matches_filters(payload: dict, filters: dict) -> bool:
    """Simple key-equality filter matching."""
    return all(payload.get(k) == v for k, v in filters.items())
