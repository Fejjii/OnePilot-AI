"""Tests for knowledge-base reindex (chunks + vectors, idempotent)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import PlanCode, Role
from onepilot.demo_data.seed import seed_knowledge_base
from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
from onepilot.providers.vector.memory_vector_provider import MemoryVectorProvider
from onepilot.repositories.documents import DocumentChunkRepository, DocumentRepository
from onepilot.repositories.models import Document
from onepilot.security.auth import Principal
from onepilot.services import document_service


@pytest.fixture
def principal() -> Principal:
    return Principal(
        user_id="usr_reindex",
        organization_id="org_reindex",
        role=Role.OWNER,
        plan_code=PlanCode.BUSINESS,
    )


@pytest.fixture
def fallback_embeddings() -> FallbackEmbeddingsProvider:
    return FallbackEmbeddingsProvider()


@pytest.fixture
def memory_vector() -> MemoryVectorProvider:
    return MemoryVectorProvider()


class TestReindexKnowledgeBase:
    def test_seed_idempotent_without_duplicating_documents(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: FallbackEmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
    ) -> None:
        settings = Settings()
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            (docs_dir / "alpha.md").write_text("# Alpha\n\nServices and integrations overview.")
            (docs_dir / "beta.md").write_text("# Beta\n\nHubSpot and Gmail calendar sync.")

            first = seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
            )
            second = seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
            )

        assert first.documents_created == 2
        assert second.documents_created == 0
        assert second.documents_skipped == 2
        assert DocumentRepository(db_session).count_for_org(principal.organization_id) == 2

    def test_reindex_existing_docs_creates_vectors(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: FallbackEmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
    ) -> None:
        settings = Settings()
        doc = Document(
            id="doc_reindex_1",
            organization_id=principal.organization_id,
            filename="services.md",
            title="Services",
            content_type="text/markdown",
            size_bytes=80,
            chunk_count=0,
            status="ready",
            source="demo_seed",
            uploaded_by=principal.user_id,
        )
        DocumentRepository(db_session).create(doc)
        db_session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            (docs_dir / "services.md").write_text(
                "# Services\n\nNovaEdge offers AI workspace, HubSpot, Gmail, and Calendar integrations."
            )
            result = document_service.reindex_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                source_dir=docs_dir,
            )

        assert result.documents_seen == 1
        assert result.documents_created == 0
        assert result.chunks_created > 0
        assert result.vector_upserts > 0
        assert result.sample_search_hits > 0

    def test_reindex_does_not_duplicate_documents(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: FallbackEmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
    ) -> None:
        settings = Settings()
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            (docs_dir / "only.md").write_text("# Only\n\nSingle document for reindex idempotency.")

            seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
            )
            count_before = DocumentRepository(db_session).count_for_org(principal.organization_id)

            reindex_result = document_service.reindex_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                source_dir=docs_dir,
            )
            count_after = DocumentRepository(db_session).count_for_org(principal.organization_id)

        assert count_before == count_after == 1
        assert reindex_result.documents_created == 0
        assert reindex_result.vector_upserts > 0

    def test_reindex_uses_stable_vector_ids(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: FallbackEmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
    ) -> None:
        settings = Settings()
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            (docs_dir / "stable.md").write_text("# Stable\n\nDeterministic vector point ids.")

            seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
            )
            collection = document_service.collection_name(principal.organization_id)
            first_ids = set(memory_vector._collections[collection].records.keys())

            document_service.reindex_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                source_dir=docs_dir,
            )
            second_ids = set(memory_vector._collections[collection].records.keys())

        assert first_ids == second_ids
        assert len(first_ids) > 0

    def test_seed_reindex_flag_rebuilds_vectors(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: FallbackEmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
    ) -> None:
        settings = Settings()
        doc = Document(
            id="doc_seed_reindex",
            organization_id=principal.organization_id,
            filename="seed_reindex.md",
            title="Seed Reindex",
            content_type="text/markdown",
            size_bytes=50,
            chunk_count=0,
            status="ready",
            source="demo_seed",
            uploaded_by=principal.user_id,
        )
        DocumentRepository(db_session).create(doc)
        db_session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            (docs_dir / "seed_reindex.md").write_text(
                "# Seed Reindex\n\nNovaEdge services and HubSpot integrations."
            )
            result = seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
                reindex=True,
            )

        assert result.documents_skipped == 1
        assert result.documents_created == 0
        assert result.vector_upsert_count > 0
        assert result.total_chunks > 0

    def test_seed_hint_when_documents_skipped_without_vectors(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: FallbackEmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
    ) -> None:
        from unittest.mock import MagicMock, patch

        from onepilot.services.rag_service import SearchOutcome

        settings = Settings()
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            (docs_dir / "hint.md").write_text("# Hint\n\nNovaEdge services overview.")

            seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
            )
            memory_vector._collections.clear()

            fake_hit = MagicMock()
            with patch(
                "onepilot.services.rag_service.search",
                side_effect=[
                    SearchOutcome(
                        query="test",
                        hits=[fake_hit],
                        weak_evidence=False,
                        fallback_used=False,
                    ),
                    SearchOutcome(
                        query="verify",
                        hits=[],
                        weak_evidence=True,
                        fallback_used=False,
                    ),
                ],
            ):
                result = seed_knowledge_base(
                    db_session,
                    principal=principal,
                    settings=settings,
                    embeddings=fallback_embeddings,
                    vector=memory_vector,
                    docs_dir=docs_dir,
                )

        assert result.documents_skipped == 1
        assert result.documents_created == 0
        assert result.reindex_hint is not None
        assert "reindex" in result.reindex_hint.lower()

    def test_missing_qdrant_uses_memory_provider(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: FallbackEmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = Settings()
        monkeypatch.setattr(settings, "QDRANT_URL", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            (docs_dir / "memory.md").write_text("# Memory\n\nFallback vector store without Qdrant.")
            seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
            )
            memory_vector._collections.clear()

            result = document_service.reindex_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                source_dir=docs_dir,
            )

        assert result.qdrant_configured is False
        assert result.provider_mode == "memory"
        assert result.vector_upserts > 0
