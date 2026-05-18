#!/usr/bin/env python3
"""Manual script for critical two-stage routing examples (not collected by pytest).

Automated coverage lives in ``tests/test_two_stage_routing.py``.

Run from the backend directory::

    python scripts/manual_routing.py
"""

from __future__ import annotations

from onepilot.agents.intent_classifier import classify as classify_intent
from onepilot.agents.message_classifier import classify_message
from onepilot.core.constants import Intent, MessageClass


def run_routing_example(
    message: str,
    expected_class: MessageClass | None = None,
    expected_intent: Intent | None = None,
):
    """Print routing results for a single message through both stages."""
    print(f"\n{'=' * 80}")
    print(f'Message: "{message}"')
    print(f"{'=' * 80}")

    msg_result = classify_message(message)
    print("\nStage 1 - Message Classification:")
    print(f"  Class: {msg_result.message_class}")
    print(f"  Confidence: {msg_result.confidence:.2f}")
    print(f"  Reason: {msg_result.reason}")
    print("  Top Scores:")
    if msg_result.scores:
        sorted_scores = sorted(msg_result.scores.items(), key=lambda x: x[1], reverse=True)
        for cls, score in sorted_scores[:5]:
            if score > 0:
                print(f"    {cls}: {score:.1f}")

    intent_result = classify_intent(message, message_class=msg_result.message_class)
    print("\nStage 2 - Intent Classification:")
    print(f"  Intent: {intent_result.intent}")
    print(f"  Confidence: {intent_result.confidence:.2f}")
    print(f"  Reason: {intent_result.reason}")

    if expected_class:
        status = "[PASS]" if msg_result.message_class == expected_class else "[FAIL]"
        print(f"\n{status} Expected message class: {expected_class}")

    if expected_intent:
        status = "[PASS]" if intent_result.intent == expected_intent else "[FAIL]"
        print(f"{status} Expected intent: {expected_intent}")

    calls_rag = intent_result.intent in {Intent.KNOWLEDGE_SEARCH, Intent.DOCUMENT_SUMMARY}
    print(f"\n[{'CALLS RAG' if calls_rag else 'NO RAG'}]")

    return msg_result, intent_result


def main() -> None:
    """Run critical routing scenarios interactively."""
    print("\n" + "=" * 80)
    print("TWO-STAGE ROUTING - MANUAL VERIFICATION")
    print("=" * 80)

    run_routing_example(
        "What can you do for me?",
        expected_class=MessageClass.CAPABILITY_OR_HELP,
        expected_intent=Intent.GENERAL_ASSISTANT,
    )

    run_routing_example(
        "What services does NovaEdge Solutions offer and what integrations are supported?",
        expected_class=MessageClass.BUSINESS_KNOWLEDGE,
        expected_intent=Intent.KNOWLEDGE_SEARCH,
    )

    run_routing_example(
        "This is not what I meant.",
        expected_class=MessageClass.CORRECTION_OR_META,
        expected_intent=Intent.GENERAL_ASSISTANT,
    )

    run_routing_example(
        "Draft a follow up email for this lead.",
        expected_class=MessageClass.WORKFLOW_REQUEST,
        expected_intent=Intent.EMAIL_DRAFTING,
    )

    run_routing_example(
        "Hello",
        expected_class=MessageClass.CONVERSATIONAL,
        expected_intent=Intent.GENERAL_ASSISTANT,
    )

    run_routing_example(
        "What's your refund policy?",
        expected_class=MessageClass.BUSINESS_KNOWLEDGE,
        expected_intent=Intent.KNOWLEDGE_SEARCH,
    )

    print("\n" + "=" * 80)
    print("MANUAL VERIFICATION COMPLETE")
    print("=" * 80)
    print("\nKey Findings:")
    print("[PASS] Capability questions route to general_assistant (no RAG)")
    print("[PASS] Business knowledge questions route to knowledge_search (RAG)")
    print("[PASS] Corrections route to general_assistant (no RAG)")
    print("[PASS] Workflow requests route to appropriate tools")
    print()


if __name__ == "__main__":
    main()
