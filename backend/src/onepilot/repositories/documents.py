"""Repositories for documents and their chunks."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import Document, DocumentChunk


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Document)

    def list_for_org(
        self,
        organization_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.organization_id == organization_id)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def count_for_org(self, organization_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.organization_id == organization_id)
        )
        return self._session.execute(stmt).scalar() or 0


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DocumentChunk)

    def bulk_create(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        self._session.add_all(chunks)
        self._session.flush()

    def list_by_document(self, document_id: str, *, organization_id: str) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.organization_id == organization_id,
            )
            .order_by(DocumentChunk.ordinal.asc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_many(
        self,
        chunk_ids: list[str],
        *,
        organization_id: str,
    ) -> list[DocumentChunk]:
        if not chunk_ids:
            return []
        stmt = select(DocumentChunk).where(
            DocumentChunk.id.in_(chunk_ids),
            DocumentChunk.organization_id == organization_id,
        )
        return list(self._session.execute(stmt).scalars().all())

    def delete_by_document(self, document_id: str, *, organization_id: str) -> int:
        stmt = delete(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.organization_id == organization_id,
        )
        result = self._session.execute(stmt)
        return result.rowcount or 0
