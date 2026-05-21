"""Qdrant-backed vector provider.

The Qdrant client is imported lazily so that test environments and local demos
which never reach this provider do not pay the import cost. If the client cannot
be imported or the server is unreachable, callers receive a
:class:`ProviderUnavailableError` and should fall back to the in-memory provider.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from ulid import ULID

from onepilot.core.errors import ProviderUnavailableError
from onepilot.core.logging import get_logger
from onepilot.providers.vector.base import VectorProvider, VectorSearchResult

if TYPE_CHECKING:  # pragma: no cover
    from qdrant_client import QdrantClient

log = get_logger(__name__)


class QdrantVectorProvider(VectorProvider):
    """Vector provider backed by a Qdrant deployment."""

    def __init__(self, url: str, api_key: str = "") -> None:
        if not url:
            raise ProviderUnavailableError("Qdrant URL not configured")
        self._url = url
        self._api_key = api_key
        self._client: QdrantClient | None = None

    def _get_client(self) -> QdrantClient:
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:  # pragma: no cover - qdrant-client is in pyproject
            raise ProviderUnavailableError("qdrant-client is not installed") from exc

        try:
            self._client = QdrantClient(
                url=self._url,
                api_key=self._api_key or None,
                prefer_grpc=False,
                timeout=60.0,  # Increased timeout for bulk operations
            )
        except Exception as exc:  # pragma: no cover - network failures
            raise ProviderUnavailableError(f"Cannot reach Qdrant at {self._url}") from exc
        return self._client

    def ensure_collection(self, collection: str, dimension: int) -> None:
        from qdrant_client.http import models as qm

        client = self._get_client()
        try:
            collection_info = client.get_collection(collection)
        except Exception as exc:  # pragma: no cover
            if _is_missing_collection_error(exc):
                client.create_collection(
                    collection_name=collection,
                    vectors_config=qm.VectorParams(size=dimension, distance=qm.Distance.COSINE),
                )
                _ensure_organization_id_index(client, collection)
                return
            raise ProviderUnavailableError("Qdrant get_collection failed") from exc

        existing_dimension = _collection_vector_size(collection_info)
        if existing_dimension == dimension:
            _ensure_organization_id_index(client, collection)
            return

        log.warning(
            "qdrant_collection_dimension_mismatch",
            collection=collection,
            existing_dimension=existing_dimension,
            expected_dimension=dimension,
        )

        client.recreate_collection(
            collection_name=collection,
            vectors_config=qm.VectorParams(size=dimension, distance=qm.Distance.COSINE),
        )
        _ensure_organization_id_index(client, collection)

    def upsert(
        self,
        collection: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> int:
        from qdrant_client.http import models as qm

        client = self._get_client()
        points = []
        for point_id, vec, payload in zip(ids, vectors, payloads):
            payload.setdefault("chunk_ulid", payload.get("chunk_id", point_id))
            points.append(
                qm.PointStruct(id=_to_point_id(point_id), vector=vec, payload=payload)
            )

        client.upsert(collection_name=collection, points=points, wait=True)
        return len(ids)

    def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]:
        client = self._get_client()
        qdrant_filter = _build_filter(filters)
        if hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=collection,
                query=vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            results = getattr(response, "points", response)
        else:  # pragma: no cover - older qdrant-client compatibility
            results = client.search(
                collection_name=collection,
                query_vector=vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
            )
        return [
            VectorSearchResult(
                id=str(r.payload.get("chunk_ulid", r.id)) if r.payload else str(r.id),
                score=float(r.score),
                payload=dict(r.payload or {}),
            )
            for r in results
        ]

    def delete(self, collection: str, ids: list[str]) -> None:
        from qdrant_client.http import models as qm

        client = self._get_client()
        client.delete(
            collection_name=collection,
            points_selector=qm.PointIdsList(points=[_to_point_id(i) for i in ids]),
        )


def _to_point_id(value: str) -> str:
    """Converts a ULID string to a UUID string if it's not already a valid UUID."""
    try:
        uuid.UUID(value) # Check if it's already a valid UUID
        return value
    except ValueError:
        # If not a UUID, assume it's a ULID string and convert
        if "_" in value:
            _, ulid_str = value.split("_", 1)
        else:
            ulid_str = value
        return str(ULID.from_str(ulid_str).to_uuid())


def _build_filter(filters: dict | None) -> Any:
    if not filters:
        return None
    from qdrant_client.http import models as qm

    must = [
        qm.FieldCondition(key=key, match=qm.MatchValue(value=value))
        for key, value in filters.items()
    ]
    return qm.Filter(must=must)


def _collection_vector_size(collection_info: Any) -> int | None:
    config = getattr(collection_info, "config", None)
    params = getattr(config, "params", None)
    vectors = getattr(params, "vectors", None)
    if vectors is None:
        return None
    size = getattr(vectors, "size", None)
    if isinstance(size, int):
        return size
    if isinstance(vectors, dict):
        maybe_size = vectors.get("size")
        return maybe_size if isinstance(maybe_size, int) else None
    return None


def _is_missing_collection_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "not found" in message or "does not exist" in message or "missing" in message


def _ensure_organization_id_index(client: QdrantClient, collection: str) -> None:
    """Ensure tenant filter field is indexed (required by Qdrant for payload filters)."""
    from qdrant_client.http import models as qm

    try:
        client.create_payload_index(
            collection_name=collection,
            field_name="organization_id",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )
    except Exception as exc:  # pragma: no cover - index may already exist
        message = str(exc).lower()
        if "already exists" not in message and "already has" not in message:
            log.warning(
                "qdrant_organization_id_index_failed",
                collection=collection,
                error=str(exc),
            )
