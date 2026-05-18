"""Confidence scoring for RAG answers.

Calculates answer confidence based on multiple signals:
- Number of relevant sources
- Top source score
- Title and keyword match quality
- Citation coverage
- Weak evidence detection
- Generalized facet coverage (handles any compound query type)
"""

from __future__ import annotations

from onepilot.services.facets import (
    calculate_facet_coverage,
    detect_facets,
    get_facet_coverage_ratio,
)
from onepilot.services.reranker import RerankHit

MIN_CONFIDENCE: float = 0.0
MAX_CONFIDENCE: float = 1.0

# Thresholds
STRONG_SOURCE_THRESHOLD: float = 0.60
MODERATE_SOURCE_THRESHOLD: float = 0.40
MIN_SOURCES_FOR_CONFIDENCE: int = 2
MIN_RELEVANCE_THRESHOLD: float = 0.45  # Same as fallback_answer

# Weights for confidence components
TOP_SCORE_WEIGHT: float = 0.35
SOURCE_COUNT_WEIGHT: float = 0.25
AVG_SCORE_WEIGHT: float = 0.20
TITLE_MATCH_WEIGHT: float = 0.15
KEYWORD_MATCH_WEIGHT: float = 0.05


def calculate_confidence(hits: list[RerankHit], query: str) -> float:
    """Calculate answer confidence from reranked hits.
    
    For compound queries (e.g., "services AND integrations"), confidence is
    capped if facet coverage is incomplete.
    
    Args:
        hits: List of reranked search hits
        query: The original query
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not hits:
        return 0.0
    
    # Detect facets using generalized facet detection
    facet_result = detect_facets(query)
    facet_coverage = calculate_facet_coverage(
        hits, facet_result.detected_facets, MIN_RELEVANCE_THRESHOLD
    )
    coverage_ratio = get_facet_coverage_ratio(facet_coverage)
    
    # Component 1: Top score (normalized to 0-1)
    top_score = min(hits[0].rerank_score, 1.0)
    
    # Component 2: Source count score (only count relevant sources)
    relevant_count = len([h for h in hits if h.rerank_score >= MIN_RELEVANCE_THRESHOLD])
    if relevant_count >= 5:
        source_count_score = 1.0
    elif relevant_count >= 3:
        source_count_score = 0.9
    elif relevant_count >= 2:
        source_count_score = 0.7
    else:
        source_count_score = 0.5
    
    # Component 3: Average score of top relevant sources
    relevant_hits = [h for h in hits[:5] if h.rerank_score >= MIN_RELEVANCE_THRESHOLD]
    if relevant_hits:
        top_n = min(3, len(relevant_hits))
        avg_top_score = sum(h.rerank_score for h in relevant_hits[:top_n]) / top_n
        avg_top_score = min(avg_top_score, 1.0)
    else:
        avg_top_score = 0.0
    
    # Component 4: Title match quality
    title_match_score = 0.0
    max_title_signal = 0.0
    for hit in hits[:3]:
        if hit.rerank_score < MIN_RELEVANCE_THRESHOLD:
            continue
        title_signal = hit.signals.get("title", 0.0)
        max_title_signal = max(max_title_signal, title_signal)
        if title_signal > 0.6:
            title_match_score = 1.0
            break
        elif title_signal > 0.3:
            title_match_score = max(title_match_score, 0.8)
        elif title_signal > 0.15:
            title_match_score = max(title_match_score, 0.5)
    
    # Component 5: Keyword match quality
    keyword_match_score = 0.0
    max_keyword_signal = 0.0
    for hit in hits[:3]:
        if hit.rerank_score < MIN_RELEVANCE_THRESHOLD:
            continue
        keyword_signal = hit.signals.get("keyword", 0.0)
        max_keyword_signal = max(max_keyword_signal, keyword_signal)
        if keyword_signal > 0.4:
            keyword_match_score = 1.0
            break
        elif keyword_signal > 0.2:
            keyword_match_score = max(keyword_match_score, 0.7)
    
    # Calculate weighted confidence
    confidence = (
        top_score * TOP_SCORE_WEIGHT
        + source_count_score * SOURCE_COUNT_WEIGHT
        + avg_top_score * AVG_SCORE_WEIGHT
        + title_match_score * TITLE_MATCH_WEIGHT
        + keyword_match_score * KEYWORD_MATCH_WEIGHT
    )
    
    # Apply penalties for weak evidence BEFORE boosts
    if top_score < 0.25:
        confidence *= 0.6
    elif top_score < 0.35:
        confidence *= 0.85
    
    # Boost for strong title/keyword matches (indicates relevant sources)
    if max_title_signal > 0.4 or max_keyword_signal > 0.3:
        if relevant_count >= 3:
            confidence *= 1.2
        elif relevant_count >= 2:
            confidence *= 1.15
    
    # Extra boost when both title and keyword matches are strong
    if max_title_signal > 0.3 and max_keyword_signal > 0.2 and relevant_count >= 2:
        confidence *= 1.1
    
    # Boost for metadata alignment (check boost signal)
    max_boost = max(
        (h.signals.get("boost", 1.0) for h in hits[:3] if h.rerank_score >= MIN_RELEVANCE_THRESHOLD),
        default=1.0
    )
    if max_boost > 1.2:  # Strong metadata alignment
        confidence *= 1.12
    
    # Boost for strong evidence
    if top_score > 0.7 and relevant_count >= 3:
        confidence *= 1.1
    
    # Cap at 1.0 BEFORE applying facet coverage and relevance caps
    confidence = min(confidence, 1.0)
    
    # Hard cap: confidence should never exceed 0.90 unless truly exceptional
    if confidence > 0.90:
        exceptional = (
            top_score > 0.80
            and len(highly_relevant := [h for h in hits[:5] if h.rerank_score >= 0.70]) >= 3
            and max_title_signal > 0.7
            and max_keyword_signal > 0.5
        )
        if not exceptional:
            confidence = 0.90
    
    # Apply facet coverage penalty for compound queries
    if facet_result.is_compound and len(facet_result.detected_facets) >= 2:
        if coverage_ratio < 0.5:
            # Less than half of facets covered - significant penalty
            confidence = min(confidence, 0.55)
        elif coverage_ratio < 0.67:
            # 50-67% coverage - moderate penalty
            confidence = min(confidence, 0.65)
        elif coverage_ratio < 1.0:
            # 67-99% coverage - slight penalty
            confidence = min(confidence, 0.75)
        else:
            # Full coverage - slight boost
            if confidence < 0.90:
                confidence = min(confidence * 1.05, 0.90)
    
    # Cap confidence if irrelevant sources dominate top results
    irrelevant_in_top_3 = sum(
        1 for h in hits[:3]
        if h.rerank_score < MIN_RELEVANCE_THRESHOLD or h.signals.get("doc_type", 0.5) < 0.3
    )
    if irrelevant_in_top_3 >= 2:
        confidence = min(confidence, 0.60)
    
    # High confidence (>80%) requires at least 2 highly relevant sources
    highly_relevant_final = [h for h in hits[:3] if h.rerank_score >= 0.70]
    if confidence > 0.80 and len(highly_relevant_final) < 2:
        confidence = min(confidence, 0.80)
    
    return max(MIN_CONFIDENCE, min(confidence, MAX_CONFIDENCE))


def is_weak_evidence(hits: list[RerankHit]) -> bool:
    """Determine if evidence is too weak to answer confidently.
    
    Args:
        hits: List of reranked search hits
    
    Returns:
        True if evidence is weak, False otherwise
    """
    if not hits:
        return True
    
    top_score = hits[0].rerank_score
    
    # Very weak top score
    if top_score < 0.28:
        return True
    
    # Weak top score with insufficient sources
    if top_score < 0.35 and len(hits) < MIN_SOURCES_FOR_CONFIDENCE:
        return True
    
    return False


def get_citation_coverage(answer: str, hits: list[RerankHit]) -> float:
    """Calculate what percentage of sources are cited in the answer.
    
    Args:
        answer: The generated answer text
        hits: List of reranked search hits
    
    Returns:
        Citation coverage ratio (0.0 to 1.0)
    """
    if not hits:
        return 0.0
    
    cited_count = 0
    answer_lower = answer.lower()
    
    for hit in hits:
        title_lower = hit.document_title.lower()
        # Check if title or key terms appear in answer
        if title_lower in answer_lower:
            cited_count += 1
            continue
        
        # Check if section is cited
        if hit.chunk.section:
            section_lower = hit.chunk.section.lower()
            if section_lower in answer_lower:
                cited_count += 1
                continue
    
    return cited_count / len(hits)
