"""Tests for Qdrant collection setup and organization_id payload indexing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from qdrant_client.http import models as qm

from onepilot.providers.vector.qdrant_provider import (
    QdrantVectorProvider,
    _ensure_organization_id_index,
)


def _mock_collection_info(*, size: int) -> MagicMock:
    info = MagicMock()
    info.config.params.vectors.size = size
    return info


class TestEnsureOrganizationIdIndex:
    def test_creates_keyword_index(self) -> None:
        client = MagicMock()
        _ensure_organization_id_index(client, "documents_org_test")
        client.create_payload_index.assert_called_once_with(
            collection_name="documents_org_test",
            field_name="organization_id",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )

    def test_ignores_already_exists(self) -> None:
        client = MagicMock()
        client.create_payload_index.side_effect = Exception("Index already exists")
        _ensure_organization_id_index(client, "documents_org_test")
        client.create_payload_index.assert_called_once()


class TestQdrantEnsureCollection:
    @patch("onepilot.providers.vector.qdrant_provider.QdrantVectorProvider._get_client")
    def test_creates_collection_and_payload_index(self, mock_get_client: MagicMock) -> None:
        client = MagicMock()
        client.get_collection.side_effect = Exception("Collection not found")
        mock_get_client.return_value = client

        provider = QdrantVectorProvider(url="http://qdrant:6333")
        provider.ensure_collection("documents_org_new", dimension=1536)

        client.create_collection.assert_called_once()
        client.create_payload_index.assert_called_once_with(
            collection_name="documents_org_new",
            field_name="organization_id",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )
        client.recreate_collection.assert_not_called()

    @patch("onepilot.providers.vector.qdrant_provider.QdrantVectorProvider._get_client")
    def test_matching_dimension_ensures_index_only(self, mock_get_client: MagicMock) -> None:
        client = MagicMock()
        client.get_collection.return_value = _mock_collection_info(size=1536)
        mock_get_client.return_value = client

        provider = QdrantVectorProvider(url="http://qdrant:6333")
        provider.ensure_collection("documents_org_existing", dimension=1536)

        client.create_collection.assert_not_called()
        client.recreate_collection.assert_not_called()
        client.create_payload_index.assert_called_once()

    @patch("onepilot.providers.vector.qdrant_provider.QdrantVectorProvider._get_client")
    def test_dimension_mismatch_recreates_and_indexes(self, mock_get_client: MagicMock) -> None:
        client = MagicMock()
        client.get_collection.return_value = _mock_collection_info(size=384)
        mock_get_client.return_value = client

        provider = QdrantVectorProvider(url="http://qdrant:6333")
        provider.ensure_collection("documents_org_migrate", dimension=1536)

        client.recreate_collection.assert_called_once()
        client.create_payload_index.assert_called_once_with(
            collection_name="documents_org_migrate",
            field_name="organization_id",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )

    @patch("onepilot.providers.vector.qdrant_provider.QdrantVectorProvider._get_client")
    def test_index_already_exists_after_recreate_is_safe(
        self, mock_get_client: MagicMock
    ) -> None:
        client = MagicMock()
        client.get_collection.return_value = _mock_collection_info(size=384)
        client.create_payload_index.side_effect = Exception("already has index")
        mock_get_client.return_value = client

        provider = QdrantVectorProvider(url="http://qdrant:6333")
        provider.ensure_collection("documents_org_safe", dimension=1536)

        client.recreate_collection.assert_called_once()
        client.create_payload_index.assert_called_once()
