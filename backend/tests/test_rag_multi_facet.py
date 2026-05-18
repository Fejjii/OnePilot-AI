"""Tests for generalized multi-facet RAG retrieval.

Verifies that compound queries retrieve relevant documents for all detected facets.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import PlanCode, Role
from onepilot.providers.embeddings.base import EmbeddingsProvider
from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
from onepilot.providers.vector.memory_vector_provider import MemoryVectorProvider
from onepilot.repositories.documents import DocumentChunkRepository, DocumentRepository
from onepilot.repositories.models import Document, DocumentChunk
from onepilot.security.auth import Principal
from onepilot.services import rag_service


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
def memory_vector() -> MemoryVectorProvider:
    return MemoryVectorProvider()


@pytest.fixture
def comprehensive_docs(db_session: Session, principal: Principal) -> list[Document]:
    """Create comprehensive test documents covering multiple facets."""
    doc_repo = DocumentRepository(db_session)
    chunk_repo = DocumentChunkRepository(db_session)
    
    documents = []
    chunks_to_create = []
    
    # Services Overview
    services_doc = Document(
        id="doc_services",
        organization_id=principal.organization_id,
        filename="services_overview.md",
        title="NovaEdge Solutions — Services Overview",
        content_type="text/markdown",
        size_bytes=1000,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(services_doc)
    documents.append(services_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_services",
            organization_id=principal.organization_id,
            document_id=services_doc.id,
            ordinal=0,
            section="Services Overview",
            content=(
                "NovaEdge Solutions offers comprehensive AI-powered customer support automation, "
                "intelligent lead qualification, automated email workflows, internal knowledge search, "
                "and smart appointment booking."
            ),
            token_count=40,
        )
    )
    
    # Integration Guide
    integration_doc = Document(
        id="doc_integration",
        organization_id=principal.organization_id,
        filename="integration_guide.md",
        title="Integration Guide — HubSpot, Gmail, Google Calendar",
        content_type="text/markdown",
        size_bytes=800,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(integration_doc)
    documents.append(integration_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_integration",
            organization_id=principal.organization_id,
            document_id=integration_doc.id,
            ordinal=0,
            section="Supported Integrations",
            content=(
                "NovaEdge supports integrations with HubSpot CRM, Gmail and Google Workspace, "
                "and Google Calendar. All integrations are seamless and secure."
            ),
            token_count=30,
        )
    )
    
    # Pricing Plans
    pricing_doc = Document(
        id="doc_pricing",
        organization_id=principal.organization_id,
        filename="pricing_plans.md",
        title="Pricing Plans",
        content_type="text/markdown",
        size_bytes=600,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(pricing_doc)
    documents.append(pricing_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_pricing",
            organization_id=principal.organization_id,
            document_id=pricing_doc.id,
            ordinal=0,
            section="Plans and Pricing",
            content=(
                "NovaEdge offers three pricing plans: Starter at $99/month, Professional at $299/month, "
                "and Enterprise with custom pricing. All plans include 24/7 support."
            ),
            token_count=35,
        )
    )
    
    # Refund Policy
    refund_doc = Document(
        id="doc_refund",
        organization_id=principal.organization_id,
        filename="refund_policy.md",
        title="Refund Policy",
        content_type="text/markdown",
        size_bytes=400,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(refund_doc)
    documents.append(refund_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_refund",
            organization_id=principal.organization_id,
            document_id=refund_doc.id,
            ordinal=0,
            section="Cancellation and Refunds",
            content=(
                "We offer a 30-day money-back guarantee. Cancel anytime and receive a full refund "
                "if you're not satisfied within the first 30 days."
            ),
            token_count=30,
        )
    )
    
    # Onboarding Guide
    onboarding_doc = Document(
        id="doc_onboarding",
        organization_id=principal.organization_id,
        filename="onboarding_guide.md",
        title="Onboarding Guide",
        content_type="text/markdown",
        size_bytes=700,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(onboarding_doc)
    documents.append(onboarding_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_onboarding",
            organization_id=principal.organization_id,
            document_id=onboarding_doc.id,
            ordinal=0,
            section="Getting Started",
            content=(
                "Onboarding with NovaEdge takes 2-3 weeks. We start with a kickoff call, followed by "
                "configuration, integration setup, and training. Our team supports you every step."
            ),
            token_count=35,
        )
    )
    
    # Escalation Policy
    escalation_doc = Document(
        id="doc_escalation",
        organization_id=principal.organization_id,
        filename="escalation_policy.md",
        title="Escalation Policy",
        content_type="text/markdown",
        size_bytes=500,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(escalation_doc)
    documents.append(escalation_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_escalation",
            organization_id=principal.organization_id,
            document_id=escalation_doc.id,
            ordinal=0,
            section="When to Escalate",
            content=(
                "Issues are escalated to senior support when: severity is critical, response time exceeds SLA, "
                "or the customer explicitly requests escalation. Urgent issues receive immediate attention."
            ),
            token_count=35,
        )
    )
    
    # Security Policy
    security_doc = Document(
        id="doc_security",
        organization_id=principal.organization_id,
        filename="security_policy.md",
        title="Security Policy",
        content_type="text/markdown",
        size_bytes=800,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(security_doc)
    documents.append(security_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_security",
            organization_id=principal.organization_id,
            document_id=security_doc.id,
            ordinal=0,
            section="Security Controls",
            content=(
                "NovaEdge implements enterprise-grade security controls including encryption at rest and in transit, "
                "role-based access control, regular security audits, and SOC 2 compliance."
            ),
            token_count=35,
        )
    )
    
    # Data Privacy Policy
    privacy_doc = Document(
        id="doc_privacy",
        organization_id=principal.organization_id,
        filename="data_privacy_policy.md",
        title="Data Privacy Policy",
        content_type="text/markdown",
        size_bytes=900,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(privacy_doc)
    documents.append(privacy_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_privacy",
            organization_id=principal.organization_id,
            document_id=privacy_doc.id,
            ordinal=0,
            section="Privacy and Data Protection",
            content=(
                "We are fully GDPR compliant. Your personal data is processed securely, never sold to third parties, "
                "and you have full control over your data including the right to export or delete it."
            ),
            token_count=40,
        )
    )
    
    # Customer FAQ
    faq_doc = Document(
        id="doc_faq",
        organization_id=principal.organization_id,
        filename="customer_faq.md",
        title="Customer FAQ",
        content_type="text/markdown",
        size_bytes=600,
        chunk_count=1,
        status="ready",
        source="test",
        uploaded_by=principal.user_id,
    )
    doc_repo.create(faq_doc)
    documents.append(faq_doc)
    
    chunks_to_create.append(
        DocumentChunk(
            id="chunk_faq",
            organization_id=principal.organization_id,
            document_id=faq_doc.id,
            ordinal=0,
            section="Frequently Asked Questions",
            content=(
                "Q: What services do you offer? A: Customer support automation, lead qualification, email workflows. "
                "Q: What integrations? A: HubSpot, Gmail, Google Calendar. Q: What's your pricing? A: Starting at $99/month."
            ),
            token_count=45,
        )
    )
    
    chunk_repo.bulk_create(chunks_to_create)
    db_session.commit()
    
    return documents


def _index_documents(
    db_session: Session,
    principal: Principal,
    documents: list[Document],
    fallback_embeddings: EmbeddingsProvider,
    memory_vector: MemoryVectorProvider,
) -> None:
    """Helper to index documents in vector store."""
    collection = f"documents_{principal.organization_id}"
    memory_vector.ensure_collection(collection, fallback_embeddings.dimension)
    
    chunk_repo = DocumentChunkRepository(db_session)
    all_chunks = []
    for doc in documents:
        chunks = chunk_repo.list_by_document(doc.id, organization_id=principal.organization_id)
        all_chunks.extend(chunks)
    
    texts = [chunk.content for chunk in all_chunks]
    vectors = fallback_embeddings.embed(texts)
    
    memory_vector.upsert(
        collection=collection,
        ids=[chunk.id for chunk in all_chunks],
        vectors=vectors,
        payloads=[
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "organization_id": principal.organization_id,
                "document_title": next(
                    (doc.title for doc in documents if doc.id == chunk.document_id),
                    "Unknown",
                ),
            }
            for chunk in all_chunks
        ],
    )


class TestMultiFacetRAG:
    """Test generalized multi-facet RAG retrieval."""

    def test_services_and_integrations(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
        comprehensive_docs: list[Document],
    ) -> None:
        """Test services + integrations compound query."""
        _index_documents(db_session, principal, comprehensive_docs, fallback_embeddings, memory_vector)
        
        outcome = rag_service.search(
            db_session,
            principal=principal,
            query="What services does NovaEdge Solutions offer and what integrations are supported?",
            top_k=5,
            settings=Settings(),
            embeddings=fallback_embeddings,
            vector=memory_vector,
            enforce_quota=False,
        )
        
        # Both Services Overview and Integration Guide should be in top 5
        titles = [hit.document_title for hit in outcome.hits]
        assert any("Services Overview" in title for title in titles)
        assert any("Integration Guide" in title for title in titles)
        
        # All scores should be <= 1.0
        for hit in outcome.hits:
            assert 0.0 <= hit.score <= 1.0

    def test_pricing_and_refunds(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
        comprehensive_docs: list[Document],
    ) -> None:
        """Test pricing + refunds compound query."""
        _index_documents(db_session, principal, comprehensive_docs, fallback_embeddings, memory_vector)
        
        outcome = rag_service.search(
            db_session,
            principal=principal,
            query="What are the pricing plans and refund policy?",
            top_k=5,
            settings=Settings(),
            embeddings=fallback_embeddings,
            vector=memory_vector,
            enforce_quota=False,
        )
        
        # Both Pricing Plans and Refund Policy should be in top 5
        titles = [hit.document_title for hit in outcome.hits]
        assert any("Pricing" in title for title in titles)
        assert any("Refund" in title for title in titles)
        
        # All scores normalized
        for hit in outcome.hits:
            assert 0.0 <= hit.score <= 1.0

    def test_onboarding_and_escalation(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
        comprehensive_docs: list[Document],
    ) -> None:
        """Test onboarding + escalation compound query."""
        _index_documents(db_session, principal, comprehensive_docs, fallback_embeddings, memory_vector)
        
        outcome = rag_service.search(
            db_session,
            principal=principal,
            query="How does onboarding work and when do you escalate issues?",
            top_k=5,
            settings=Settings(),
            embeddings=fallback_embeddings,
            vector=memory_vector,
            enforce_quota=False,
        )
        
        # Both Onboarding Guide and Escalation Policy should be in top 5
        titles = [hit.document_title for hit in outcome.hits]
        assert any("Onboarding" in title for title in titles)
        assert any("Escalation" in title for title in titles)
        
        # All scores normalized
        for hit in outcome.hits:
            assert 0.0 <= hit.score <= 1.0

    def test_security_and_privacy(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
        comprehensive_docs: list[Document],
    ) -> None:
        """Test security + privacy compound query."""
        _index_documents(db_session, principal, comprehensive_docs, fallback_embeddings, memory_vector)
        
        outcome = rag_service.search(
            db_session,
            principal=principal,
            query="What security controls and data privacy policies do you follow?",
            top_k=5,
            settings=Settings(),
            embeddings=fallback_embeddings,
            vector=memory_vector,
            enforce_quota=False,
        )
        
        # Both Security Policy and Data Privacy Policy should be in top 5
        titles = [hit.document_title for hit in outcome.hits]
        assert any("Security" in title for title in titles)
        assert any("Privacy" in title for title in titles)
        
        # All scores normalized
        for hit in outcome.hits:
            assert 0.0 <= hit.score <= 1.0

    def test_single_facet_services(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
        comprehensive_docs: list[Document],
    ) -> None:
        """Test single facet query: services only."""
        _index_documents(db_session, principal, comprehensive_docs, fallback_embeddings, memory_vector)
        
        outcome = rag_service.search(
            db_session,
            principal=principal,
            query="What services does NovaEdge offer?",
            top_k=5,
            settings=Settings(),
            embeddings=fallback_embeddings,
            vector=memory_vector,
            enforce_quota=False,
        )
        
        # Services Overview should be top result
        assert "Services Overview" in outcome.hits[0].document_title
        
        # All scores normalized
        for hit in outcome.hits:
            assert 0.0 <= hit.score <= 1.0

    def test_facet_downranking_services_query_excludes_privacy(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
        comprehensive_docs: list[Document],
    ) -> None:
        """Test that unrelated facets are downranked for services query."""
        _index_documents(db_session, principal, comprehensive_docs, fallback_embeddings, memory_vector)
        
        outcome = rag_service.search(
            db_session,
            principal=principal,
            query="What services does NovaEdge offer?",
            top_k=5,
            settings=Settings(),
            embeddings=fallback_embeddings,
            vector=memory_vector,
            enforce_quota=False,
        )
        
        # Privacy/Refund/Security should not dominate top 5
        titles = [hit.document_title for hit in outcome.hits[:5]]
        privacy_refund_security_count = sum(
            1 for title in titles if any(kw in title for kw in ["Privacy", "Refund", "Security"])
        )
        
        # At most 1 of these should appear in top 5 for a services query
        assert privacy_refund_security_count <= 1

    def test_score_normalization(
        self,
        db_session: Session,
        principal: Principal,
        fallback_embeddings: EmbeddingsProvider,
        memory_vector: MemoryVectorProvider,
        comprehensive_docs: list[Document],
    ) -> None:
        """Test that scores are always normalized to 0-1 range."""
        _index_documents(db_session, principal, comprehensive_docs, fallback_embeddings, memory_vector)
        
        # Test with high-boost query
        outcome = rag_service.search(
            db_session,
            principal=principal,
            query="services integrations HubSpot Gmail Calendar",
            top_k=10,
            settings=Settings(),
            embeddings=fallback_embeddings,
            vector=memory_vector,
            enforce_quota=False,
        )
        
        # All scores must be in valid range
        for hit in outcome.hits:
            assert 0.0 <= hit.score <= 1.0, f"Score {hit.score} out of range for {hit.document_title}"
