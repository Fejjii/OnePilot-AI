"""Query facet detection and metadata mapping for multi-facet RAG retrieval.

This module provides:
1. Facet detection: Identify semantic facets in queries (services, integrations, pricing, etc.)
2. Facet metadata mapping: Map facets to preferred document titles/filenames
3. Facet query expansion: Generate facet-specific retrieval queries
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Facet keyword definitions with synonyms and variations
FACET_KEYWORDS: dict[str, set[str]] = {
    "services": {
        "service",
        "servic",  # matches services, servicing
        "offer",
        "offering",
        "package",
        "automation",
        "automat",  # matches automations, automated
        "feature",
        "featur",  # matches features
        "capability",
        "capabilit",  # matches capabilities
        "provide",
        "provid",  # matches provides, providing
    },
    "integrations": {
        "integration",
        "integrat",  # matches integrations, integrate
        "connect",
        "connector",
        "hubspot",
        "crm",
        "gmail",
        "google",
        "calendar",
        "slack",
        "supported",
        "support",  # matches supports (in context of platforms)
    },
    "pricing": {
        "price",
        "pricing",
        "plan",
        "plans",
        "cost",
        "subscription",
        "fee",
        "payment",
        "bill",
        "billing",
    },
    "refunds": {
        "refund",
        "refunds",
        "cancellation",
        "cancel",
        "money back",
        "return",
        "reimburse",
        "policy",  # Added to catch "refund policy"
    },
    "onboarding": {
        "onboard",
        "onboarding",
        "implementation",
        "setup",
        "kickoff",
        "start",
        "getting started",
        "begin",
        "configure",
        "configuration",
    },
    "support": {
        "support",
        "troubleshooting",
        "troubleshoot",
        "issue",
        "ticket",
        "response time",
        "help",
        "assist",
    },
    "escalation": {
        "escalate",
        "escalation",
        "escalated",
        "urgent",
        "severity",
        "priority",
        "critical",
        "emergency",
        "issue",  # Added to catch "escalate issues"
    },
    "security": {
        "security",
        "secure",
        "access control",
        "encryption",
        "audit",
        "authentication",
    },
    "privacy": {
        "privacy",
        "gdpr",
        "personal data",
        "data processing",
        "compliance",
        "regulation",
    },
    "email": {
        "email",
        "inbox",
        "gmail",
        "follow up",
        "sequence",
        "message",
        "correspondence",
    },
    "crm": {
        "crm",
        "customer relationship",
        "lead",
        "contact",
        "hubspot",
        "salesforce",
    },
    "calendar": {
        "calendar",
        "appointment",
        "booking",
        "schedule",
        "scheduling",
        "meeting",
    },
    "lead_qualification": {
        "lead",
        "prospect",
        "qualification",
        "qualify",
        "scoring",
    },
    "appointments": {
        "appointment",
        "booking",
        "schedule",
        "calendar",
        "meeting",
        "demo call",
    },
}

# Facet to document title/filename mapping
# Maps each facet to preferred document titles/filenames/sections
FACET_DOCUMENT_MAPPING: dict[str, list[str]] = {
    "services": [
        "services_overview",
        "service overview",
        "services overview",
        "company_profile",
        "company profile",
        "customer_faq",
        "customer faq",
        "pricing_plans",
        "pricing plans",
    ],
    "integrations": [
        "integration_guide",
        "integration guide",
        "hubspot",
        "gmail",
        "google_calendar",
        "google calendar",
        "crm",
        "calendar",
    ],
    "pricing": [
        "pricing_plans",
        "pricing plans",
        "customer_faq",
        "customer faq",
    ],
    "refunds": [
        "refund_policy",
        "refund policy",
        "customer_faq",
        "customer faq",
    ],
    "onboarding": [
        "onboarding_guide",
        "onboarding guide",
        "demo_call_checklist",
        "demo call checklist",
        "discovery_call_script",
        "discovery call script",
    ],
    "support": [
        "support_troubleshooting",
        "support troubleshooting",
        "customer_faq",
        "customer faq",
    ],
    "escalation": [
        "escalation_policy",
        "escalation policy",
        "support_troubleshooting",
        "support troubleshooting",
    ],
    "security": [
        "security_policy",
        "security policy",
        "ai_usage_policy",
        "ai usage policy",
    ],
    "privacy": [
        "data_privacy_policy",
        "data privacy policy",
        "security_policy",
        "security policy",
    ],
    "email": [
        "email_templates",
        "email templates",
        "integration_guide",
        "integration guide",
    ],
    "crm": [
        "integration_guide",
        "integration guide",
        "hubspot",
        "salesforce",
    ],
    "calendar": [
        "integration_guide",
        "integration guide",
        "google_calendar",
        "google calendar",
    ],
    "lead_qualification": [
        "sales_playbook",
        "sales playbook",
        "services_overview",
        "services overview",
        "customer_faq",
        "customer faq",
    ],
    "appointments": [
        "integration_guide",
        "integration guide",
        "demo_call_checklist",
        "demo call checklist",
        "onboarding_guide",
        "onboarding guide",
    ],
}

# Facet expansion templates for retrieval query generation
FACET_EXPANSION_TEMPLATES: dict[str, str] = {
    "services": "services offerings features capabilities automation customer support lead qualification",
    "integrations": "integrations supported HubSpot Gmail Google Calendar CRM email platforms connect",
    "pricing": "pricing plans costs fees subscription billing payment",
    "refunds": "refund policy cancellation money back return reimbursement",
    "onboarding": "onboarding implementation setup getting started configuration kickoff",
    "support": "support troubleshooting help assistance response time tickets",
    "escalation": "escalation urgent priority critical severity emergency",
    "security": "security access control encryption authentication audit compliance",
    "privacy": "privacy GDPR personal data data processing compliance regulation",
    "email": "email inbox Gmail follow-up sequences messaging correspondence",
    "crm": "CRM customer relationship lead contact HubSpot Salesforce",
    "calendar": "calendar appointment booking schedule Google Calendar meeting",
    "lead_qualification": "lead qualification prospect scoring lead scoring qualification criteria",
    "appointments": "appointments booking schedule calendar demo call meeting",
}


@dataclass(slots=True)
class FacetDetectionResult:
    """Result of facet detection on a query."""

    detected_facets: list[str]
    is_compound: bool
    facet_scores: dict[str, float]


@dataclass(slots=True)
class FacetRetrievalQuery:
    """A facet-specific retrieval query."""

    facet: str
    query_text: str
    weight: float


def _normalize_text(text: str) -> str:
    """Normalize text for matching: lowercase, collapse whitespace."""
    return " ".join(text.lower().split())


def _extract_keywords(text: str) -> set[str]:
    """Extract keywords from text (words >= 3 chars)."""
    normalized = _normalize_text(text)
    words = set(normalized.split())
    
    # Add singular/plural variations
    variations = set()
    for word in words:
        if len(word) >= 3:
            variations.add(word)
            # Simple singular/plural normalization
            if word.endswith("ies") and len(word) > 4:
                variations.add(word[:-3] + "y")
            elif word.endswith("es") and len(word) > 3:
                variations.add(word[:-2])
            elif word.endswith("s") and len(word) > 3:
                variations.add(word[:-1])
    
    return variations


def detect_facets(query: str, threshold: float = 0.15) -> FacetDetectionResult:
    """Detect semantic facets in a query.

    Args:
        query: The user query
        threshold: Minimum score to consider a facet detected (0.0 to 1.0, default 0.15)

    Returns:
        FacetDetectionResult with detected facets and scores
    """
    query_lower = _normalize_text(query)
    query_keywords = _extract_keywords(query)

    facet_scores: dict[str, float] = {}

    for facet_name, facet_keywords in FACET_KEYWORDS.items():
        # Count matching keywords
        matches = query_keywords & facet_keywords
        
        # Also check for phrase matches (more weight)
        phrase_matches = sum(
            1 for keyword in facet_keywords if keyword in query_lower
        )
        
        # Calculate score based on matches and phrase matches
        if matches or phrase_matches > 0:
            keyword_score = len(matches) / min(len(query_keywords), len(facet_keywords)) if query_keywords else 0
            phrase_score = phrase_matches / len(facet_keywords)
            
            # Weighted combination: phrase matches count more
            facet_scores[facet_name] = (keyword_score * 0.4) + (phrase_score * 0.6)

    # Filter facets above threshold
    detected_facets = [
        facet for facet, score in facet_scores.items() if score >= threshold
    ]
    detected_facets.sort(key=lambda f: facet_scores[f], reverse=True)

    is_compound = len(detected_facets) >= 2

    return FacetDetectionResult(
        detected_facets=detected_facets,
        is_compound=is_compound,
        facet_scores=facet_scores,
    )


def generate_facet_queries(
    query: str, facet_result: FacetDetectionResult, include_general: bool = True
) -> list[FacetRetrievalQuery]:
    """Generate retrieval queries for each detected facet.

    Args:
        query: The original user query
        facet_result: The facet detection result
        include_general: Whether to include the general/original query

    Returns:
        List of FacetRetrievalQuery objects
    """
    queries: list[FacetRetrievalQuery] = []

    # Include general query if requested
    if include_general:
        queries.append(
            FacetRetrievalQuery(
                facet="general", query_text=query, weight=1.0
            )
        )

    # Generate facet-specific queries for compound queries
    if facet_result.is_compound:
        for facet in facet_result.detected_facets:
            expansion = FACET_EXPANSION_TEMPLATES.get(facet, "")
            if expansion:
                facet_query = f"{expansion} {query}"
                weight = facet_result.facet_scores.get(facet, 0.5)
                queries.append(
                    FacetRetrievalQuery(
                        facet=facet, query_text=facet_query, weight=weight
                    )
                )

    return queries


def get_facet_preferred_documents(facet: str) -> list[str]:
    """Get preferred document titles/filenames for a facet.

    Args:
        facet: The facet name

    Returns:
        List of preferred document title patterns (lowercased)
    """
    return FACET_DOCUMENT_MAPPING.get(facet, [])


def should_boost_document_for_facet(document_title: str, facet: str) -> bool:
    """Check if a document should be boosted for a given facet.

    Args:
        document_title: The document title (will be normalized)
        facet: The facet name

    Returns:
        True if the document is strongly relevant to the facet
    """
    title_lower = _normalize_text(document_title)
    preferred_docs = get_facet_preferred_documents(facet)

    for preferred_pattern in preferred_docs:
        if preferred_pattern in title_lower:
            return True

    return False


def should_downrank_document_for_query(
    document_title: str, detected_facets: list[str]
) -> tuple[bool, str | None]:
    """Check if a document should be downranked for the detected facets.

    A document is downranked if it strongly matches an unrelated facet and does NOT match any detected facet.

    Args:
        document_title: The document title (will be normalized)
        detected_facets: List of facets detected in the query

    Returns:
        Tuple of (should_downrank, reason_facet)
    """
    title_lower = _normalize_text(document_title)

    # First check if document matches ANY detected facet
    matches_detected_facet = False
    for facet in detected_facets:
        preferred_docs = FACET_DOCUMENT_MAPPING.get(facet, [])
        for preferred_pattern in preferred_docs:
            if preferred_pattern in title_lower:
                matches_detected_facet = True
                break
        if matches_detected_facet:
            break

    # If document matches a detected facet, don't downrank
    if matches_detected_facet:
        return False, None

    # Check all facets not in the query
    for facet, preferred_docs in FACET_DOCUMENT_MAPPING.items():
        if facet in detected_facets:
            continue  # Don't downrank facets that ARE in the query

        # Check if document strongly matches this unrelated facet
        for preferred_pattern in preferred_docs:
            if preferred_pattern in title_lower:
                # Strong match to unrelated facet and no match to detected facets - downrank
                return True, facet

    return False, None


def calculate_facet_coverage(
    hits: list[Any], detected_facets: list[str], min_score_threshold: float = 0.45
) -> dict[str, bool]:
    """Calculate which detected facets are covered by the top hits.

    Args:
        hits: List of search hits (must have .document_title and .rerank_score or .score)
        detected_facets: List of detected facets
        min_score_threshold: Minimum score to consider a hit relevant

    Returns:
        Dict mapping facet name to coverage status (True if covered)
    """
    if not detected_facets:
        return {}

    coverage: dict[str, bool] = {facet: False for facet in detected_facets}

    for hit in hits[:5]:  # Check top 5 hits
        # Get score (handle both SearchHit and RerankHit)
        score = getattr(hit, "rerank_score", None) or getattr(hit, "score", 0.0)
        if score < min_score_threshold:
            continue

        document_title = hit.document_title

        # Check which facets this document covers
        for facet in detected_facets:
            if coverage[facet]:
                continue  # Already covered

            if should_boost_document_for_facet(document_title, facet):
                coverage[facet] = True

    return coverage


def get_facet_coverage_ratio(coverage: dict[str, bool]) -> float:
    """Calculate the facet coverage ratio.

    Args:
        coverage: Dict mapping facet name to coverage status

    Returns:
        Coverage ratio (0.0 to 1.0)
    """
    if not coverage:
        return 1.0  # No facets = full coverage

    covered_count = sum(1 for covered in coverage.values() if covered)
    total_count = len(coverage)

    return covered_count / total_count if total_count > 0 else 1.0
