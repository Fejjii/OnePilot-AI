"""Query-aware reranking for RAG retrieval.

Combines vector similarity with keyword overlap, title matching, filename matching,
section matching, and document type boosting to improve retrieval quality.

Now supports generalized facet-aware boosting and downranking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from onepilot.repositories.models import DocumentChunk
from onepilot.services.facets import should_boost_document_for_facet, should_downrank_document_for_query

# Weights for different ranking signals (total should be ~1.0)
VECTOR_WEIGHT: float = 0.35
KEYWORD_WEIGHT: float = 0.15
TITLE_MATCH_WEIGHT: float = 0.20
FILENAME_MATCH_WEIGHT: float = 0.15
SECTION_MATCH_WEIGHT: float = 0.10
DOC_TYPE_WEIGHT: float = 0.05

# Document type boosts based on query patterns
HIGH_VALUE_TYPES = {
    "overview",
    "guide",
    "faq",
    "pricing",
    "services",
    "integration",
    "onboarding",
    "escalation",
    "customer",
}

# Hard downranking for irrelevant documents (deprecated - now using facet-aware downranking)
# Kept for _doc_type_score backward compatibility
IRRELEVANT_TYPES = {
    "template",
    "policy",
    "privacy",
    "security",
    "refund",
    "legal",
    "terms",
    "meeting",
    "notes",
    "internal",
    "sample",
}


@dataclass(slots=True)
class RerankHit:
    chunk: DocumentChunk
    document_title: str
    vector_score: float
    rerank_score: float
    signals: dict[str, float]


def _normalize_text(text: str) -> str:
    """Normalize text for matching: lowercase, remove punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_singular_plural(word: str) -> str:
    """Normalize word to handle singular/plural variations.
    
    Examples:
        services -> service
        integrations -> integration
        offerings -> offering
    """
    # Simple heuristic: remove trailing 's' for common plural forms
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"  # policies -> policy
    if word.endswith("es") and len(word) > 3:
        return word[:-2]  # services -> servic (will also match service)
    if word.endswith("s") and len(word) > 3:
        return word[:-1]  # integrations -> integration
    return word


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text (words >= 3 chars).
    
    Returns both original and singular/plural normalized forms.
    """
    normalized = _normalize_text(text)
    words = {word for word in normalized.split() if len(word) >= 3}
    
    # Add singular/plural variations
    variations = set()
    for word in words:
        variations.add(word)
        variations.add(_normalize_singular_plural(word))
    
    return variations


def _keyword_overlap_score(query: str, text: str) -> float:
    """Calculate keyword overlap score using Jaccard similarity."""
    query_words = _extract_keywords(query)
    text_words = _extract_keywords(text)
    if not query_words:
        return 0.0
    intersection = query_words & text_words
    union = query_words | text_words
    if not union:
        return 0.0
    return len(intersection) / len(union)


def _title_match_score(query: str, title: str) -> float:
    """Score based on query-title matching.
    
    Gives high scores when document title contains key query terms.
    """
    query_norm = _normalize_text(query)
    title_norm = _normalize_text(title)
    
    # Extract key terms from query (words >= 4 chars, excluding common words)
    common_words = {"what", "how", "when", "where", "does", "are", "the", "and", "for", "with"}
    query_keywords = _extract_keywords(query) - common_words
    title_keywords = _extract_keywords(title)
    
    # Exact phrase match in title
    if query_norm in title_norm:
        return 1.0
    if title_norm in query_norm:
        return 0.95
    
    # Check if main query terms appear in title
    if query_keywords:
        matches = query_keywords & title_keywords
        match_ratio = len(matches) / len(query_keywords)
        
        # High score if most query terms are in title
        if match_ratio >= 0.7:
            return 0.9
        elif match_ratio >= 0.5:
            return 0.75
        elif match_ratio >= 0.3:
            return 0.5
        else:
            return match_ratio
    
    # Fallback to keyword overlap
    return _keyword_overlap_score(query, title) * 0.8


def _filename_match_score(query: str, title: str) -> float:
    """Score based on query-filename matching."""
    # Extract filename-like words from title
    title_norm = _normalize_text(title)
    query_norm = _normalize_text(query)
    
    # Check if key query terms appear in the title
    query_keywords = _extract_keywords(query)
    title_keywords = _extract_keywords(title)
    
    if not query_keywords:
        return 0.0
    
    matches = query_keywords & title_keywords
    return len(matches) / len(query_keywords)


def _section_match_score(query: str, section: str | None) -> float:
    """Score based on query-section matching."""
    if not section:
        return 0.0
    
    section_norm = _normalize_text(section)
    query_norm = _normalize_text(query)
    
    # Exact match
    if query_norm in section_norm or section_norm in query_norm:
        return 1.0
    
    # Keyword overlap
    return _keyword_overlap_score(query, section)


def _doc_type_score(query: str, title: str) -> float:
    """Score based on document type relevance to query.
    
    Returns:
        1.0 for high-value matches
        0.5 for neutral documents
        0.3 for potentially irrelevant (but not completely eliminated)
    
    Note: This is now supplemented by facet-aware downranking in the rerank function.
    """
    query_norm = _normalize_text(query)
    title_norm = _normalize_text(title)
    
    # Check if document is high-value type
    for doc_type in HIGH_VALUE_TYPES:
        if doc_type in title_norm:
            return 1.0
    
    # Check if document might be irrelevant type
    for doc_type in IRRELEVANT_TYPES:
        if doc_type in title_norm:
            # Soft downrank unless query explicitly asks for it
            if doc_type in query_norm:
                return 1.0  # User explicitly asked for this
            return 0.3  # Potentially irrelevant (facet downranking will handle this better)
    
    return 0.5


def _facet_aware_boost(document_title: str, detected_facets: list[str]) -> float:
    """Calculate boost multiplier based on facet alignment.
    
    Returns a boost multiplier (1.0 = no boost, up to 2.5 for strong matches).
    
    Args:
        document_title: The document title
        detected_facets: List of facets detected in the query
    
    Returns:
        Boost multiplier
    """
    if not detected_facets:
        return 1.0
    
    boost = 1.0
    
    # Check if document is strongly relevant to any detected facet
    for facet in detected_facets:
        if should_boost_document_for_facet(document_title, facet):
            # Strong match to a query facet - apply strong boost
            boost *= 2.5
            break  # Only apply boost once
    
    return boost


def _facet_aware_downrank(document_title: str, detected_facets: list[str]) -> float:
    """Calculate downrank penalty based on facet mismatch.
    
    Returns a penalty multiplier (1.0 = no penalty, < 1.0 for mismatch).
    
    Args:
        document_title: The document title
        detected_facets: List of facets detected in the query
    
    Returns:
        Penalty multiplier (0.4 to 1.0)
    """
    should_downrank, mismatched_facet = should_downrank_document_for_query(
        document_title, detected_facets
    )
    
    if should_downrank:
        # Document strongly matches an unrelated facet - apply penalty
        return 0.4  # Significant penalty but not complete elimination
    
    return 1.0


def rerank(
    query: str,
    hits: list[tuple[DocumentChunk, float, str]],
    detected_facets: list[str] | None = None,
) -> list[RerankHit]:
    """Rerank search hits using query-aware scoring with facet awareness.
    
    Args:
        query: The search query
        hits: List of (chunk, vector_score, document_title) tuples
        detected_facets: Optional list of detected facets for facet-aware boosting/downranking
    
    Returns:
        List of RerankHit objects sorted by rerank_score (descending)
    """
    if not hits:
        return []
    
    detected_facets = detected_facets or []
    reranked: list[RerankHit] = []
    
    for chunk, vector_score, document_title in hits:
        # Calculate individual signals
        keyword_score = _keyword_overlap_score(query, chunk.content)
        title_score = _title_match_score(query, document_title)
        filename_score = _filename_match_score(query, document_title)
        section_score = _section_match_score(query, chunk.section)
        doc_type_score = _doc_type_score(query, document_title)
        
        # Calculate weighted base score
        base_score = (
            vector_score * VECTOR_WEIGHT
            + keyword_score * KEYWORD_WEIGHT
            + title_score * TITLE_MATCH_WEIGHT
            + filename_score * FILENAME_MATCH_WEIGHT
            + section_score * SECTION_MATCH_WEIGHT
            + doc_type_score * DOC_TYPE_WEIGHT
        )
        
        # Apply facet-aware boost
        boost = _facet_aware_boost(document_title, detected_facets)
        
        # Apply facet-aware downrank penalty
        downrank_penalty = _facet_aware_downrank(document_title, detected_facets)
        
        # Combine boost and penalty
        rerank_score = base_score * boost * downrank_penalty
        
        reranked.append(
            RerankHit(
                chunk=chunk,
                document_title=document_title,
                vector_score=vector_score,
                rerank_score=rerank_score,
                signals={
                    "vector": vector_score,
                    "keyword": keyword_score,
                    "title": title_score,
                    "filename": filename_score,
                    "section": section_score,
                    "doc_type": doc_type_score,
                    "boost": boost,
                    "downrank_penalty": downrank_penalty,
                },
            )
        )
    
    # Sort by rerank score (descending)
    reranked.sort(key=lambda h: h.rerank_score, reverse=True)
    return reranked
