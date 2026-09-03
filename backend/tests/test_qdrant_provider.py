"""Unit tests for QdrantVectorProvider.ensure_collection payload-index behavior.

Qdrant Cloud strict mode requires a keyword payload index on organization_id
before filtered search. These tests mock the Qdrant client and never contact
a live cluster.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.vector.qdrant_provider import QdrantVectorProvider

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
