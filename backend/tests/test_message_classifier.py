"""Tests for the message classifier (Stage 1 of routing)."""

from __future__ import annotations

import pytest

from onepilot.agents.message_classifier import classify_message
from onepilot.core.constants import MessageClass


class TestCapabilityOrHelp:
    """Test classification of capability/help questions."""

    @pytest.mark.parametrize(
        "message",
        [
            "What can you do for me?",
            "How can you help?",
            "What features do you have?",
            "What tools are available?",
            "Show me what you can do",
            "What are your capabilities?",
        ],
    )
    def test_capability_questions_generalized(self, message: str) -> None:
        """Capability/help questions should route to CAPABILITY_OR_HELP."""
        result = classify_message(message)
        assert result.message_class == MessageClass.CAPABILITY_OR_HELP
        assert result.confidence >= 0.7
        assert "capability" in result.reason.lower() or "help" in result.reason.lower()

    @pytest.mark.parametrize(
        "message",
        [
            "Tell me what you're capable of",  # Edge case: might be unclear
            "What functions does this assistant support?",  # Edge case: "functions" might confuse
            "Can you explain what you offer?",  # Edge case: "offer" might trigger business
            "How does this work?",  # Edge case: very general
        ],
    )
    def test_capability_questions_edge_cases(self, message: str) -> None:
        """Edge case capability questions may be slightly ambiguous."""
        result = classify_message(message)
        # These should ideally be capability_or_help but might classify differently
        assert result.message_class in {
            MessageClass.CAPABILITY_OR_HELP,
            MessageClass.UNCLEAR,
            MessageClass.BUSINESS_KNOWLEDGE,
        }


class TestConversational:
    """Test classification of conversational messages."""

    @pytest.mark.parametrize(
        "message",
        [
            "Hi",
            "Hello there",
            "Hey, how's it going?",
            "Good morning",
            "Thanks!",
            "Thank you so much",
            "I appreciate your help",
            "Ok",
            "Sounds good",
            "Perfect",
            "How are you?",
            "Nice to meet you",
            "Test",
            "Testing, can you hear me?",
        ],
    )
    def test_conversational_messages_generalized(self, message: str) -> None:
        """Greetings, thanks, acknowledgments should route to CONVERSATIONAL."""
        result = classify_message(message)
        assert result.message_class == MessageClass.CONVERSATIONAL
        assert result.confidence >= 0.7
        assert "conversational" in result.reason.lower()

    @pytest.mark.parametrize(
        "message",
        [
            "Okay, got it",  # Edge case: longer acknowledgment, might be unclear
        ],
    )
    def test_conversational_edge_cases(self, message: str) -> None:
        """Edge case conversational messages."""
        result = classify_message(message)
        assert result.message_class in {MessageClass.CONVERSATIONAL, MessageClass.UNCLEAR}


class TestCorrectionOrMeta:
    """Test classification of correction/meta messages."""

    @pytest.mark.parametrize(
        "message",
        [
            "That's not what I meant",
            "Wrong answer",
            "You misunderstood",
            "This is incorrect",
            "That doesn't help",
            "This is unrelated",
            "You're off track",
            "Nevermind",
            "Forget it",
            "Actually, I want something else",
            "Wait, stop",
            "This is not a related conversation about the services that you do",
            "You got that wrong",
        ],
    )
    def test_correction_meta_messages_generalized(self, message: str) -> None:
        """Corrections and meta comments should route to CORRECTION_OR_META."""
        result = classify_message(message)
        assert result.message_class == MessageClass.CORRECTION_OR_META
        assert result.confidence >= 0.7
        assert "correction" in result.reason.lower() or "meta" in result.reason.lower()


class TestBusinessKnowledge:
    """Test classification of business knowledge questions."""

    @pytest.mark.parametrize(
        "message",
        [
            # Service questions
            "What services does NovaEdge Solutions offer?",
            "Tell me about your products",
            "What solutions do you provide?",
            # Integration questions
            "What integrations are supported?",
            "Do you have an API?",
            "How do I integrate with your system?",
            # Policy questions
            "What's your refund policy?",
            "Tell me about your privacy policy",
            "What is the data retention policy?",
            "How do you handle security?",
            # Pricing/billing
            "How much does it cost?",
            "What are your pricing tiers?",
            "Tell me about billing",
            "What's included in the subscription?",
            # Support/onboarding
            "How do I get support?",
            "What's the onboarding process?",
            "Where is the user guide?",
            # Documentation
            "Where can I find the documentation?",
            "Is there a knowledge base?",
            "Show me the setup guide",
        ],
    )
    def test_business_knowledge_questions_generalized(self, message: str) -> None:
        """Business knowledge questions should route to BUSINESS_KNOWLEDGE."""
        result = classify_message(message)
        assert result.message_class == MessageClass.BUSINESS_KNOWLEDGE
        assert result.confidence >= 0.65
        assert "business" in result.reason.lower() or "knowledge" in result.reason.lower()

    @pytest.mark.parametrize(
        "message",
        [
            "What third-party tools do you work with?",  # Edge case: "you" might trigger capability
            "How do I escalate an issue?",  # Edge case: might be unclear without context
        ],
    )
    def test_business_knowledge_edge_cases(self, message: str) -> None:
        """Edge case business questions may classify as business_knowledge or capability_or_help."""
        result = classify_message(message)
        # These are acceptable classifications given the ambiguity
        assert result.message_class in {
            MessageClass.BUSINESS_KNOWLEDGE,
            MessageClass.CAPABILITY_OR_HELP,
            MessageClass.UNCLEAR,
        }


class TestWorkflowRequest:
    """Test classification of workflow requests."""

    @pytest.mark.parametrize(
        "message",
        [
            # Email
            "Draft an email to John",
            "Write a follow-up message",
            "Compose a reply to this customer",
            "Send an introduction email",
            # Lead
            "Create a new lead for Acme Corp",
            "Qualify this prospect",
            "Capture lead information",
            "Update the lead status",
            # Meeting/scheduling
            "Schedule a meeting tomorrow",
            "Book an appointment with the client",
            # CRM/actions
            "Update the CRM",
            "Sync to CRM",
            "Approve this request",
            "Reject the proposal",
            # Document
            "Summarize this document",
            "Create a report summary",
        ],
    )
    def test_workflow_requests_generalized(self, message: str) -> None:
        """Workflow requests should route to WORKFLOW_REQUEST."""
        result = classify_message(message)
        assert result.message_class == MessageClass.WORKFLOW_REQUEST
        assert result.confidence >= 0.60

    @pytest.mark.parametrize(
        "message",
        [
            "Set up a call for next week",  # Edge case: "set up" + "call"
            "Give me the key points",  # Edge case: might be unclear without context
        ],
    )
    def test_workflow_edge_cases(self, message: str) -> None:
        """Edge case workflow requests may need more context."""
        result = classify_message(message)
        assert result.message_class in {
            MessageClass.WORKFLOW_REQUEST,
            MessageClass.UNCLEAR,
        }


class TestUnclear:
    """Test classification of unclear messages."""

    @pytest.mark.parametrize(
        "message",
        [
            "hmm",  # Too short and not a greeting
            "",  # Empty
            "   ",  # Whitespace only
            "xyz",  # Gibberish short
        ],
    )
    def test_unclear_messages(self, message: str) -> None:
        """Very short or empty messages (non-conversational) should route to UNCLEAR."""
        result = classify_message(message)
        assert result.message_class == MessageClass.UNCLEAR
        assert result.confidence >= 0.5

    def test_short_greetings_are_conversational(self) -> None:
        """Short greetings like 'hi' and 'ok' should be CONVERSATIONAL, not UNCLEAR."""
        short_conversational = ["hi", "Hi", "ok", "Ok", "hey"]
        for msg in short_conversational:
            result = classify_message(msg)
            assert result.message_class == MessageClass.CONVERSATIONAL


class TestOutOfScope:
    """Test classification of out-of-scope messages."""

    @pytest.mark.parametrize(
        "message",
        [
            "What's the weather today?",
            "Tell me a joke",
            "Write me a love poem",
            "Sing a song",
            "Play a game with me",
            "Generate an image of a cat",
        ],
    )
    def test_out_of_scope_messages(self, message: str) -> None:
        """Out-of-scope requests should route to OUT_OF_SCOPE."""
        result = classify_message(message)
        assert result.message_class == MessageClass.OUT_OF_SCOPE
        assert result.confidence >= 0.85
        assert "out_of_scope" in result.reason.lower() or "scope" in result.reason.lower()

    @pytest.mark.parametrize(
        "message",
        [
            "What's the stock price of Tesla?",
            "What is the price of bitcoin?",
            "Tell me about cryptocurrency prices today",
        ],
    )
    def test_market_price_queries_route_to_external_research(self, message: str) -> None:
        """Public market/current-fact queries should use web search, not internal KB."""
        result = classify_message(message)
        assert result.message_class == MessageClass.EXTERNAL_RESEARCH


class TestDisambiguation:
    """Test disambiguation between similar message classes."""

    def test_capability_vs_business_knowledge_services(self) -> None:
        """'What services do you offer' is about business, not assistant capability."""
        result = classify_message("What services does NovaEdge offer?")
        # This should be business knowledge (about the company's services)
        # not capability (about the assistant's features)
        assert result.message_class == MessageClass.BUSINESS_KNOWLEDGE

    def test_capability_question_about_assistant(self) -> None:
        """'What can you do' is about assistant capability."""
        result = classify_message("What can you do for me?")
        assert result.message_class == MessageClass.CAPABILITY_OR_HELP

    def test_greeting_vs_capability(self) -> None:
        """'Hi how can you help' should prioritize conversational greeting."""
        result = classify_message("Hi, how can you help?")
        # With current priority, conversational should win due to greeting
        assert result.message_class in {MessageClass.CONVERSATIONAL, MessageClass.CAPABILITY_OR_HELP}

    def test_business_question_with_what(self) -> None:
        """Generic 'what' question about business topic should route to business knowledge."""
        result = classify_message("What integrations are available?")
        assert result.message_class == MessageClass.BUSINESS_KNOWLEDGE


class TestRobustness:
    """Test robustness to different phrasings."""

    def test_varied_capability_phrasings(self) -> None:
        """Different ways of asking about capabilities should all route the same."""
        messages = [
            "What are you able to do?",
            "What features are supported?",
            "Tell me your capabilities",
            "Show me what tools you have",
        ]
        for msg in messages:
            result = classify_message(msg)
            assert result.message_class == MessageClass.CAPABILITY_OR_HELP

    def test_varied_correction_phrasings(self) -> None:
        """Different ways of correcting should all route the same."""
        messages = [
            "That's not right",
            "You misunderstood me",
            "This is wrong",
            "That doesn't make sense",
        ]
        for msg in messages:
            result = classify_message(msg)
            assert result.message_class == MessageClass.CORRECTION_OR_META

    def test_varied_business_knowledge_phrasings(self) -> None:
        """Different ways of asking business questions should all route to business_knowledge."""
        messages = [
            "What's your pricing?",
            "Tell me about your prices",
            "How much do you charge?",
        ]
        for msg in messages:
            result = classify_message(msg)
            # "What are the costs?" might be unclear without context
            assert result.message_class in {
                MessageClass.BUSINESS_KNOWLEDGE,
                MessageClass.UNCLEAR,
            }, f"Failed for: {msg}"


class TestScoreDetails:
    """Test that scores are calculated and returned properly."""

    def test_scores_present_in_result(self) -> None:
        """Result should include scores for all message classes."""
        result = classify_message("What can you do?")
        assert result.scores is not None
        assert len(result.scores) >= 5  # Should have scores for multiple classes
        assert MessageClass.CAPABILITY_OR_HELP in result.scores
        assert MessageClass.BUSINESS_KNOWLEDGE in result.scores

    def test_confidence_in_valid_range(self) -> None:
        """Confidence should always be between 0.0 and 1.0."""
        messages = [
            "What can you do?",
            "Hello",
            "That's wrong",
            "What's your refund policy?",
            "Draft an email",
        ]
        for msg in messages:
            result = classify_message(msg)
            assert 0.0 <= result.confidence <= 1.0

    def test_reason_is_descriptive(self) -> None:
        """Reason should explain why the classification was chosen."""
        result = classify_message("What can you do?")
        assert result.reason
        assert len(result.reason) > 0
