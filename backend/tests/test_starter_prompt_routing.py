"""Starter-prompt routing for workspace chips (OP-015)."""

from __future__ import annotations

from onepilot.agents.intent_classifier import classify
from onepilot.agents.message_classifier import classify_message
from onepilot.agents.workflow import branch_for
from onepilot.core.constants import Intent

STARTER_PROMPTS: list[tuple[str, Intent, str]] = [
    (
        "Summarize our recent business activity across leads, approvals, and conversations.",
        Intent.WORKSPACE_INSIGHTS,
        "workspace_insights",
    ),
    (
        "Which approvals are currently pending and what do they cover?",
        Intent.WORKSPACE_INSIGHTS,
        "workspace_insights",
    ),
    (
        "What does our knowledge base say about the escalation policy?",
        Intent.KNOWLEDGE_SEARCH,
        "knowledge_search",
    ),
    (
        "Analyze our current leads and highlight the most promising ones.",
        Intent.WORKSPACE_INSIGHTS,
        "workspace_insights",
    ),
    (
        "Draft a follow-up email to our most promising lead about scheduling an intro call.",
        Intent.EMAIL_DRAFTING,
        "email_assistant",
    ),
    (
        "What meetings are on the calendar this week?",
        Intent.CALENDAR_AVAILABILITY,
        "calendar_assistant",
    ),
]


def test_starter_prompts_route_to_expected_branches() -> None:
    for prompt, expected_intent, expected_branch in STARTER_PROMPTS:
        msg = classify_message(prompt)
        intent = classify(prompt, message_class=msg.message_class, use_llm=False)
        assert intent.intent == expected_intent, (
            f"{prompt!r} -> {intent.intent} ({intent.reason}); class={msg.message_class}"
        )
        assert branch_for(intent.intent) == expected_branch
        assert intent.intent != Intent.WEB_SEARCH
        assert intent.intent != Intent.CLARIFICATION


def test_recent_without_web_context_does_not_force_web_search() -> None:
    prompt = "Summarize our recent business activity across leads, approvals, and conversations."
    msg = classify_message(prompt)
    intent = classify(prompt, message_class=msg.message_class, use_llm=False)
    assert intent.intent == Intent.WORKSPACE_INSIGHTS


def test_genuine_web_research_still_routes_to_serper() -> None:
    prompt = "Find recent SMB automation trends"
    msg = classify_message(prompt)
    intent = classify(prompt, message_class=msg.message_class, use_llm=False)
    assert intent.intent == Intent.WEB_SEARCH
    assert branch_for(intent.intent) == "web_search"
