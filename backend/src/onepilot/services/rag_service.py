"""Retrieval-augmented generation service.

Search returns the top-K chunks scoped to the caller's tenant.
Answer assembles a grounded reply with citations. If retrieval evidence is weak
we **do not** ask the LLM to answer; instead, we return a deterministic grounded
answer or the configured weak-evidence message so the agent never invents an
answer that is not grounded in the knowledge base.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import LanguageCode, UsageFeature
from onepilot.services import i18n_messages
from onepilot.services.language_service import (
    build_english_retrieval_queries,
    cap_confidence_for_weak_evidence,
    detect_language_heuristic,
    language_display_name,
    response_language_instruction,
)
from onepilot.core.errors import ProviderUnavailableError
from onepilot.core.logging import get_logger
from onepilot.providers import (
    get_embeddings_provider,
    get_llm_provider,
    get_vector_provider,
)
from onepilot.providers.embeddings.base import EmbeddingsProvider
from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
from onepilot.providers.llm.base import LLMProvider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.providers.vector.base import VectorProvider
from onepilot.repositories.documents import DocumentChunkRepository
from onepilot.repositories.models import DocumentChunk
from onepilot.security.auth import Principal
from onepilot.services import audit_service, document_service, quota_service, usage_service
from onepilot.services.confidence import calculate_confidence, is_weak_evidence
from onepilot.services.fallback_answer import synthesize_answer
from onepilot.services.facets import detect_facets, generate_facet_queries
from onepilot.services.reranker import rerank

logger = get_logger(__name__)

WEAK_EVIDENCE_ANSWER: str = (
    "I don't have a confident answer based on the knowledge I have. "
    "I'm forwarding this to a human teammate."
)
MAX_CONTEXT_CHARS: int = 4_000


@dataclass(slots=True)
class SearchHit:
    chunk: DocumentChunk
    score: float
    document_title: str
    vector_score: float
    signals: dict[str, float]


@dataclass(slots=True)
class SearchOutcome:
    query: str
    hits: list[SearchHit]
    weak_evidence: bool
    fallback_used: bool


@dataclass(slots=True)
class AnswerOutcome:
    query: str
    answer: str
    confidence: float
    hits: list[SearchHit]
    weak_evidence: bool
    fallback_used: bool
    model: str


def _embedding_fallback(embeddings: EmbeddingsProvider) -> bool:
    return isinstance(embeddings, FallbackEmbeddingsProvider)


def _llm_fallback(llm: LLMProvider) -> bool:
    return isinstance(llm, FallbackLLMProvider)


def _is_dimension_mismatch_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "dimension",
            "vector size",
            "expected size",
            "size mismatch",
            "does not match the size",
        )
    )


def _balance_facet_coverage(
    reranked: list[Any], detected_facets: list[str], target_k: int
) -> list[Any]:
    """Balance top-k results to ensure coverage of multiple facets.
    
    For compound queries, ensure that top-k results include at least one
    strong source for each detected facet when possible. Prioritizes
    facet-specific documents over generic ones.
    
    Args:
        reranked: List of RerankHit objects sorted by score
        detected_facets: List of detected facet names
        target_k: Target number of results
    
    Returns:
        Balanced list of RerankHit objects (length target_k)
    """
    from onepilot.services.facets import should_boost_document_for_facet
    
    if not detected_facets or len(detected_facets) <= 1:
        return reranked[:target_k]
    
    # Track which facets are covered in current selection
    selected: list[Any] = []
    covered_facets: set[str] = set()
    remaining = list(reranked)
    
    # Phase 1: Select the BEST source for each uncovered facet
    # This ensures we get strong facet-specific documents in top results
    for facet in detected_facets:
        if len(selected) >= target_k:
            break
        
        # Find best candidate for this facet that hasn't been selected yet
        best_idx = -1
        best_score = -1.0
        
        for idx, hit in enumerate(remaining):
            if should_boost_document_for_facet(hit.document_title, facet):
                # Prefer this candidate if:
                # 1. It has higher score, OR
                # 2. It's the first match for this facet
                if hit.rerank_score > best_score or best_idx == -1:
                    best_score = hit.rerank_score
                    best_idx = idx
        
        if best_idx >= 0:
            selected.append(remaining.pop(best_idx))
            covered_facets.add(facet)
    
    # Phase 2: Fill remaining slots with highest-scoring candidates
    # Sort remaining by score and add until we reach target_k
    remaining.sort(key=lambda h: h.rerank_score, reverse=True)
    while len(selected) < target_k and remaining:
        selected.append(remaining.pop(0))
    
    # Sort final selection by score (descending)
    selected.sort(key=lambda h: h.rerank_score, reverse=True)
    
    return selected


def _compute_candidate_balance_weights(
    facet_result: Any, candidates_by_facet: dict[str, int]
) -> dict[str, float]:
    """Compute balanced retrieval weights for each facet to prevent one facet from dominating.
    
    Args:
        facet_result: FacetDetectionResult
        candidates_by_facet: Dict mapping facet name to candidate count
    
    Returns:
        Dict mapping facet name to weight multiplier
    """
    if not facet_result.is_compound:
        return {f: 1.0 for f in candidates_by_facet}
    
    # For compound queries, balance candidate counts
    weights: dict[str, float] = {}
    total_candidates = sum(candidates_by_facet.values())
    
    if total_candidates == 0:
        return {f: 1.0 for f in candidates_by_facet}
    
    target_per_facet = total_candidates / len(candidates_by_facet)
    
    for facet, count in candidates_by_facet.items():
        if count > target_per_facet * 1.5:
            # Too many candidates from this facet - downweight slightly
            weights[facet] = 0.9
        elif count < target_per_facet * 0.5:
            # Too few candidates from this facet - upweight slightly
            weights[facet] = 1.1
        else:
            weights[facet] = 1.0
    
    return weights


def search(
    session: Session,
    *,
    principal: Principal,
    query: str,
    top_k: int = 5,
    settings: Settings,
    embeddings: EmbeddingsProvider | None = None,
    vector: VectorProvider | None = None,
    enforce_quota: bool = True,
    supplemental_queries: list[str] | None = None,
) -> SearchOutcome:
    if enforce_quota:
        quota_service.check_and_increment(
            session,
            principal.organization_id,
            UsageFeature.RAG_QUERIES,
            amount=1,
        )

    embeddings = embeddings or get_embeddings_provider(settings)
    vector = vector or get_vector_provider(settings)

    collection = document_service.collection_name(principal.organization_id)
    vector.ensure_collection(collection, embeddings.dimension)

    started = time.monotonic()

    if supplemental_queries is None:
        lang_guess = detect_language_heuristic(query)
        if lang_guess.language != LanguageCode.EN:
            supplemental_queries = build_english_retrieval_queries(
                query, lang_guess.language
            )

    # Detect query facets using generalized facet detection
    facet_result = detect_facets(query)
    facet_queries = generate_facet_queries(query, facet_result, include_general=True)
    
    logger.info(
        "rag_search_facet_detection",
        organization_id=principal.organization_id,
        query=query,
        detected_facets=facet_result.detected_facets,
        is_compound=facet_result.is_compound,
        num_facet_queries=len(facet_queries),
    )
    
    # Retrieve candidates for each facet
    all_raw_results: dict[str, list] = {}
    seen_chunk_ids: set[str] = set()
    candidates_by_facet: dict[str, int] = {}
    
    all_retrieval_queries: list[tuple[str, str]] = [
        (facet_query.facet, facet_query.query_text) for facet_query in facet_queries
    ]
    for idx, extra_query in enumerate(supplemental_queries or []):
        if extra_query.strip():
            all_retrieval_queries.append((f"supplemental_{idx}", extra_query))

    for facet_name, query_text in all_retrieval_queries:
        try:
            query_vector = embeddings.embed_query(query_text)
        except NotImplementedError as exc:
            logger.warning(
                "rag_embeddings_fallback",
                organization_id=principal.organization_id,
                provider=type(embeddings).__name__,
                error=str(exc),
            )
            embeddings = FallbackEmbeddingsProvider()
            query_vector = embeddings.embed_query(query_text)

        # For compound queries, retrieve more candidates per facet
        facet_top_k = top_k * 2 if facet_result.is_compound else top_k
        
        try:
            raw_results = vector.search(
                collection=collection,
                vector=query_vector,
                top_k=facet_top_k,
                filters={"organization_id": principal.organization_id},
            )
        except Exception as exc:
            if _is_dimension_mismatch_error(exc):
                logger.warning(
                    "rag_vector_dimension_mismatch",
                    organization_id=principal.organization_id,
                    collection=collection,
                    error=str(exc),
                )
                document_service.reindex_organization_documents(
                    session,
                    principal=principal,
                    settings=settings,
                    embeddings=embeddings,
                    vector=vector,
                )
                raw_results = vector.search(
                    collection=collection,
                    vector=query_vector,
                    top_k=facet_top_k,
                    filters={"organization_id": principal.organization_id},
                )
            else:
                logger.exception(
                    "rag_search_failed",
                    organization_id=principal.organization_id,
                    collection=collection,
                    error=str(exc),
                )
                raise ProviderUnavailableError(f"Knowledge search failed: {exc}") from exc
        
        all_raw_results[facet_name] = raw_results
        seen_chunk_ids.update(r.id for r in raw_results)
        candidates_by_facet[facet_name] = len(raw_results)
    
    latency_ms = int((time.monotonic() - started) * 1000)

    # Fetch all unique chunks
    chunk_ids = list(seen_chunk_ids)
    chunk_repo = DocumentChunkRepository(session)
    chunks_by_id = {
        c.id: c
        for c in chunk_repo.get_many(chunk_ids, organization_id=principal.organization_id)
    }

    # Compute balance weights for facets
    balance_weights = _compute_candidate_balance_weights(facet_result, candidates_by_facet)
    
    # Merge results from all facet queries, deduplicating by chunk_id
    # For each chunk, keep the best (weighted) score across all facets
    merged_results: dict[str, tuple[float, str, str]] = {}  # chunk_id -> (best_score, document_title, source_facet)
    
    for facet_name, raw_results in all_raw_results.items():
        weight = balance_weights.get(facet_name, 1.0)
        
        for r in raw_results:
            chunk = chunks_by_id.get(r.id)
            if not chunk:
                continue
            document_title = str(r.payload.get("document_title") or chunk.section or "Document")
            
            # Apply balance weight to score
            weighted_score = r.score * weight
            
            # Keep the highest weighted score if chunk appears in multiple facet queries
            if r.id not in merged_results or weighted_score > merged_results[r.id][0]:
                merged_results[r.id] = (weighted_score, document_title, facet_name)
    
    # Prepare hits for reranking
    raw_hits: list[tuple[DocumentChunk, float, str]] = [
        (chunks_by_id[chunk_id], score, title)
        for chunk_id, (score, title, source_facet) in merged_results.items()
        if chunk_id in chunks_by_id
    ]
    
    logger.info(
        "rag_search_candidates",
        organization_id=principal.organization_id,
        total_candidates=len(raw_hits),
        unique_documents=len(set(h[2] for h in raw_hits)),
        facets=facet_result.detected_facets,
    )

    # Rerank using query-aware scoring with facet context
    # Pass facet information to reranker for facet-aware boosting and downranking
    reranked = rerank(query, raw_hits, detected_facets=facet_result.detected_facets)
    
    # For compound queries, ensure balanced facet coverage in top_k
    # Apply stronger boosting before balanced selection
    if facet_result.is_compound and len(reranked) > 0:
        # Apply extra boost to ensure facet-specific docs are highly ranked
        from onepilot.services.facets import should_boost_document_for_facet
        
        for hit in reranked:
            for facet in facet_result.detected_facets:
                if should_boost_document_for_facet(hit.document_title, facet):
                    # Extra boost for compound queries to ensure coverage
                    hit.rerank_score *= 1.3
                    break
        
        # Re-sort after applying extra boost
        reranked.sort(key=lambda h: h.rerank_score, reverse=True)
    
    if facet_result.is_compound and len(reranked) > top_k:
        # Use balanced reranking to ensure coverage of multiple facets
        reranked = _balance_facet_coverage(reranked, facet_result.detected_facets, top_k)
    else:
        # Take only top_k after reranking
        reranked = reranked[:top_k]

    # Normalize scores to 0-1 range to prevent >100% display in UI
    # Find max score and scale all scores proportionally if needed
    if reranked:
        max_score = max(rh.rerank_score for rh in reranked)
        if max_score > 1.0:
            # Scale down all scores proportionally
            scale_factor = 1.0 / max_score
            for rh in reranked:
                rh.rerank_score = min(rh.rerank_score * scale_factor, 1.0)
    
    # Convert to SearchHit objects
    hits: list[SearchHit] = [
        SearchHit(
            chunk=rh.chunk,
            score=rh.rerank_score,
            document_title=rh.document_title,
            vector_score=rh.vector_score,
            signals=rh.signals,
        )
        for rh in reranked
    ]

    weak_evidence = is_weak_evidence(reranked)
    fallback_used = _embedding_fallback(embeddings)

    embed_tokens = max(1, len(query) // 4)
    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=UsageFeature.RAG_QUERIES.value,
        model=getattr(embeddings, "model", None),
        provider=type(embeddings).__name__,
        fallback_used=fallback_used,
        embedding_tokens=embed_tokens,
        latency_ms=latency_ms,
        metadata={
            "top_k": top_k,
            "weak_evidence": weak_evidence,
            "hit_count": len(hits),
        },
    )
    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="knowledge.searched",
        resource_type="knowledge_query",
        resource_id=f"search_{int(time.time() * 1000)}",
        detail={"query_length": len(query), "hit_count": len(hits)},
    )
    session.commit()

    logger.info(
        "rag_search",
        organization_id=principal.organization_id,
        hit_count=len(hits),
        weak_evidence=weak_evidence,
        fallback_used=fallback_used,
    )
    return SearchOutcome(
        query=query,
        hits=hits,
        weak_evidence=weak_evidence,
        fallback_used=fallback_used,
    )


def _build_context(hits: list[SearchHit]) -> str:
    parts: list[str] = []
    total = 0
    for hit in hits:
        snippet = hit.chunk.content.strip()
        if total + len(snippet) > MAX_CONTEXT_CHARS:
            snippet = snippet[: MAX_CONTEXT_CHARS - total]
        section = f" — {hit.chunk.section}" if hit.chunk.section else ""
        parts.append(f"[{hit.document_title}{section}]\n{snippet}")
        total += len(snippet)
        if total >= MAX_CONTEXT_CHARS:
            break
    return "\n\n".join(parts)


def _hits_to_rerank(hits: list[SearchHit]) -> list:
    from onepilot.services.reranker import RerankHit

    return [
        RerankHit(
            chunk=h.chunk,
            document_title=h.document_title,
            vector_score=h.vector_score,
            rerank_score=h.score,
            signals=h.signals,
        )
        for h in hits
    ]


def _merge_search_hits(primary: SearchOutcome, secondary: SearchOutcome, top_k: int) -> SearchOutcome:
    """Merge hits from a secondary search into the primary outcome and re-evaluate evidence."""
    seen: set[str] = {h.chunk.id for h in primary.hits}
    merged = list(primary.hits)
    for hit in secondary.hits:
        if hit.chunk.id in seen:
            continue
        seen.add(hit.chunk.id)
        merged.append(hit)
    merged.sort(key=lambda h: h.score, reverse=True)
    merged = merged[:top_k]
    reranked = _hits_to_rerank(merged)
    return SearchOutcome(
        query=primary.query,
        hits=merged,
        weak_evidence=is_weak_evidence(reranked),
        fallback_used=primary.fallback_used or secondary.fallback_used,
    )


def answer(
    session: Session,
    *,
    principal: Principal,
    query: str,
    top_k: int = 5,
    settings: Settings,
    embeddings: EmbeddingsProvider | None = None,
    vector: VectorProvider | None = None,
    llm: LLMProvider | None = None,
    response_language: str = "en",
    detected_language: str | None = None,
) -> AnswerOutcome:
    det = detected_language or response_language
    try:
        det_code = LanguageCode(str(det).lower())
    except ValueError:
        det_code = LanguageCode.EN

    supplemental: list[str] | None = None
    if det_code != LanguageCode.EN:
        supplemental = build_english_retrieval_queries(query, det_code)

    outcome = search(
        session,
        principal=principal,
        query=query,
        top_k=top_k,
        settings=settings,
        embeddings=embeddings,
        vector=vector,
        supplemental_queries=supplemental,
    )

    if outcome.weak_evidence:
        audit_service.record(
            session,
            organization_id=principal.organization_id,
            user_id=principal.user_id,
            action="knowledge.answered",
            resource_type="knowledge_query",
            resource_id=f"answer_{int(time.time() * 1000)}",
            detail={"weak_evidence": True, "hit_count": len(outcome.hits)},
        )
        session.commit()
        
        rerank_hits = _hits_to_rerank(outcome.hits)

        try:
            resp_lang = LanguageCode(str(response_language).lower())
        except ValueError:
            resp_lang = LanguageCode.EN
        weak_msg = i18n_messages.get_message(i18n_messages.RAG_WEAK_EVIDENCE, resp_lang)

        raw_confidence = calculate_confidence(rerank_hits, query) if rerank_hits else 0.0
        return AnswerOutcome(
            query=query,
            answer=weak_msg,
            confidence=cap_confidence_for_weak_evidence(
                raw_confidence, weak_evidence=True
            ),
            hits=outcome.hits,
            weak_evidence=True,
            fallback_used=outcome.fallback_used,
            model="weak-evidence-guard",
        )

    llm = llm or get_llm_provider(settings)
    llm_fallback = _llm_fallback(llm)

    context = _build_context(outcome.hits)
    try:
        resp_lang = LanguageCode(str(response_language).lower())
    except ValueError:
        resp_lang = LanguageCode.EN
    lang_instruction = response_language_instruction(resp_lang)
    answer_lang = language_display_name(resp_lang)
    messages = [
        {
            "role": "system",
            "content": (
                "You are the NovaEdge knowledge assistant. Answer using ONLY the provided "
                "context. Do not invent information. If the context is insufficient, say so "
                "in the requested response language. Cite source document titles in brackets "
                "exactly as they appear in the context — never translate document or section "
                f"names. {lang_instruction}\n\n"
                "Format the answer exactly with these markdown sections:\n"
                "## Summary\n"
                "(1-2 short sentences maximum)\n"
                "## Key points\n"
                "(3-5 concise bullet points)\n"
                "## Evidence or sources\n"
                "(brief citations with document titles from context; do not invent sources)\n"
                "## Suggested next action\n"
                "(one sentence only)"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question: {query}\n\nContext:\n{context}\n\n"
                f"Write a grounded answer in {answer_lang} using only the context above. "
                "Use the required section headings. Keep each section concise. Include "
                "bracketed citations with original document titles from the context."
            ),
        },
    ]

    started = time.monotonic()
    try:
        response = llm.chat(messages, temperature=0.2, max_tokens=512)
    except NotImplementedError as exc:
        logger.warning(
            "rag_llm_fallback",
            organization_id=principal.organization_id,
            provider=type(llm).__name__,
            error=str(exc),
        )
        llm = FallbackLLMProvider()
        response = llm.chat(messages, temperature=0.2, max_tokens=512)
    except Exception as exc:
        logger.exception(
            "rag_answer_failed",
            organization_id=principal.organization_id,
            error=str(exc),
        )
        raise ProviderUnavailableError(f"Knowledge answer failed: {exc}") from exc
    latency_ms = int((time.monotonic() - started) * 1000)

    if llm_fallback:
        # Convert hits to rerank format for synthesis
        from onepilot.services.reranker import RerankHit
        rerank_hits = [
            RerankHit(
                chunk=h.chunk,
                document_title=h.document_title,
                vector_score=h.vector_score,
                rerank_score=h.score,
                signals=h.signals,
            )
            for h in outcome.hits
        ]
        answer_text = synthesize_answer(
            query, rerank_hits, response_language=resp_lang.value
        )
        
        # If synthesize_answer returned weak evidence message, mark as weak
        if answer_text == WEAK_EVIDENCE_ANSWER:
            audit_service.record(
                session,
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                action="knowledge.answered",
                resource_type="knowledge_query",
                resource_id=f"answer_{int(time.time() * 1000)}",
                detail={"weak_evidence": True, "hit_count": len(outcome.hits), "source": "synthesize_fallback"},
            )
            session.commit()
            
            raw_confidence = calculate_confidence(rerank_hits, query) if rerank_hits else 0.0
            return AnswerOutcome(
                query=query,
                answer=answer_text,
                confidence=cap_confidence_for_weak_evidence(
                    raw_confidence, weak_evidence=True
                ),
                hits=outcome.hits,
                weak_evidence=True,
                fallback_used=outcome.fallback_used or llm_fallback,
                model="weak-evidence-guard",
            )
    else:
        answer_text = response.content.strip() or WEAK_EVIDENCE_ANSWER

    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=UsageFeature.CHAT_MESSAGES.value,
        model=response.model,
        provider=type(llm).__name__,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        fallback_used=llm_fallback,
        latency_ms=latency_ms,
        metadata={
            "rag": True,
            "hit_count": len(outcome.hits),
            "detected_language": det_code.value,
            "response_language": resp_lang.value,
        },
    )
    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="knowledge.answered",
        resource_type="knowledge_query",
        resource_id=f"answer_{int(time.time() * 1000)}",
        detail={
            "weak_evidence": False,
            "hit_count": len(outcome.hits),
            "model": response.model,
            "fallback_used": llm_fallback,
        },
    )
    session.commit()

    rerank_hits = _hits_to_rerank(outcome.hits)
    confidence = calculate_confidence(rerank_hits, query)
    
    return AnswerOutcome(
        query=query,
        answer=answer_text,
        confidence=confidence,
        hits=outcome.hits,
        weak_evidence=False,
        fallback_used=outcome.fallback_used or llm_fallback,
        model=response.model,
    )
