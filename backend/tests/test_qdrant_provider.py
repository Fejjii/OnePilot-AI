"""Unit tests for QdrantVectorProvider.ensure_collection payload-index behavior.

Qdrant Cloud strict mode requires a keyword payload index on organization_id
before filtered search. These tests mock the Qdrant client and never contact
a live cluster.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.vector.qdrant_provider import QdrantVectorProvider, _to_point_id

_COLLECTION = "documents_org_test"
_DIMENSION = 1536


def _provider_with_client(client: MagicMock) -> QdrantVectorProvider:
    provider = QdrantVectorProvider(url="http://qdrant.test.invalid")
    provider._client = client
    return provider


def _collection_info(*, size: int, payload_schema: dict[str, Any] | None = None) -> MagicMock:
    info = MagicMock()
    info.config.params.vectors.size = size
    info.payload_schema = {} if payload_schema is None else payload_schema
    return info


def _keyword_index_info() -> MagicMock:
    info = MagicMock()
    info.data_type = "keyword"
    return info


def _payload_index_kwargs(client: MagicMock) -> dict[str, Any]:
    assert client.create_payload_index.called
    return client.create_payload_index.call_args.kwargs


def _assert_keyword_organization_id_index(client: MagicMock) -> None:
    kwargs = _payload_index_kwargs(client)
    assert kwargs["collection_name"] == _COLLECTION
    assert kwargs["field_name"] == "organization_id"
    assert kwargs["wait"] is True
    schema = kwargs["field_schema"]
    schema_value = getattr(schema, "value", schema)
    assert str(schema_value).lower() == "keyword"


class TestEnsureCollectionCreatesPayloadIndex:
    def test_new_collection_creates_collection_and_keyword_index(self) -> None:
        client = MagicMock()
        client.get_collection.side_effect = Exception("Collection documents_org_test not found")
        provider = _provider_with_client(client)

        provider.ensure_collection(_COLLECTION, _DIMENSION)

        client.create_collection.assert_called_once()
        create_kwargs = client.create_collection.call_args.kwargs
        assert create_kwargs["collection_name"] == _COLLECTION
        assert create_kwargs["vectors_config"].size == _DIMENSION
        client.recreate_collection.assert_not_called()
        _assert_keyword_organization_id_index(client)

    def test_existing_collection_without_index_adds_index_only(self) -> None:
        client = MagicMock()
        client.get_collection.return_value = _collection_info(size=_DIMENSION, payload_schema={})
        provider = _provider_with_client(client)

        provider.ensure_collection(_COLLECTION, _DIMENSION)

        client.create_collection.assert_not_called()
        client.recreate_collection.assert_not_called()
        _assert_keyword_organization_id_index(client)

    def test_existing_collection_with_index_skips_duplicate_create(self) -> None:
        client = MagicMock()
        client.get_collection.return_value = _collection_info(
            size=_DIMENSION,
            payload_schema={"organization_id": _keyword_index_info()},
        )
        provider = _provider_with_client(client)

        provider.ensure_collection(_COLLECTION, _DIMENSION)

        client.create_collection.assert_not_called()
        client.recreate_collection.assert_not_called()
        client.create_payload_index.assert_not_called()

    def test_index_already_exists_error_is_idempotent(self) -> None:
        client = MagicMock()
        client.get_collection.return_value = _collection_info(size=_DIMENSION, payload_schema={})
        client.create_payload_index.side_effect = Exception(
            'Index already exists for field "organization_id"'
        )
        provider = _provider_with_client(client)

        provider.ensure_collection(_COLLECTION, _DIMENSION)

        client.recreate_collection.assert_not_called()
        client.create_payload_index.assert_called_once()

    def test_index_creation_failure_raises_provider_unavailable(self) -> None:
        client = MagicMock()
        client.get_collection.return_value = _collection_info(size=_DIMENSION, payload_schema={})
        client.create_payload_index.side_effect = Exception("Qdrant unavailable: timeout")
        provider = _provider_with_client(client)

        with pytest.raises(ProviderUnavailableError, match="create_payload_index"):
            provider.ensure_collection(_COLLECTION, _DIMENSION)

        client.recreate_collection.assert_not_called()

    def test_matching_dimension_does_not_recreate_collection(self) -> None:
        client = MagicMock()
        client.get_collection.return_value = _collection_info(
            size=_DIMENSION,
            payload_schema={"organization_id": _keyword_index_info()},
        )
        provider = _provider_with_client(client)

        provider.ensure_collection(_COLLECTION, _DIMENSION)

        client.recreate_collection.assert_not_called()
        client.create_collection.assert_not_called()

    def test_dimension_mismatch_still_recreates_then_indexes(self) -> None:
        client = MagicMock()
        client.get_collection.return_value = _collection_info(size=384, payload_schema={})
        provider = _provider_with_client(client)

        provider.ensure_collection(_COLLECTION, _DIMENSION)

        client.create_collection.assert_not_called()
        client.recreate_collection.assert_called_once()
        recreate_kwargs = client.recreate_collection.call_args.kwargs
        assert recreate_kwargs["collection_name"] == _COLLECTION
        assert recreate_kwargs["vectors_config"].size == _DIMENSION
        _assert_keyword_organization_id_index(client)


_CHUNK_A = "chunk_01ARZ3NDEKTSV4RRFFQ69G5FAV"
_CHUNK_B = "chunk_01BX5ZZKBKACTAV9WEVGEMMVRZ"
_ORG_ID = "org_demo_onepilot"


def _upsert_kwargs(client: MagicMock) -> dict[str, Any]:
    assert client.upsert.called
    return client.upsert.call_args.kwargs


def _point_ids(points: list[Any]) -> list[str]:
    return [str(point.id) for point in points]


class TestDeterministicPointIds:
    def test_same_chunk_id_always_maps_to_same_uuid(self) -> None:
        first = _to_point_id(_CHUNK_A)
        second = _to_point_id(_CHUNK_A)
        assert first == second
        parsed = uuid.UUID(first)
        assert parsed.version == 5

    def test_different_chunk_ids_produce_different_point_ids(self) -> None:
        assert _to_point_id(_CHUNK_A) != _to_point_id(_CHUNK_B)

    def test_full_chunk_id_including_prefix_is_the_mapping_key(self) -> None:
        # Prefix-stripped ULID conversion would collide across entity types.
        assert _to_point_id(_CHUNK_A) != _to_point_id(_CHUNK_A.removeprefix("chunk_"))


class TestIdempotentUpsert:
    def test_first_upsert_inserts_n_points_with_deterministic_ids(self) -> None:
        client = MagicMock()
        provider = _provider_with_client(client)
        vectors = [[0.1, 0.2], [0.3, 0.4]]
        payloads = [
            {"organization_id": _ORG_ID, "ordinal": 0},
            {"organization_id": _ORG_ID, "ordinal": 1},
        ]

        count = provider.upsert(
            _COLLECTION,
            [_CHUNK_A, _CHUNK_B],
            vectors,
            payloads,
        )

        assert count == 2
        kwargs = _upsert_kwargs(client)
        assert kwargs["collection_name"] == _COLLECTION
        assert kwargs["wait"] is True
        points = kwargs["points"]
        assert len(points) == 2
        assert _point_ids(points) == [_to_point_id(_CHUNK_A), _to_point_id(_CHUNK_B)]
        assert points[0].payload["chunk_ulid"] == _CHUNK_A
        assert points[1].payload["chunk_ulid"] == _CHUNK_B
        assert points[0].payload["organization_id"] == _ORG_ID
        assert points[0].vector == vectors[0]

    def test_repeating_the_same_upsert_reuses_the_same_point_ids(self) -> None:
        client = MagicMock()
        provider = _provider_with_client(client)
        ids = [_CHUNK_A, _CHUNK_B]
        vectors = [[1.0], [2.0]]
        payloads = [{"organization_id": _ORG_ID}, {"organization_id": _ORG_ID}]

        provider.upsert(_COLLECTION, ids, vectors, [dict(p) for p in payloads])
        first_ids = _point_ids(_upsert_kwargs(client)["points"])

        provider.upsert(_COLLECTION, ids, vectors, [dict(p) for p in payloads])
        second_ids = _point_ids(_upsert_kwargs(client)["points"])

        assert client.upsert.call_count == 2
        assert len(first_ids) == 2
        assert first_ids == second_ids
        assert first_ids == [_to_point_id(_CHUNK_A), _to_point_id(_CHUNK_B)]

    def test_changed_vector_and_payload_keep_the_same_point_id(self) -> None:
        client = MagicMock()
        provider = _provider_with_client(client)

        provider.upsert(
            _COLLECTION,
            [_CHUNK_A],
            [[0.1, 0.2]],
            [{"organization_id": _ORG_ID, "ordinal": 0}],
        )
        first = _upsert_kwargs(client)["points"][0]

        provider.upsert(
            _COLLECTION,
            [_CHUNK_A],
            [[9.9, 8.8]],
            [{"organization_id": _ORG_ID, "ordinal": 99, "section": "updated"}],
        )
        second = _upsert_kwargs(client)["points"][0]

        assert str(first.id) == str(second.id) == _to_point_id(_CHUNK_A)
        assert second.vector == [9.9, 8.8]
        assert second.payload["ordinal"] == 99
        assert second.payload["section"] == "updated"
        assert second.payload["chunk_ulid"] == _CHUNK_A
        assert second.payload["organization_id"] == _ORG_ID


class TestDeleteUsesDeterministicIds:
    def test_delete_uses_the_same_point_ids_as_upsert(self) -> None:
        client = MagicMock()
        provider = _provider_with_client(client)
        provider.upsert(
            _COLLECTION,
            [_CHUNK_A, _CHUNK_B],
            [[0.1], [0.2]],
            [{"organization_id": _ORG_ID}, {"organization_id": _ORG_ID}],
        )
        upserted_ids = _point_ids(_upsert_kwargs(client)["points"])

        provider.delete(_COLLECTION, [_CHUNK_A, _CHUNK_B])

        delete_kwargs = client.delete.call_args.kwargs
        assert delete_kwargs["collection_name"] == _COLLECTION
        selector = delete_kwargs["points_selector"]
        assert list(selector.points) == upserted_ids
        assert list(selector.points) == [_to_point_id(_CHUNK_A), _to_point_id(_CHUNK_B)]


class TestSearchReturnsChunkUlid:
    def test_search_result_id_is_original_chunk_ulid(self) -> None:
        client = MagicMock()
        hit = MagicMock()
        hit.id = _to_point_id(_CHUNK_A)
        hit.score = 0.91
        hit.payload = {
            "chunk_ulid": _CHUNK_A,
            "organization_id": _ORG_ID,
            "document_title": "Refund Policy",
        }
        response = MagicMock()
        response.points = [hit]
        client.query_points.return_value = response
        provider = _provider_with_client(client)

        results = provider.search(
            _COLLECTION,
            vector=[0.1, 0.2],
            top_k=1,
            filters={"organization_id": _ORG_ID},
        )

        assert len(results) == 1
        assert results[0].id == _CHUNK_A
        assert results[0].payload["chunk_ulid"] == _CHUNK_A
        assert results[0].payload["organization_id"] == _ORG_ID
        query_kwargs = client.query_points.call_args.kwargs
        assert query_kwargs["collection_name"] == _COLLECTION
        assert query_kwargs["limit"] == 1
        assert query_kwargs["with_payload"] is True
