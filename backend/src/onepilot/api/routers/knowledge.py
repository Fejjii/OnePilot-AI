"""HTTP endpoints for knowledge search and grounded answers."""

from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession, SettingsDep
from onepilot.schemas.rag import (
    AnswerRequest,
    AnswerResponse,
    Citation,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from onepilot.security.permissions import require_member
from onepilot.services import rag_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/search", response_model=SearchResponse)
def search(
    body: SearchRequest,
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> SearchResponse:
    require_member(principal)
    outcome = rag_service.search(
        session,
        principal=principal,
        query=body.query,
        top_k=body.top_k,
        settings=settings,
    )
    return SearchResponse(
        query=outcome.query,
        results=[
            SearchResult(
                chunk_id=hit.chunk.id,
                document_id=hit.chunk.document_id,
                document_title=hit.document_title,
                section=hit.chunk.section,
                content=hit.chunk.content,
                score=hit.score,
                metadata=hit.chunk.chunk_metadata or {},
            )
            for hit in outcome.hits
        ],
        total_found=len(outcome.hits),
        weak_evidence=outcome.weak_evidence,
        fallback_used=outcome.fallback_used,
    )


@router.post("/answer", response_model=AnswerResponse)
def answer(
    body: AnswerRequest,
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> AnswerResponse:
    require_member(principal)
    outcome = rag_service.answer(
        session,
        principal=principal,
        query=body.query,
        top_k=body.top_k,
        settings=settings,
    )
    return AnswerResponse(
        query=outcome.query,
        answer=outcome.answer,
        confidence=outcome.confidence,
        citations=[
            Citation(
                chunk_id=hit.chunk.id,
                document_id=hit.chunk.document_id,
                document_title=hit.document_title,
                section=hit.chunk.section,
                score=hit.score,
            )
            for hit in outcome.hits
        ],
        weak_evidence=outcome.weak_evidence,
        fallback_used=outcome.fallback_used,
        model=outcome.model,
    )
