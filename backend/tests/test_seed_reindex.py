"""Tests for seed reindexing when embedding provider changes."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import PlanCode, Role
from onepilot.demo_data.seed import seed_knowledge_base
from onepilot.providers.embeddings.base import EmbeddingsProvider
from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
from onepilot.providers.embeddings.openai_embeddings import OpenAIEmbeddingsProvider
from onepilot.providers.vector.memory_vector_provider import MemoryVectorProvider
from onepilot.repositories.documents import DocumentChunkRepository, DocumentRepository
from onepilot.repositories.models import Document, DocumentChunk
from onepilot.security.auth import Principal


@pytest.fixture
def principal() -> Principal:
    return Principal(
        user_id="usr_test",
        organization_id="org_test",
        role=Role.OWNER,
        plan_code=PlanCode.BUSINESS,
    )


@pytest.fixture
def fallback_embeddings() -> EmbeddingsProvider:
    return FallbackEmbeddingsProvider()


@pytest.fixture
def openai_embeddings() -> Generator[EmbeddingsProvider, None, None]:
    """Mock OpenAI embeddings provider with deterministic embeddings."""
    
    class MockEmbeddingResponse:
        def __init__(self, embedding: list[float], index: int):
            self.embedding = embedding
            self.index = index
    
    class MockEmbeddingsData:
        def __init__(self, embeddings: list[list[float]]):
            self.data = [MockEmbeddingResponse(emb, idx) for idx, emb in enumerate(embeddings)]
    
    def mock_create(input, **kwargs):
        # Return deterministic embeddings based on input text
        if isinstance(input, str):
            inputs = [input]
        else:
            inputs = input
        
        # Generate deterministic 1536-dim vectors
        embeddings = []
        for text in inputs:
            # Use hash of text to generate deterministic vector
            import hashlib
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            # Generate 1536 values based on hash
            vec = [(hash_val + i) % 1000 / 1000.0 for i in range(1536)]
            # Normalize to unit vector
            norm = sum(v * v for v in vec) ** 0.5
            vec = [v / norm for v in vec]
            embeddings.append(vec)
        
        return MockEmbeddingsData(embeddings)
    
    with patch("onepilot.providers.embeddings.openai_embeddings.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.embeddings.create = mock_create
        mock_openai.return_value = mock_client
        
        yield OpenAIEmbeddingsProvider(api_key="test-key", default_model="text-embedding-3-small", dim=1536)


@pytest.fixture
def memory_vector() -> MemoryVectorProvider:
    return MemoryVectorProvider()


class TestSeedReindex:
    """Test seed reindexing behavior when provider changes."""
    
    def test_seed_detects_missing_vectors_and_reindexes(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
    ) -> None:
        """Test that seed detects when vectors are missing and triggers reindex."""
        settings = Settings()
        # Create a document manually in Postgres without vectors
        doc = Document(
            id="doc_test_123",
            organization_id=principal.organization_id,
            filename="test.md",
            title="Test Document",
            content_type="text/markdown",
            size_bytes=100,
            chunk_count=1,
            status="ready",
            source="test",
            uploaded_by=principal.user_id,
        )
        doc_repo = DocumentRepository(db_session)
        doc_repo.create(doc)
        
        chunk = DocumentChunk(
            id="chunk_test_456",
            organization_id=principal.organization_id,
            document_id=doc.id,
            ordinal=0,
            section="",
            content="This is a test document about services and integrations.",
            token_count=10,
        )
        chunk_repo = DocumentChunkRepository(db_session)
        chunk_repo.bulk_create([chunk])
        db_session.commit()
        
        # Verify document exists but vector search returns nothing
        assert doc_repo.count_for_org(principal.organization_id) == 1
        collection = f"documents_{principal.organization_id}"
        
        # Vector collection doesn't exist yet (or is empty after dimension mismatch)
        # When we seed, it should detect this and reindex
        
        # Create a temporary docs directory with one markdown file
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            test_file = docs_dir / "test2.md"
            test_file.write_text("# Test Document 2\n\nThis is another test document.")
            
            # Seed should detect existing doc has no vectors and reindex
            result = seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=fallback_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
            )
            
            # Should have created 1 new document and reindexed the existing one
            assert result.documents_created == 1
            assert result.documents_skipped == 0
            assert result.total_documents == 2
            # Should have upserted vectors for both documents (1 existing chunk + chunks from new doc)
            assert result.vector_upsert_count > 0
    
    def test_seed_with_openai_after_fallback(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        openai_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
    ) -> None:
        """Test switching from fallback to OpenAI embeddings triggers reindex."""
        settings = Settings()
        # First seed with fallback embeddings
        doc = Document(
            id="doc_test_789",
            organization_id=principal.organization_id,
            filename="test.md",
            title="Test Document",
            content_type="text/markdown",
            size_bytes=100,
            chunk_count=1,
            status="ready",
            source="test",
            uploaded_by=principal.user_id,
        )
        doc_repo = DocumentRepository(db_session)
        doc_repo.create(doc)
        
        chunk = DocumentChunk(
            id="chunk_test_abc",
            organization_id=principal.organization_id,
            document_id=doc.id,
            ordinal=0,
            section="",
            content="Test content for reindexing.",
            token_count=5,
        )
        chunk_repo = DocumentChunkRepository(db_session)
        chunk_repo.bulk_create([chunk])
        db_session.commit()
        
        # Create collection with fallback dimension (384)
        collection = f"documents_{principal.organization_id}"
        memory_vector.ensure_collection(collection, fallback_embeddings.dimension)
        
        # Upsert with fallback embeddings
        vectors_fallback = fallback_embeddings.embed([chunk.content])
        memory_vector.upsert(
            collection=collection,
            ids=[chunk.id],
            vectors=vectors_fallback,
            payloads=[{"chunk_id": chunk.id, "document_id": doc.id}],
        )
        
        # Verify search works with fallback
        results = memory_vector.search(collection, vectors_fallback[0], top_k=1)
        assert len(results) == 1
        
        # Now simulate switching to OpenAI embeddings (dimension 1536)
        # The collection will be recreated with new dimension, old vectors deleted
        # (This is what ensure_collection does when dimension changes)
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            # Create a dummy file with the same name as existing doc to test skipping
            test_file = docs_dir / "test.md"
            test_file.write_text("# Existing Doc\n\nThis will be skipped.")
            
            # Seed with OpenAI embeddings
            # This should detect dimension mismatch and reindex
            result = seed_knowledge_base(
                db_session,
                principal=principal,
                settings=settings,
                embeddings=openai_embeddings,
                vector=memory_vector,
                docs_dir=docs_dir,
            )
            
            # Should have detected reindex needed
            assert result.documents_created == 0
            assert result.documents_skipped == 1
            assert result.total_documents == 1
            # Should have reindexed the existing document
            assert result.vector_upsert_count == 1
    
    def test_seed_fails_if_documents_exist_but_no_vectors_after_seed(
        self,
        db_session: Session,
        principal: Principal,
    ) -> None:
        """Test that seed fails with clear error if verification detects missing vectors."""
        settings = Settings()
        # Create a document manually
        doc = Document(
            id="doc_test_fail",
            organization_id=principal.organization_id,
            filename="test.md",
            title="Test Document",
            content_type="text/markdown",
            size_bytes=100,
            chunk_count=1,
            status="ready",
            source="test",
            uploaded_by=principal.user_id,
        )
        doc_repo = DocumentRepository(db_session)
        doc_repo.create(doc)
        
        chunk = DocumentChunk(
            id="chunk_test_fail",
            organization_id=principal.organization_id,
            document_id=doc.id,
            ordinal=0,
            section="",
            content="Test content",
            token_count=5,
        )
        chunk_repo = DocumentChunkRepository(db_session)
        chunk_repo.bulk_create([chunk])
        db_session.commit()
        
        # Create a broken embeddings provider that returns empty vectors
        class BrokenEmbeddingsProvider(EmbeddingsProvider):
            @property
            def dimension(self) -> int:
                return 384
            
            def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
                # Return incorrect number of vectors (causes upsert to fail)
                return []
            
            def embed_query(self, text: str, model: str | None = None) -> list[float]:
                return []
        
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            
            # Seed with broken provider should fail verification
            with pytest.raises(RuntimeError, match="Seed verification failed.*search returns 0 results"):
                seed_knowledge_base(
                    db_session,
                    principal=principal,
                    settings=settings,
                    embeddings=BrokenEmbeddingsProvider(),
                    vector=MemoryVectorProvider(),
                    docs_dir=docs_dir,
                )
