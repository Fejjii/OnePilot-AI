"""Document service: validate, parse, chunk, embed, persist, and audit."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import UsageFeature
from onepilot.core.errors import NotFoundError, ValidationError
from onepilot.core.ids import new_id
from onepilot.core.logging import get_logger
from onepilot.providers import get_embeddings_provider, get_vector_provider
from onepilot.providers.embeddings.base import EmbeddingsProvider
from onepilot.providers.vector.base import VectorProvider
from onepilot.repositories.documents import DocumentChunkRepository, DocumentRepository
from onepilot.repositories.models import Document, DocumentChunk
from onepilot.security.auth import Principal
from onepilot.security.file_validation import validate_file
from onepilot.services import (
    audit_service,
    chunking_service,
    ingestion_service,
    quota_service,
    usage_service,
)

logger = get_logger(__name__)

VECTOR_COLLECTION_PREFIX: str = "documents_"
_STABLE_ID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def stable_chunk_id(organization_id: str, document_id: str, ordinal: int) -> str:
    """Deterministic chunk primary key for idempotent reindex rebuilds."""
    digest = uuid.uuid5(
        _STABLE_ID_NAMESPACE,
        f"chunk:{organization_id}:{document_id}:{ordinal}",
    )
    return f"chunk_{digest.hex[:26]}"


def stable_vector_point_id(organization_id: str, document_id: str, ordinal: int) -> str:
    """Deterministic vector point id (organization, document, chunk ordinal)."""
    return str(
        uuid.uuid5(
            _STABLE_ID_NAMESPACE,
            f"vector:{organization_id}:{document_id}:{ordinal}",
        )
    )


def _embedding_fallback(embeddings: EmbeddingsProvider) -> bool:
    return "fallback" in type(embeddings).__name__.lower()


@dataclass(slots=True)
class UploadResult:
    document: Document
    chunk_count: int
    vector_upsert_count: int


@dataclass(slots=True)
class ReindexResult:
    documents_seen: int
    documents_created: int
    documents_skipped: int
    chunks_created: int
    chunks_reindexed: int
    vector_upserts: int
    qdrant_collection: str
    provider_mode: str
    qdrant_configured: bool
    sample_search_hits: int


def collection_name(organization_id: str) -> str:
    return f"{VECTOR_COLLECTION_PREFIX}{organization_id}"


def _vector_provider_mode(settings: Settings, vector: VectorProvider) -> str:
    if settings.has_qdrant and "qdrant" in type(vector).__name__.lower():
        return "qdrant"
    return "memory"


def _rebuild_document_chunks(
    session: Session,
    *,
    principal: Principal,
    document: Document,
    content: bytes,
    chunk_repo: DocumentChunkRepository,
    doc_repo: DocumentRepository,
) -> list[DocumentChunk]:
    """Replace chunks for a document using deterministic chunk ids."""
    chunk_repo.delete_by_document(document.id, organization_id=principal.organization_id)
    title, text = ingestion_service.load_document(content, document.filename, document.content_type)
    chunks = chunking_service.chunk_text(text)
    if not chunks:
        raise ValidationError(f"Document '{document.filename}' produced no chunks")

    chunk_models: list[DocumentChunk] = []
    for chunk in chunks:
        chunk_models.append(
            DocumentChunk(
                id=stable_chunk_id(principal.organization_id, document.id, chunk.ordinal),
                organization_id=principal.organization_id,
                document_id=document.id,
                ordinal=chunk.ordinal,
                section=chunk.section,
                content=chunk.content,
                token_count=chunk.token_count,
                chunk_metadata={
                    "document_title": title,
                    "filename": document.filename,
                    "section": chunk.section,
                },
            )
        )

    chunk_repo.bulk_create(chunk_models)
    doc_repo.update(
        document,
        {"title": title, "chunk_count": len(chunk_models)},
    )
    return chunk_models


def _upsert_chunks_to_vector(
    *,
    principal: Principal,
    document: Document,
    chunk_models: list[DocumentChunk],
    embeddings: EmbeddingsProvider,
    vector: VectorProvider,
) -> int:
    embed_inputs = [
        f"{c.section}\n\n{c.content}" if c.section else c.content for c in chunk_models
    ]
    vectors = embeddings.embed(embed_inputs)
    collection = collection_name(principal.organization_id)
    vector.ensure_collection(collection, embeddings.dimension)
    return vector.upsert(
        collection=collection,
        ids=[
            stable_vector_point_id(principal.organization_id, document.id, c.ordinal)
            for c in chunk_models
        ],
        vectors=vectors,
        payloads=[
            {
                "chunk_id": c.id,
                "chunk_ulid": c.id,
                "document_id": document.id,
                "document_title": document.title,
                "section": c.section,
                "organization_id": principal.organization_id,
                "ordinal": c.ordinal,
            }
            for c in chunk_models
        ],
    )


def reindex_organization_documents(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
    embeddings: EmbeddingsProvider | None = None,
    vector: VectorProvider | None = None,
    source_dir: Path | None = None,
    rebuild_missing_chunks: bool = True,
) -> int:
    """Rebuild the tenant's vector index from persisted (or rebuilt) document chunks."""
    result = reindex_knowledge_base(
        session,
        principal=principal,
        settings=settings,
        embeddings=embeddings,
        vector=vector,
        source_dir=source_dir,
        rebuild_missing_chunks=rebuild_missing_chunks,
    )
    return result.vector_upserts


def reindex_knowledge_base(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
    embeddings: EmbeddingsProvider | None = None,
    vector: VectorProvider | None = None,
    source_dir: Path | None = None,
    rebuild_missing_chunks: bool = True,
) -> ReindexResult:
    """Reindex all knowledge-base documents for a tenant without duplicating documents."""
    embeddings = embeddings or get_embeddings_provider(settings)
    vector = vector or get_vector_provider(settings)
    collection = collection_name(principal.organization_id)

    doc_repo = DocumentRepository(session)
    chunk_repo = DocumentChunkRepository(session)
    docs = doc_repo.list_for_org(principal.organization_id, offset=0, limit=10_000)

    chunks_created = 0
    chunks_reindexed = 0
    vector_upserts = 0
    started = time.monotonic()

    for doc in docs:
        chunk_models = chunk_repo.list_by_document(
            doc.id, organization_id=principal.organization_id
        )
        if not chunk_models and rebuild_missing_chunks and source_dir is not None:
            source_path = source_dir / doc.filename
            if not source_path.is_file():
                logger.warning(
                    "reindex_missing_source",
                    organization_id=principal.organization_id,
                    document_id=doc.id,
                    filename=doc.filename,
                )
                continue
            chunk_models = _rebuild_document_chunks(
                session,
                principal=principal,
                document=doc,
                content=source_path.read_bytes(),
                chunk_repo=chunk_repo,
                doc_repo=doc_repo,
            )
            chunks_created += len(chunk_models)
        elif chunk_models:
            chunks_reindexed += len(chunk_models)
        else:
            logger.warning(
                "reindex_no_chunks",
                organization_id=principal.organization_id,
                document_id=doc.id,
                filename=doc.filename,
            )
            continue

        vector_upserts += _upsert_chunks_to_vector(
            principal=principal,
            document=doc,
            chunk_models=chunk_models,
            embeddings=embeddings,
            vector=vector,
        )

    session.commit()
    embed_latency_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "knowledge_base_reindexed",
        organization_id=principal.organization_id,
        documents_seen=len(docs),
        chunks_created=chunks_created,
        chunks_reindexed=chunks_reindexed,
        vector_upsert_count=vector_upserts,
        latency_ms=embed_latency_ms,
        provider_mode=_vector_provider_mode(settings, vector),
    )

    sample_hits = 0
    if vector_upserts > 0:
        from onepilot.services import rag_service

        try:
            outcome = rag_service.search(
                session,
                principal=principal,
                query="NovaEdge services integrations HubSpot Gmail Calendar",
                top_k=3,
                settings=settings,
                embeddings=embeddings,
                vector=vector,
                enforce_quota=False,
            )
            sample_hits = len(outcome.hits)
        except Exception:
            logger.exception("reindex_sample_search_failed")

    return ReindexResult(
        documents_seen=len(docs),
        documents_created=0,
        documents_skipped=len(docs),
        chunks_created=chunks_created,
        chunks_reindexed=chunks_reindexed,
        vector_upserts=vector_upserts,
        qdrant_collection=collection,
        provider_mode=_vector_provider_mode(settings, vector),
        qdrant_configured=settings.has_qdrant,
        sample_search_hits=sample_hits,
    )


def upload_document(
    session: Session,
    *,
    principal: Principal,
    filename: str,
    content_type: str,
    content: bytes,
    source: str = "upload",
    settings: Settings,
    embeddings: EmbeddingsProvider | None = None,
    vector: VectorProvider | None = None,
    enforce_quota: bool = True,
) -> UploadResult:
    """Upload, chunk, embed, and persist a document for the current tenant."""
    validation = validate_file(filename, content_type, len(content))
    if not validation.valid:
        raise ValidationError("; ".join(validation.errors))

    if enforce_quota:
        quota_service.check_and_increment(
            session,
            principal.organization_id,
            UsageFeature.DOCUMENT_UPLOADS,
            amount=1,
        )

    embeddings = embeddings or get_embeddings_provider(settings)
    vector = vector or get_vector_provider(settings)

    title, text = ingestion_service.load_document(content, filename, content_type)
    chunks = chunking_service.chunk_text(text)
    if not chunks:
        raise ValidationError("Document produced no chunks")

    document = Document(
        id=new_id("doc"),
        organization_id=principal.organization_id,
        filename=filename,
        title=title,
        content_type=content_type,
        size_bytes=len(content),
        chunk_count=len(chunks),
        status="ready",
        source=source,
        uploaded_by=principal.user_id,
        doc_metadata={"original_filename": filename},
    )
    doc_repo = DocumentRepository(session)
    doc_repo.create(document)

    chunk_models: list[DocumentChunk] = []
    for chunk in chunks:
        chunk_models.append(
            DocumentChunk(
                id=new_id("chunk"),
                organization_id=principal.organization_id,
                document_id=document.id,
                ordinal=chunk.ordinal,
                section=chunk.section,
                content=chunk.content,
                token_count=chunk.token_count,
                chunk_metadata={
                    "document_title": title,
                    "filename": filename,
                    "section": chunk.section,
                },
            )
        )

    chunk_repo = DocumentChunkRepository(session)
    chunk_repo.bulk_create(chunk_models)

    started = time.monotonic()
    embed_inputs = [
        f"{c.section}\n\n{c.content}" if c.section else c.content for c in chunk_models
    ]
    vectors = embeddings.embed(embed_inputs)
    embed_latency_ms = int((time.monotonic() - started) * 1000)

    vector.ensure_collection(collection_name(principal.organization_id), embeddings.dimension)
    upsert_count = vector.upsert(
        collection=collection_name(principal.organization_id),
        ids=[
            stable_vector_point_id(principal.organization_id, document.id, c.ordinal)
            for c in chunk_models
        ],
        vectors=vectors,
        payloads=[
            {
                "chunk_id": c.id,
                "chunk_ulid": c.id,
                "document_id": document.id,
                "document_title": title,
                "section": c.section,
                "organization_id": principal.organization_id,
                "ordinal": c.ordinal,
            }
            for c in chunk_models
        ],
    )

    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="document.uploaded",
        resource_type="document",
        resource_id=document.id,
        detail={"title": title, "chunk_count": len(chunk_models), "size_bytes": len(content)},
    )
    embed_tokens = sum(c.token_count for c in chunks)
    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=UsageFeature.DOCUMENT_UPLOADS.value,
        model=getattr(embeddings, "model", None),
        provider=type(embeddings).__name__,
        embedding_tokens=embed_tokens,
        fallback_used=_embedding_fallback(embeddings),
        latency_ms=embed_latency_ms,
        metadata={"document_id": document.id, "chunks": len(chunks)},
    )

    session.commit()
    session.refresh(document)
    logger.info(
        "document_uploaded",
        document_id=document.id,
        organization_id=principal.organization_id,
        chunk_count=len(chunks),
    )
    return UploadResult(document=document, chunk_count=len(chunks), vector_upsert_count=upsert_count)


def list_documents(
    session: Session,
    *,
    principal: Principal,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Document], int]:
    repo = DocumentRepository(session)
    items = repo.list_for_org(principal.organization_id, offset=offset, limit=limit)
    total = repo.count_for_org(principal.organization_id)
    return items, total


def get_document(
    session: Session,
    *,
    principal: Principal,
    document_id: str,
    include_chunks: bool = False,
) -> tuple[Document, list[DocumentChunk]]:
    doc_repo = DocumentRepository(session)
    document = doc_repo.get(document_id, organization_id=principal.organization_id)
    if not document:
        raise NotFoundError(f"Document '{document_id}' not found")

    chunks: list[DocumentChunk] = []
    if include_chunks:
        chunk_repo = DocumentChunkRepository(session)
        chunks = chunk_repo.list_by_document(
            document_id, organization_id=principal.organization_id
        )
    return document, chunks


def delete_document(
    session: Session,
    *,
    principal: Principal,
    document_id: str,
    settings: Settings,
    vector: VectorProvider | None = None,
) -> None:
    doc_repo = DocumentRepository(session)
    document = doc_repo.get(document_id, organization_id=principal.organization_id)
    if not document:
        raise NotFoundError(f"Document '{document_id}' not found")

    chunk_repo = DocumentChunkRepository(session)
    chunks = chunk_repo.list_by_document(
        document_id, organization_id=principal.organization_id
    )
    chunk_ids = [c.id for c in chunks]

    vector = vector or get_vector_provider(settings)
    if chunk_ids:
        try:
            vector.delete(collection_name(principal.organization_id), chunk_ids)
        except Exception as exc:  # pragma: no cover - best-effort vector cleanup
            logger.warning(
                "vector_delete_failed",
                document_id=document_id,
                error=str(exc),
            )

    doc_repo.delete(document)

    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="document.deleted",
        resource_type="document",
        resource_id=document_id,
        detail={"chunk_count": len(chunk_ids)},
    )
    session.commit()
    logger.info(
        "document_deleted",
        document_id=document_id,
        organization_id=principal.organization_id,
    )
