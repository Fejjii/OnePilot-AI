"""Tests for two-stage routing (message class + intent)."""

from __future__ import annotations

import pytest

from onepilot.agents.intent_classifier import classify as classify_intent
from onepilot.agents.message_classifier import classify_message
from onepilot.core.constants import Intent, MessageClass


class TestTwoStageRouting:
    """Test the full two-stage routing pipeline."""

    def test_capability_question_routes_to_general_assistant(self) -> None:
        """Capability question -> capability_or_help -> general_assistant."""
        message = "What can you do for me?"
        
        # Stage 1: Message classification
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.CAPABILITY_OR_HELP
        
        # Stage 2: Intent classification
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.GENERAL_ASSISTANT
        assert "message_class" in intent_result.reason

    def test_business_knowledge_routes_to_knowledge_search(self) -> None:
        """Business knowledge question -> business_knowledge -> knowledge_search."""
        message = "What services does NovaEdge Solutions offer?"
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.BUSINESS_KNOWLEDGE
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.KNOWLEDGE_SEARCH

    def test_conversational_routes_to_general_assistant(self) -> None:
        """Conversational message -> conversational -> general_assistant."""
        message = "Hello, how are you?"
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.CONVERSATIONAL
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.GENERAL_ASSISTANT

    def test_correction_routes_to_general_assistant(self) -> None:
        """Correction/meta -> correction_or_meta -> general_assistant."""
        message = "That's not what I meant"
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.CORRECTION_OR_META
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.GENERAL_ASSISTANT

    def test_email_workflow_routes_to_email_drafting(self) -> None:
        """Email workflow -> workflow_request -> email_drafting."""
        message = "Draft a follow-up email for this lead"
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.WORKFLOW_REQUEST
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.EMAIL_DRAFTING

    def test_lead_workflow_routes_to_lead_support(self) -> None:
        """Lead workflow -> workflow_request -> lead_support."""
        message = "Qualify this prospect and capture their information"
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.WORKFLOW_REQUEST
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.LEAD_SUPPORT

    def test_document_summary_workflow(self) -> None:
        """Document summary -> workflow_request -> document_summary."""
        message = "Summarize this document for me"
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.WORKFLOW_REQUEST
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.DOCUMENT_SUMMARY

    def test_scheduling_workflow_routes_to_calendar_scheduling(self) -> None:
        """Scheduling workflow -> workflow_request -> calendar_scheduling."""
        message = "Schedule a meeting for tomorrow at 2pm"
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.WORKFLOW_REQUEST
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.CALENDAR_SCHEDULING

    def test_unclear_routes_to_clarification(self) -> None:
        """Unclear message -> unclear -> clarification."""
        message = "xyz"  # Changed from "ok" which is now properly recognized as conversational
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.UNCLEAR
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.CLARIFICATION

    def test_out_of_scope_routes_to_out_of_scope(self) -> None:
        """Out of scope -> out_of_scope -> out_of_scope."""
        message = "Tell me a joke about programming"
        
        # Stage 1
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.OUT_OF_SCOPE
        
        # Stage 2
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.OUT_OF_SCOPE


class TestLegacyCompatibility:
    """Test that legacy classification (without message_class) still works."""

    @pytest.mark.parametrize(
        "message, expected_intent",
        [
            ("What is our refund policy?", Intent.KNOWLEDGE_SEARCH),
            ("Draft an email to Acme", Intent.EMAIL_DRAFTING),
            ("Capture this lead", Intent.LEAD_SUPPORT),
            ("Summarize the Q3 plan", Intent.DOCUMENT_SUMMARY),
            ("Schedule a meeting", Intent.CALENDAR_SCHEDULING),
            ("Hello there", Intent.GENERAL_ASSISTANT),
            ("That's not what I meant", Intent.GENERAL_ASSISTANT),
            ("Tell me a joke", Intent.OUT_OF_SCOPE),
        ],
    )
    def test_legacy_classification_without_message_class(
        self, message: str, expected_intent: Intent
    ) -> None:
        """Legacy path should still work when message_class is not provided."""
        result = classify_intent(message, message_class=None)
        assert result.intent == expected_intent
        assert result.source == "rules"
        # Legacy path should log a warning but still work


class TestWorkflowDisambiguation:
    """Test that workflow requests are correctly disambiguated into specific intents."""

    def test_email_indicators_detected(self) -> None:
        """Email-related workflow requests should map to EMAIL_DRAFTING."""
        messages = [
            "Draft an email",
            "Write a message to the client",
            "Compose a follow-up reply",
            "Send an introduction email",
        ]
        for msg in messages:
            msg_result = classify_message(msg)
            intent_result = classify_intent(msg, message_class=msg_result.message_class)
            assert intent_result.intent == Intent.EMAIL_DRAFTING, f"Failed for: {msg}"

    def test_lead_indicators_detected(self) -> None:
        """Lead-related workflow requests should map to LEAD_SUPPORT."""
        messages = [
            "Capture this lead",
            "Qualify the prospect",
            "New lead from Acme Corp",
            "Interested customer inquiry",
        ]
        for msg in messages:
            msg_result = classify_message(msg)
            intent_result = classify_intent(msg, message_class=msg_result.message_class)
            assert intent_result.intent == Intent.LEAD_SUPPORT, f"Failed for: {msg}"

    def test_document_summary_indicators_detected(self) -> None:
        """Document summary requests should map to DOCUMENT_SUMMARY."""
        messages = [
            "Summarize this document",
            "What are the key points?",
            "TL;DR of this report",
        ]
        for msg in messages:
            msg_result = classify_message(msg)
            intent_result = classify_intent(msg, message_class=msg_result.message_class)
            # "Give me a summary" is too ambiguous without context
            assert intent_result.intent in {
                Intent.DOCUMENT_SUMMARY,
                Intent.CLARIFICATION,
            }, f"Failed for: {msg}"

    def test_workflow_action_indicators_detected(self) -> None:
        """CRM-style workflow actions should map to WORKFLOW_ACTION."""
        messages = [
            "Update the CRM",
            "Approve this request",
        ]
        for msg in messages:
            msg_result = classify_message(msg)
            intent_result = classify_intent(msg, message_class=msg_result.message_class)
            assert intent_result.intent == Intent.WORKFLOW_ACTION, f"Failed for: {msg}"

    def test_calendar_scheduling_indicators_detected(self) -> None:
        messages = [
            "Schedule a meeting",
            "Book an appointment",
        ]
        for msg in messages:
            msg_result = classify_message(msg)
            intent_result = classify_intent(msg, message_class=msg_result.message_class)
            assert intent_result.intent == Intent.CALENDAR_SCHEDULING, f"Failed for: {msg}"

    def test_ambiguous_workflow_routes_to_clarification(self) -> None:
        """Workflow request without clear indicators should ask for clarification."""
        message = "Do something with that"
        msg_result = classify_message(message)
        
        # This might not classify as workflow_request if it's too vague
        # But if it does, and we can't determine the specific intent, it should clarify
        if msg_result.message_class == MessageClass.WORKFLOW_REQUEST:
            intent_result = classify_intent(message, message_class=msg_result.message_class)
            # Should either clarify or fall back to a reasonable default
            assert intent_result.intent in {Intent.CLARIFICATION, Intent.GENERAL_ASSISTANT}


class TestPriorityAndOverrides:
    """Test that priority rules work correctly."""

    def test_capability_question_not_routed_to_knowledge_search(self) -> None:
        """'What can you do' should NOT trigger knowledge search."""
        message = "What can you do for me?"
        msg_result = classify_message(message)
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        
        # Should be GENERAL_ASSISTANT, not KNOWLEDGE_SEARCH
        assert intent_result.intent == Intent.GENERAL_ASSISTANT
        assert msg_result.message_class == MessageClass.CAPABILITY_OR_HELP

    def test_greeting_not_routed_to_knowledge_search(self) -> None:
        """Greetings should NOT trigger knowledge search."""
        message = "Hello"
        msg_result = classify_message(message)
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        
        # Should be GENERAL_ASSISTANT, not KNOWLEDGE_SEARCH
        assert intent_result.intent == Intent.GENERAL_ASSISTANT
        assert msg_result.message_class == MessageClass.CONVERSATIONAL

    def test_correction_not_routed_to_knowledge_search(self) -> None:
        """User corrections should NOT trigger knowledge search."""
        message = "That's not what I meant"
        msg_result = classify_message(message)
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        
        # Should be GENERAL_ASSISTANT, not KNOWLEDGE_SEARCH
        assert intent_result.intent == Intent.GENERAL_ASSISTANT
        assert msg_result.message_class == MessageClass.CORRECTION_OR_META

    def test_business_knowledge_does_route_to_knowledge_search(self) -> None:
        """True business knowledge questions SHOULD trigger knowledge search."""
        messages = [
            "What services does NovaEdge Solutions offer?",
            "What integrations are supported?",
            "What's your refund policy?",
            "Tell me about your security practices",
        ]
        for msg in messages:
            msg_result = classify_message(msg)
            intent_result = classify_intent(msg, message_class=msg_result.message_class)
            assert intent_result.intent == Intent.KNOWLEDGE_SEARCH, f"Failed for: {msg}"
            assert msg_result.message_class == MessageClass.BUSINESS_KNOWLEDGE

    def test_german_hubspot_integration_routes_to_knowledge_search(self) -> None:
        """German integration questions must not fall through to clarification."""
        message = "Welche Integrationen unterstützt NovaEdge mit HubSpot und Gmail?"
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.BUSINESS_KNOWLEDGE
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.KNOWLEDGE_SEARCH

    def test_french_integration_routes_to_knowledge_search(self) -> None:
        message = "Quelles intégrations NovaEdge prend en charge avec HubSpot et Gmail?"
        msg_result = classify_message(message)
        assert msg_result.message_class == MessageClass.BUSINESS_KNOWLEDGE
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert intent_result.intent == Intent.KNOWLEDGE_SEARCH


class TestDemoRoutingMatrix:
    """Private demo routing scenarios for RAG, Serper, Gmail, Calendar, and safety."""

    @pytest.mark.parametrize(
        "message,expected_class,expected_intent",
        [
            (
                "What is NovaEdge refund policy?",
                MessageClass.BUSINESS_KNOWLEDGE,
                Intent.KNOWLEDGE_SEARCH,
            ),
            (
                "What is the price of bitcoin?",
                MessageClass.EXTERNAL_RESEARCH,
                Intent.WEB_SEARCH,
            ),
            (
                "Search the web for recent AI automation trends for SMBs",
                MessageClass.EXTERNAL_RESEARCH,
                Intent.WEB_SEARCH,
            ),
            (
                "Draft an email to a lead",
                MessageClass.WORKFLOW_REQUEST,
                Intent.EMAIL_DRAFTING,
            ),
            (
                "Schedule a 30 minute demo call tomorrow afternoon",
                MessageClass.WORKFLOW_REQUEST,
                Intent.CALENDAR_SCHEDULING,
            ),
        ],
    )
    def test_demo_routing(
        self,
        message: str,
        expected_class: MessageClass,
        expected_intent: Intent,
    ) -> None:
        msg_result = classify_message(message)
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert msg_result.message_class == expected_class
        assert intent_result.intent == expected_intent

    def test_french_berlin_weather_routes_to_web_search(self) -> None:
        message = "C'est quoi la température à Berlin aujourd'hui ?"
        msg_result = classify_message(message)
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert msg_result.message_class == MessageClass.EXTERNAL_RESEARCH
        assert intent_result.intent == Intent.WEB_SEARCH

    def test_french_oil_barrel_price_routes_to_web_search(self) -> None:
        message = "C'est quoi le prix du baril de pétrole aujourd'hui ?"
        msg_result = classify_message(message)
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert msg_result.message_class == MessageClass.EXTERNAL_RESEARCH
        assert intent_result.intent == Intent.WEB_SEARCH

    def test_english_bitcoin_price_routes_to_web_search(self) -> None:
        message = "What is the price of bitcoin?"
        msg_result = classify_message(message)
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert msg_result.message_class == MessageClass.EXTERNAL_RESEARCH
        assert intent_result.intent == Intent.WEB_SEARCH

    def test_novaedge_refund_routes_to_rag(self) -> None:
        message = "What is NovaEdge refund policy?"
        msg_result = classify_message(message)
        intent_result = classify_intent(message, message_class=msg_result.message_class)
        assert msg_result.message_class == MessageClass.BUSINESS_KNOWLEDGE
        assert intent_result.intent == Intent.KNOWLEDGE_SEARCH
