"""Tests for the deterministic intent classifier."""

from __future__ import annotations

import pytest

from onepilot.agents.intent_classifier import classify
from onepilot.core.constants import Intent


class TestRuleBasedIntent:
    @pytest.mark.parametrize(
        "message, expected",
        [
            ("What is our refund policy?", Intent.KNOWLEDGE_SEARCH),
            ("Where is the onboarding guide?", Intent.KNOWLEDGE_SEARCH),
            ("Draft an email to Acme thanking them.", Intent.EMAIL_DRAFTING),
            ("Write a follow-up email to a prospect.", Intent.EMAIL_DRAFTING),
            ("Capture this lead: John from Globex.", Intent.LEAD_SUPPORT),
            ("Qualify this prospect.", Intent.LEAD_SUPPORT),
            ("Summarize the Q3 plan.", Intent.DOCUMENT_SUMMARY),
            ("Schedule a meeting tomorrow.", Intent.WORKFLOW_ACTION),
            ("Update the CRM with this conversation.", Intent.WORKFLOW_ACTION),
            ("Hey there, how's your day going?", Intent.GENERAL_ASSISTANT),
            ("Tell me a joke please.", Intent.OUT_OF_SCOPE),
            ("What's the weather like?", Intent.OUT_OF_SCOPE),
            ("ok", Intent.CLARIFICATION),
            # User corrections and meta-comments
            ("That's not what I meant.", Intent.GENERAL_ASSISTANT),
            ("This is not a related conversation about the services that you do.", Intent.GENERAL_ASSISTANT),
            ("Wrong, that doesn't help.", Intent.GENERAL_ASSISTANT),
            ("You misunderstood my question.", Intent.GENERAL_ASSISTANT),
            ("Nevermind, I'll do it myself.", Intent.GENERAL_ASSISTANT),
            ("Actually, forget about that.", Intent.GENERAL_ASSISTANT),
        ],
    )
    def test_classify_known_examples(self, message: str, expected: Intent) -> None:
        result = classify(message)
        assert result.intent == expected, f"{message!r} -> {result.intent}"
        assert 0.0 <= result.confidence <= 1.0
        assert result.source == "rules"

    def test_clarification_for_short_message(self) -> None:
        assert classify("hi").intent == Intent.CLARIFICATION

    def test_clarification_for_empty_message(self) -> None:
        assert classify("").intent == Intent.CLARIFICATION
        assert classify("   ").intent == Intent.CLARIFICATION

    def test_out_of_scope_takes_priority(self) -> None:
        # "What is the weather" matches both knowledge_search (what) and out_of_scope.
        # Out-of-scope MUST win.
        result = classify("What is the weather today?")
        assert result.intent == Intent.OUT_OF_SCOPE

    def test_no_match_falls_back_to_general(self) -> None:
        result = classify("random gibberish text without any signal pattern")
        assert result.intent == Intent.GENERAL_ASSISTANT
        assert result.confidence == pytest.approx(0.5)


class TestUseLLMOptOut:
    def test_use_llm_returns_rules_when_no_openai(self) -> None:
        # Without OPENAI_API_KEY, even when ``use_llm=True`` we must fall back
        # to the deterministic rule path.
        result = classify("Draft an email to Bob.", use_llm=True)
        assert result.intent == Intent.EMAIL_DRAFTING
        assert result.source == "rules"
