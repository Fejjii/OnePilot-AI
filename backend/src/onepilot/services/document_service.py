"""Document service: validate, parse, chunk, embed, persist, and audit."""

from __future__ import annotations

import time
from dataclasses import dataclass

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


def _embedding_fallback(embeddings: EmbeddingsProvider) -> bool:
    return "fallback" in type(embeddings).__name__.lower()


@dataclass(slots=True)
class UploadResult:
    document: Document
    chunk_count: int
    vector_upsert_count: int


def collection_name(organization_id: str) -> str:
    return f"{VECTOR_COLLECTION_PREFIX}{organization_id}"


def reindex_organization_documents(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
    embeddings: EmbeddingsProvider | None = None,
    vector: VectorProvider | None = None,
) -> int:
    """Rebuild the tenant's vector index from the persisted document chunks.

    This is used as a self-healing path when the vector collection exists but
    was created with a different embedding dimension.
    """
    embeddings = embeddings or get_embeddings_provider(settings)
    vector = vector or get_vector_provider(settings)

    doc_repo = DocumentRepository(session)
    docs = doc_repo.list_for_org(principal.organization_id, offset=0, limit=10_000)
    if not docs:
        return 0

    chunk_repo = DocumentChunkRepository(session)
    chunk_models: list[DocumentChunk] = []
    embed_inputs: list[str] = []
    payloads: list[dict] = []
    for doc in docs:
        for chunk in chunk_repo.list_by_document(doc.id, organization_id=principal.organization_id):
            chunk_models.append(chunk)
            embed_inputs.append(
                f"{chunk.section}\n\n{chunk.content}" if chunk.section else chunk.content
            )
            payloads.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_title": doc.title,
                    "section": chunk.section,
                    "organization_id": principal.organization_id,
                    "ordinal": chunk.ordinal,
                }
            )

    if not chunk_models:
        return 0

    started = time.monotonic()
    vectors = embeddings.embed(embed_inputs)
    embed_latency_ms = int((time.monotonic() - started) * 1000)

    collection = collection_name(principal.organization_id)
    vector.ensure_collection(collection, embeddings.dimension)
    upsert_count = vector.upsert(
        collection=collection,
        ids=[chunk.id for chunk in chunk_models],
        vectors=vectors,
        payloads=payloads,
    )

    session.commit()
    logger.warning(
        "knowledge_base_reindexed",
        organization_id=principal.organization_id,
        chunk_count=len(chunk_models),
        vector_upsert_count=upsert_count,
        latency_ms=embed_latency_ms,
    )
    return upsert_count


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
        ids=[c.id for c in chunk_models],
        vectors=vectors,
        payloads=[
            {
                "chunk_id": c.id,
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
