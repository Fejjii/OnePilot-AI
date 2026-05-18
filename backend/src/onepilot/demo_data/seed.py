"""Seed a demo organization with the NovaEdge knowledge base.

The seeder is idempotent: re-running it does not duplicate documents.
Run it programmatically or via the `POST /demo/seed` API endpoint.

Deterministic demo identity
---------------------------
DEV_ORG_ID  = org_demo_onepilot   (set in .env / Settings)
DEV_USER_ID = usr_demo_admin       (set in .env / Settings)

Both the dev-auth bypass (no Bearer token) and the seed script resolve to the
same IDs, so /documents always returns the seeded content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.ids import new_id
from onepilot.core.logging import get_logger
from onepilot.providers import get_embeddings_provider, get_vector_provider
from onepilot.providers.embeddings.base import EmbeddingsProvider
from onepilot.providers.vector.base import VectorProvider
from onepilot.repositories.documents import DocumentChunkRepository, DocumentRepository
from onepilot.repositories.models import Organization, OrganizationMember, Subscription, User
from onepilot.repositories.organizations import OrganizationMemberRepository, OrganizationRepository
from onepilot.repositories.plans import SubscriptionRepository
from onepilot.repositories.users import UserRepository
from onepilot.security.auth import Principal, hash_password
from onepilot.services import document_service

logger = get_logger(__name__)

DEMO_EMAIL = "admin@onepilot.ai"
DEMO_PASSWORD = "Demo1234!"
DEMO_FULL_NAME = "Demo Admin"
DEMO_ORG_NAME = "OnePilot AI"
DEMO_ORG_SLUG = "onepilot-ai-demo"

NOVAEDGE_DOCS_DIR: Path = Path(__file__).resolve().parent / "novaedge_docs"


def ensure_demo_principal(session: Session, *, settings: Settings) -> Principal:
    """Upsert the demo org and user with deterministic IDs from settings.

    Idempotent: safe to call on every seed run.  Returns a Principal that
    matches DEV_ORG_ID / DEV_USER_ID so the dev-auth bypass and JWT tokens
    both resolve to the same tenant.
    """
    org_id = settings.DEV_ORG_ID
    user_id = settings.DEV_USER_ID

    org_repo = OrganizationRepository(session)
    if not org_repo.get(org_id):
        org_repo.create(
            Organization(id=org_id, name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG)
        )

    user_repo = UserRepository(session)
    if not user_repo.get(user_id):
        user_repo.create(
            User(
                id=user_id,
                email=DEMO_EMAIL,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=DEMO_FULL_NAME,
            )
        )

    member_repo = OrganizationMemberRepository(session)
    if not member_repo.get_membership(org_id, user_id):
        member_repo.create(
            OrganizationMember(
                id=new_id("mem"),
                organization_id=org_id,
                user_id=user_id,
                role=Role.OWNER,
            )
        )

    sub_repo = SubscriptionRepository(session)
    if not sub_repo.get_active(org_id):
        sub_repo.create(
            Subscription(
                id=new_id("sub"),
                organization_id=org_id,
                plan_code=PlanCode.BUSINESS,
                status="active",
            )
        )

    session.commit()

    logger.info(
        "demo_principal_ensured",
        org_id=org_id,
        user_id=user_id,
    )
    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.BUSINESS,
    )


@dataclass(slots=True)
class SeedResult:
    documents_created: int
    documents_skipped: int
    total_documents: int
    total_chunks: int
    vector_upsert_count: int


def seed_knowledge_base(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
    embeddings: EmbeddingsProvider | None = None,
    vector: VectorProvider | None = None,
    docs_dir: Path | None = None,
) -> SeedResult:
    """Ingest all NovaEdge markdown docs into the principal's organization.
    
    If documents already exist but vectors are missing (e.g., after switching
    embedding providers), this will automatically reindex all documents.
    """
    directory = docs_dir or NOVAEDGE_DOCS_DIR
    if not directory.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {directory}")

    embeddings = embeddings or get_embeddings_provider(settings)
    vector = vector or get_vector_provider(settings)
    
    # Log provider configuration for debugging
    from onepilot.providers.embeddings.openai_embeddings import OpenAIEmbeddingsProvider
    from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
    from onepilot.providers.llm.openai_provider import OpenAILLMProvider
    from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
    
    embeddings_provider_name = "openai" if isinstance(embeddings, OpenAIEmbeddingsProvider) else "fallback"
    embeddings_model = getattr(embeddings, "model", getattr(embeddings, "_default_model", "unknown"))
    
    logger.info(
        "seed_start",
        organization_id=principal.organization_id,
        embedding_provider=embeddings_provider_name,
        embedding_model=embeddings_model,
        embedding_dimension=embeddings.dimension,
        qdrant_collection=document_service.collection_name(principal.organization_id),
    )

    existing = {
        doc.filename
        for doc in DocumentRepository(session).list_for_org(
            principal.organization_id, offset=0, limit=500
        )
    }
    
    # Check if we need to reindex (documents exist but vectors are missing)
    doc_repo = DocumentRepository(session)
    chunk_repo = DocumentChunkRepository(session)
    existing_doc_count = doc_repo.count_for_org(principal.organization_id)
    needs_reindex = False
    
    if existing_doc_count > 0 and len(existing) > 0:
        # Count existing chunks
        total_chunk_count = sum(
            len(list(chunk_repo.list_by_document(doc.id, organization_id=principal.organization_id)))
            for doc in doc_repo.list_for_org(principal.organization_id, offset=0, limit=500)
        )
        
        # Ensure the collection exists before testing search
        collection = document_service.collection_name(principal.organization_id)
        vector.ensure_collection(collection, embeddings.dimension)
        
        logger.info(
            "seed_reindex_check",
            organization_id=principal.organization_id,
            embedding_provider=embeddings_provider_name,
            embedding_dimension=embeddings.dimension,
            vector_provider=type(vector).__name__,
            document_count=existing_doc_count,
            chunk_count=total_chunk_count,
        )
        
        # Test if vector search returns results
        try:
            from onepilot.services import rag_service
            test_outcome = rag_service.search(
                session,
                principal=principal,
                query="test query",
                top_k=1,
                settings=settings,
                embeddings=embeddings,
                vector=vector,
                enforce_quota=False,
            )
            test_search_result_count = len(test_outcome.hits)
            
            logger.info(
                "seed_reindex_test_search",
                organization_id=principal.organization_id,
                search_result_count=test_search_result_count,
                document_count=existing_doc_count,
                chunk_count=total_chunk_count,
            )
            
            if test_search_result_count == 0:
                logger.warning(
                    "seed_reindex_required",
                    reason="Documents exist in Postgres but vector search returns 0 results",
                    organization_id=principal.organization_id,
                    document_count=existing_doc_count,
                    chunk_count=total_chunk_count,
                    embedding_dimension=embeddings.dimension,
                )
                needs_reindex = True
        except Exception:
            logger.exception("seed_reindex_check_failed")
            needs_reindex = True
    
    # Reindex if needed (e.g., after provider change)
    reindex_upserts = 0
    if needs_reindex:
        logger.info(
            "seed_reindexing",
            organization_id=principal.organization_id,
            document_count=existing_doc_count,
        )
        reindex_upserts = document_service.reindex_organization_documents(
            session,
            principal=principal,
            settings=settings,
            embeddings=embeddings,
            vector=vector,
        )
        logger.info(
            "seed_reindex_complete",
            organization_id=principal.organization_id,
            vector_upsert_count=reindex_upserts,
        )

    created = 0
    skipped = 0
    total_chunks = 0
    total_vector_upserts = reindex_upserts
    for path in sorted(directory.glob("*.md")):
        if path.name in existing:
            skipped += 1
            continue
        content = path.read_bytes()
        try:
            upload_result = document_service.upload_document(
                session,
                principal=principal,
                filename=path.name,
                content_type="text/markdown",
                content=content,
                source="demo_seed",
                settings=settings,
                embeddings=embeddings,
                vector=vector,
                enforce_quota=False,
            )
            created += 1
            total_chunks += upload_result.chunk_count
            total_vector_upserts += upload_result.vector_upsert_count
        except Exception:
            # Undo the failed document's flush so the session is clean for the
            # next document.  Previously committed documents are unaffected.
            session.rollback()
            logger.exception("demo_seed_failed", filename=path.name)

    total_documents_in_db = doc_repo.count_for_org(principal.organization_id)
    
    # Count total chunks across all documents
    all_docs = doc_repo.list_for_org(principal.organization_id, offset=0, limit=500)
    final_chunk_count = sum(
        len(list(chunk_repo.list_by_document(doc.id, organization_id=principal.organization_id)))
        for doc in all_docs
    )
    
    # Ensure the collection exists with correct dimension before verification
    collection = document_service.collection_name(principal.organization_id)
    vector.ensure_collection(collection, embeddings.dimension)
    
    logger.info(
        "seed_verification_start",
        organization_id=principal.organization_id,
        embedding_provider=embeddings_provider_name,
        embedding_dimension=embeddings.dimension,
        vector_provider=type(vector).__name__,
        document_count=total_documents_in_db,
        chunk_count=final_chunk_count,
        total_vector_upserts=total_vector_upserts,
    )
    
    # Final verification: check that search returns results
    search_result_count = 0
    try:
        from onepilot.services import rag_service
        verify_outcome = rag_service.search(
            session,
            principal=principal,
            query="services integrations support",
            top_k=5,
            settings=settings,
            embeddings=embeddings,
            vector=vector,
            enforce_quota=False,
        )
        search_result_count = len(verify_outcome.hits)
        
        logger.info(
            "seed_verification_search_complete",
            organization_id=principal.organization_id,
            search_result_count=search_result_count,
            document_count=total_documents_in_db,
            chunk_count=final_chunk_count,
        )
    except Exception:
        logger.exception(
            "seed_verification_search_failed",
            organization_id=principal.organization_id,
            document_count=total_documents_in_db,
            chunk_count=final_chunk_count,
        )
    
    logger.info(
        "demo_seed_complete",
        organization_id=principal.organization_id,
        embedding_provider=embeddings_provider_name,
        embedding_model=embeddings_model,
        embedding_dimension=embeddings.dimension,
        created=created,
        skipped=skipped,
        reindexed=needs_reindex,
        total_documents=total_documents_in_db,
        total_chunks=total_chunks,
        total_vector_upserts=total_vector_upserts,
        search_result_count=search_result_count,
    )
    
    # Fail fast if verification shows problems
    if total_documents_in_db == 0:
        raise RuntimeError("Seed verification failed: document_count is 0")
    if total_chunks == 0 and created > 0:
        raise RuntimeError("Seed verification failed: chunk_count is 0 but documents were created")
    if total_vector_upserts == 0 and (created > 0 or needs_reindex):
        raise RuntimeError("Seed verification failed: vector_upsert_count is 0 but documents were created or reindexed")
    if search_result_count == 0 and total_documents_in_db > 0:
        raise RuntimeError(
            f"Seed verification failed: knowledge search returns 0 results but {total_documents_in_db} documents exist. "
            f"This indicates a vector index mismatch. Embedding dimension: {embeddings.dimension}"
        )
    
    return SeedResult(
        documents_created=created,
        documents_skipped=skipped,
        total_documents=total_documents_in_db,
        total_chunks=total_chunks,
        vector_upsert_count=total_vector_upserts,
    )
