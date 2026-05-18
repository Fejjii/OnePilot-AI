"""Debug utility for RAG multi-facet retrieval.

Run this script to debug facet detection, retrieval, and reranking for a query.

Usage:
    python -m onepilot.debug.rag_debug "Your query here"
"""

from __future__ import annotations

import sys
from typing import Any

from onepilot.services.facets import (
    detect_facets,
    generate_facet_queries,
    calculate_facet_coverage,
    get_facet_coverage_ratio,
)


def debug_facet_detection(query: str) -> None:
    """Debug facet detection for a query."""
    print("\n" + "=" * 80)
    print("RAG MULTI-FACET DEBUG")
    print("=" * 80)
    print(f"\nQuery: {query}")
    print("\n" + "-" * 80)
    print("FACET DETECTION")
    print("-" * 80)
    
    facet_result = detect_facets(query)
    
    print(f"\nDetected Facets: {facet_result.detected_facets}")
    print(f"Is Compound: {facet_result.is_compound}")
    print("\nFacet Scores:")
    for facet, score in sorted(facet_result.facet_scores.items(), key=lambda x: x[1], reverse=True):
        if score > 0:
            print(f"  {facet}: {score:.3f}")
    
    print("\n" + "-" * 80)
    print("FACET QUERIES")
    print("-" * 80)
    
    facet_queries = generate_facet_queries(query, facet_result)
    for i, fq in enumerate(facet_queries, 1):
        print(f"\n{i}. Facet: {fq.facet}")
        print(f"   Weight: {fq.weight:.3f}")
        print(f"   Query: {fq.query_text}")
    
    print("\n" + "-" * 80)
    print("EXPECTED DOCUMENT BOOSTING")
    print("-" * 80)
    
    from onepilot.services.facets import get_facet_preferred_documents
    
    for facet in facet_result.detected_facets:
        preferred_docs = get_facet_preferred_documents(facet)
        print(f"\n{facet.upper()}:")
        print(f"  Preferred docs: {', '.join(preferred_docs[:5])}")
    
    print("\n" + "-" * 80)
    print("FACET MISMATCH DOWNRANKING")
    print("-" * 80)
    
    from onepilot.services.facets import should_downrank_document_for_query, FACET_DOCUMENT_MAPPING
    
    # Check which documents would be downranked
    all_facets = list(FACET_DOCUMENT_MAPPING.keys())
    unrelated_facets = [f for f in all_facets if f not in facet_result.detected_facets]
    
    print(f"\nUnrelated facets (will be downranked): {unrelated_facets}")
    
    # Sample document titles to check
    sample_titles = [
        "Services Overview",
        "Integration Guide",
        "Pricing Plans",
        "Refund Policy",
        "Data Privacy Policy",
        "Security Policy",
        "Onboarding Guide",
        "Escalation Policy",
        "Customer FAQ",
    ]
    
    print("\nDocument downranking simulation:")
    for title in sample_titles:
        should_downrank, reason = should_downrank_document_for_query(title, facet_result.detected_facets)
        status = f"DOWNRANKED (reason: {reason})" if should_downrank else "OK"
        print(f"  {title}: {status}")
    
    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80 + "\n")


def debug_with_mock_hits(query: str, mock_hits: list[dict[str, Any]]) -> None:
    """Debug facet coverage with mock hits.
    
    Args:
        query: The query string
        mock_hits: List of dicts with keys 'document_title' and 'rerank_score'
    """
    print("\n" + "=" * 80)
    print("FACET COVERAGE DEBUG")
    print("=" * 80)
    print(f"\nQuery: {query}")
    
    facet_result = detect_facets(query)
    
    print(f"\nDetected Facets: {facet_result.detected_facets}")
    print(f"Is Compound: {facet_result.is_compound}")
    
    # Create mock hit objects
    from dataclasses import dataclass
    
    @dataclass
    class MockHit:
        document_title: str
        rerank_score: float
    
    hits = [MockHit(h["document_title"], h["rerank_score"]) for h in mock_hits]
    
    print("\n" + "-" * 80)
    print("MOCK HITS")
    print("-" * 80)
    for i, hit in enumerate(hits, 1):
        print(f"{i}. {hit.document_title} (score: {hit.rerank_score:.3f})")
    
    print("\n" + "-" * 80)
    print("FACET COVERAGE ANALYSIS")
    print("-" * 80)
    
    coverage = calculate_facet_coverage(hits, facet_result.detected_facets, min_score_threshold=0.45)
    coverage_ratio = get_facet_coverage_ratio(coverage)
    
    print(f"\nCoverage by Facet:")
    for facet in facet_result.detected_facets:
        status = "✓ COVERED" if coverage.get(facet, False) else "✗ NOT COVERED"
        print(f"  {facet}: {status}")
    
    print(f"\nOverall Coverage Ratio: {coverage_ratio:.1%}")
    
    # Estimate confidence impact
    if coverage_ratio < 0.5:
        print("\nConfidence Impact: CAPPED AT 55% (< 50% coverage)")
    elif coverage_ratio < 0.67:
        print("\nConfidence Impact: CAPPED AT 65% (50-67% coverage)")
    elif coverage_ratio < 1.0:
        print("\nConfidence Impact: CAPPED AT 75% (67-99% coverage)")
    else:
        print("\nConfidence Impact: SLIGHT BOOST (100% coverage)")
    
    print("\n" + "=" * 80 + "\n")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m onepilot.debug.rag_debug \"Your query here\"")
        print("\nExample compound queries:")
        print('  "What services does NovaEdge offer and what integrations are supported?"')
        print('  "What are the pricing plans and refund policy?"')
        print('  "How does onboarding work and when do you escalate issues?"')
        print('  "What security controls and data privacy policies do you follow?"')
        sys.exit(1)
    
    query = sys.argv[1]
    debug_facet_detection(query)
    
    # Example: debug with mock hits
    if "--with-mock-hits" in sys.argv:
        mock_hits = [
            {"document_title": "Services Overview", "rerank_score": 0.92},
            {"document_title": "Customer FAQ", "rerank_score": 0.78},
            {"document_title": "Data Privacy Policy", "rerank_score": 0.65},
            {"document_title": "Company Profile", "rerank_score": 0.54},
            {"document_title": "Refund Policy", "rerank_score": 0.47},
        ]
        debug_with_mock_hits(query, mock_hits)


if __name__ == "__main__":
    main()
