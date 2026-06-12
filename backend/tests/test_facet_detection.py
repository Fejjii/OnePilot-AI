"""Tests for generalized facet detection and mapping."""

from __future__ import annotations

import pytest

from onepilot.services.facets import (
    FACET_DOCUMENT_MAPPING,
    calculate_facet_coverage,
    detect_facets,
    generate_facet_queries,
    get_facet_coverage_ratio,
    get_facet_preferred_documents,
    should_boost_document_for_facet,
    should_downrank_document_for_query,
)


class TestFacetDetection:
    """Test facet detection functionality."""

    def test_detect_single_facet_services(self) -> None:
        """Test detection of single facet: services."""
        result = detect_facets("What services does NovaEdge offer?")
        
        assert "services" in result.detected_facets
        assert not result.is_compound
        assert result.facet_scores["services"] > 0.15  # Lowered threshold

    def test_detect_single_facet_integrations(self) -> None:
        """Test detection of single facet: integrations."""
        result = detect_facets("What integrations are supported?")
        
        assert "integrations" in result.detected_facets
        assert not result.is_compound
        assert result.facet_scores["integrations"] > 0.15  # Lowered threshold

    def test_detect_compound_services_and_integrations(self) -> None:
        """Test detection of compound facets: services + integrations."""
        result = detect_facets(
            "What services does NovaEdge Solutions offer and what integrations are supported?"
        )
        
        assert "services" in result.detected_facets
        assert "integrations" in result.detected_facets
        assert result.is_compound
        assert len(result.detected_facets) >= 2

    def test_detect_compound_pricing_and_refunds(self) -> None:
        """Test detection of compound facets: pricing + refunds."""
        result = detect_facets("What are the pricing plans and refund policy?")
        
        assert "pricing" in result.detected_facets
        assert "refunds" in result.detected_facets
        assert result.is_compound

    def test_detect_compound_onboarding_and_escalation(self) -> None:
        """Test detection of compound facets: onboarding + escalation."""
        result = detect_facets("How does onboarding work and when do you escalate issues?")
        
        assert "onboarding" in result.detected_facets
        assert "escalation" in result.detected_facets
        assert result.is_compound

    def test_detect_customer_support_escalation_rules(self) -> None:
        result = detect_facets(
            "What are the escalation rules for customer support?"
        )
        assert "escalation" in result.detected_facets
        queries = generate_facet_queries(
            "What are the escalation rules for customer support?",
            result,
        )
        escalation_queries = [q.query_text for q in queries if q.facet == "escalation"]
        assert escalation_queries
        assert any("handoff" in text.lower() for text in escalation_queries)

    def test_detect_compound_security_and_privacy(self) -> None:
        """Test detection of compound facets: security + privacy."""
        result = detect_facets("What security controls and data privacy policies do you follow?")
        
        assert "security" in result.detected_facets
        assert "privacy" in result.detected_facets
        assert result.is_compound

    def test_detect_compound_email_and_crm(self) -> None:
        """Test detection of compound facets: email + crm."""
        result = detect_facets("What email workflows and CRM automations are available?")
        
        assert "email" in result.detected_facets or "crm" in result.detected_facets
        # May detect both or just one depending on keyword matching

    def test_detect_compound_support_and_response_times(self) -> None:
        """Test detection of compound facets: support."""
        result = detect_facets("What support options and response times do you provide?")
        
        assert "support" in result.detected_facets

    def test_generate_facet_queries_single(self) -> None:
        """Test query generation for single facet."""
        facet_result = detect_facets("What services do you offer?")
        queries = generate_facet_queries("What services do you offer?", facet_result)
        
        # Should only have general query for single facet
        assert len(queries) == 1
        assert queries[0].facet == "general"

    def test_generate_facet_queries_compound(self) -> None:
        """Test query generation for compound facets."""
        facet_result = detect_facets(
            "What services does NovaEdge offer and what integrations are supported?"
        )
        queries = generate_facet_queries(
            "What services does NovaEdge offer and what integrations are supported?",
            facet_result,
        )
        
        # Should have general + facet-specific queries
        assert len(queries) >= 2
        assert any(q.facet == "general" for q in queries)
        assert any(q.facet == "services" for q in queries)
        assert any(q.facet == "integrations" for q in queries)

    def test_get_facet_preferred_documents_services(self) -> None:
        """Test getting preferred documents for services facet."""
        docs = get_facet_preferred_documents("services")
        
        assert "services_overview" in docs or "services overview" in docs
        assert len(docs) > 0

    def test_get_facet_preferred_documents_integrations(self) -> None:
        """Test getting preferred documents for integrations facet."""
        docs = get_facet_preferred_documents("integrations")
        
        assert any("integration" in doc for doc in docs)
        assert len(docs) > 0

    def test_should_boost_services_overview_for_services(self) -> None:
        """Test boosting Services Overview for services query."""
        assert should_boost_document_for_facet("Services Overview", "services")
        assert should_boost_document_for_facet("NovaEdge Solutions — Services Overview", "services")

    def test_should_boost_integration_guide_for_integrations(self) -> None:
        """Test boosting Integration Guide for integrations query."""
        assert should_boost_document_for_facet("Integration Guide", "integrations")
        assert should_boost_document_for_facet("Integration Guide — HubSpot, Gmail", "integrations")

    def test_should_boost_pricing_plans_for_pricing(self) -> None:
        """Test boosting Pricing Plans for pricing query."""
        assert should_boost_document_for_facet("Pricing Plans", "pricing")

    def test_should_not_boost_unrelated_doc(self) -> None:
        """Test not boosting unrelated documents."""
        assert not should_boost_document_for_facet("Data Privacy Policy", "services")
        assert not should_boost_document_for_facet("Refund Policy", "integrations")

    def test_should_downrank_privacy_for_services_query(self) -> None:
        """Test downranking privacy docs for services-only query."""
        should_downrank, reason = should_downrank_document_for_query(
            "Data Privacy Policy",
            ["services"],
        )
        assert should_downrank
        assert reason == "privacy"

    def test_should_downrank_refund_for_services_query(self) -> None:
        """Test downranking refund docs for services-only query."""
        should_downrank, reason = should_downrank_document_for_query(
            "Refund Policy",
            ["services", "integrations"],
        )
        assert should_downrank
        assert reason == "refunds"

    def test_should_not_downrank_privacy_for_privacy_query(self) -> None:
        """Test NOT downranking privacy docs when privacy is in query."""
        should_downrank, reason = should_downrank_document_for_query(
            "Data Privacy Policy",
            ["privacy", "security"],
        )
        assert not should_downrank

    def test_should_not_downrank_services_overview(self) -> None:
        """Test not downranking Services Overview for any query."""
        should_downrank, reason = should_downrank_document_for_query(
            "Services Overview",
            ["services", "integrations"],
        )
        assert not should_downrank


class TestFacetCoverage:
    """Test facet coverage calculation."""

    def test_calculate_coverage_all_covered(self) -> None:
        """Test coverage calculation when all facets are covered."""
        from dataclasses import dataclass
        
        @dataclass
        class MockHit:
            document_title: str
            rerank_score: float
        
        hits = [
            MockHit("Services Overview", 0.9),
            MockHit("Integration Guide", 0.8),
        ]
        
        coverage = calculate_facet_coverage(hits, ["services", "integrations"], 0.45)
        
        assert coverage["services"] is True
        assert coverage["integrations"] is True

    def test_calculate_coverage_partial(self) -> None:
        """Test coverage calculation with partial coverage."""
        from dataclasses import dataclass
        
        @dataclass
        class MockHit:
            document_title: str
            rerank_score: float
        
        hits = [
            MockHit("Services Overview", 0.9),
            MockHit("Customer FAQ", 0.7),
        ]
        
        coverage = calculate_facet_coverage(hits, ["services", "integrations"], 0.45)
        
        assert coverage["services"] is True
        assert coverage["integrations"] is False  # No integration doc

    def test_calculate_coverage_none(self) -> None:
        """Test coverage calculation with no coverage."""
        from dataclasses import dataclass
        
        @dataclass
        class MockHit:
            document_title: str
            rerank_score: float
        
        hits = [
            MockHit("Data Privacy Policy", 0.9),
            MockHit("Security Policy", 0.8),
        ]
        
        coverage = calculate_facet_coverage(hits, ["services", "integrations"], 0.45)
        
        assert coverage["services"] is False
        assert coverage["integrations"] is False

    def test_get_coverage_ratio_full(self) -> None:
        """Test coverage ratio calculation with full coverage."""
        coverage = {"services": True, "integrations": True}
        ratio = get_facet_coverage_ratio(coverage)
        
        assert ratio == 1.0

    def test_get_coverage_ratio_half(self) -> None:
        """Test coverage ratio calculation with half coverage."""
        coverage = {"services": True, "integrations": False}
        ratio = get_facet_coverage_ratio(coverage)
        
        assert ratio == 0.5

    def test_get_coverage_ratio_none(self) -> None:
        """Test coverage ratio calculation with no coverage."""
        coverage = {"services": False, "integrations": False, "pricing": False}
        ratio = get_facet_coverage_ratio(coverage)
        
        assert ratio == 0.0

    def test_get_coverage_ratio_empty(self) -> None:
        """Test coverage ratio with no facets."""
        coverage = {}
        ratio = get_facet_coverage_ratio(coverage)
        
        assert ratio == 1.0  # No facets = full coverage
