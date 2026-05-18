"""HTTP endpoints for document management."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from onepilot.api.deps import CurrentPrincipal, DBSession, SettingsDep
from onepilot.schemas.documents import (
    DocumentChunkResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from onepilot.security.permissions import require_member
from onepilot.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
    file: UploadFile = File(...),
    source: str = Form(default="upload"),
) -> DocumentUploadResponse:
    require_member(principal)
    content = await file.read()
    result = document_service.upload_document(
        session,
        principal=principal,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        source=source,
        settings=settings,
    )
    return DocumentUploadResponse(
        id=result.document.id,
        filename=result.document.filename,
        title=result.document.title,
        content_type=result.document.content_type,
        size_bytes=result.document.size_bytes,
        chunk_count=result.chunk_count,
        status=result.document.status,
        created_at=result.document.created_at,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    principal: CurrentPrincipal,
    session: DBSession,
    offset: int = 0,
    limit: int = 50,
) -> DocumentListResponse:
    require_member(principal)
    items, total = document_service.list_documents(
        session, principal=principal, offset=offset, limit=min(limit, 100)
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: str,
    principal: CurrentPrincipal,
    session: DBSession,
    include_chunks: bool = False,
) -> DocumentDetailResponse:
    require_member(principal)
    document, chunks = document_service.get_document(
        session,
        principal=principal,
        document_id=document_id,
        include_chunks=include_chunks,
    )
    return DocumentDetailResponse(
        **DocumentResponse.model_validate(document).model_dump(),
        chunks=[DocumentChunkResponse.model_validate(c) for c in chunks],
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> None:
    require_member(principal)
    document_service.delete_document(
        session,
        principal=principal,
        document_id=document_id,
        settings=settings,
    )
