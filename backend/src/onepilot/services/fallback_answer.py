"""Fallback answer synthesis for deterministic RAG responses.

When LLM is unavailable, synthesizes grounded answers from retrieved chunks
instead of returning vague placeholder text.
"""

from __future__ import annotations

from onepilot.services.reranker import RerankHit

# Minimum relevance threshold for using chunks in answers
# Aligned with weak evidence detection to prevent inconsistencies
MIN_RELEVANCE_THRESHOLD: float = 0.35


def synthesize_answer(
    query: str,
    hits: list[RerankHit],
    max_length: int = 500,
    min_relevance: float = MIN_RELEVANCE_THRESHOLD,
) -> str:
    """Synthesize a deterministic answer from retrieved chunks.
    
    Creates a grounded summary by:
    1. Filtering out low-relevance chunks (below min_relevance)
    2. Extracting the most relevant sentences from high-quality chunks
    3. Citing document titles
    4. Combining into a coherent summary
    
    Args:
        query: The original query
        hits: List of reranked search hits
        max_length: Maximum answer length in characters
        min_relevance: Minimum rerank score to use chunk (default 0.45)
    
    Returns:
        Synthesized answer with citations
    """
    if not hits:
        return (
            "I don't have a confident answer based on the knowledge I have. "
            "I'm forwarding this to a human teammate."
        )
    
    # Filter hits by relevance threshold
    relevant_hits = [h for h in hits if h.rerank_score >= min_relevance]
    
    if not relevant_hits:
        return (
            "I don't have a confident answer based on the knowledge I have. "
            "I'm forwarding this to a human teammate."
        )
    
    # Extract unique document titles for citation (only from relevant hits)
    unique_titles = list({hit.document_title for hit in relevant_hits[:3]})
    citation_text = ", ".join(unique_titles)
    
    # Build answer from relevant chunks only
    answer_parts: list[str] = []
    total_chars = 0
    
    for hit in relevant_hits[:3]:  # Only use top 3 relevant hits
        # Split chunk into sentences
        content = hit.chunk.content.strip()
        sentences = _split_sentences(content)
        
        # Take most relevant sentences
        for sentence in sentences[:2]:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short fragments
                continue
            
            if total_chars + len(sentence) > max_length:
                break
            
            answer_parts.append(sentence)
            total_chars += len(sentence)
        
        if total_chars >= max_length:
            break
    
    if not answer_parts:
        # Fallback: use first relevant chunk's first sentence
        first_content = relevant_hits[0].chunk.content.strip()
        sentences = _split_sentences(first_content)
        if sentences:
            answer_parts.append(sentences[0])
    
    # Combine into answer with citation
    answer_text = " ".join(answer_parts)
    
    # Add citation prefix
    if len(unique_titles) == 1:
        citation_prefix = f"Based on {unique_titles[0]}: "
    else:
        citation_prefix = f"Based on the knowledge base ({citation_text}): "
    
    # Ensure answer doesn't exceed max length
    max_answer_len = max_length - len(citation_prefix)
    if len(answer_text) > max_answer_len:
        answer_text = answer_text[:max_answer_len].rsplit(" ", 1)[0] + "..."
    
    return citation_prefix + answer_text


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences.
    
    Simple sentence splitter that handles common punctuation.
    """
    import re
    
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter out empty or very short fragments
    return [s.strip() for s in sentences if s.strip()]


def extract_key_points(hits: list[RerankHit], max_points: int = 5) -> list[str]:
    """Extract key points from retrieved chunks.
    
    Useful for structured responses or bullet-point summaries.
    
    Args:
        hits: List of reranked search hits
        max_points: Maximum number of points to extract
    
    Returns:
        List of key point strings
    """
    points: list[str] = []
    
    for hit in hits:
        content = hit.chunk.content.strip()
        sentences = _split_sentences(content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30:  # Skip very short fragments
                continue
            
            # Prefer sentences that look like key points
            # (start with numbers, bullets, or key terms)
            if _looks_like_key_point(sentence):
                points.append(sentence)
                if len(points) >= max_points:
                    return points
    
    return points


def _looks_like_key_point(sentence: str) -> bool:
    """Check if sentence looks like a key point or important fact."""
    sentence_lower = sentence.lower()
    
    # Starts with bullet or number
    if sentence[0] in "•-*123456789":
        return True
    
    # Contains key indicator words
    indicators = [
        "include",
        "includes",
        "offer",
        "offers",
        "provide",
        "provides",
        "support",
        "supports",
        "integrate",
        "integrates",
        "cost",
        "costs",
        "price",
    ]
    
    if any(ind in sentence_lower for ind in indicators):
        return True
    
    return False
