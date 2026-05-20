"""Intent classifier (Stage 2 of routing).

After message classification (Stage 1), this module maps message classes to
specific intents for tool selection. The mapping is deterministic and rule-based
for auditability and reproducibility.

Stage 1 (message_classifier.py) identifies high-level message classes:
- capability_or_help, conversational, correction_or_meta, business_knowledge,
  workflow_request, unclear, out_of_scope

Stage 2 (this module) maps message classes to specific intents:
- general_assistant, knowledge_search, email_drafting, lead_support,
  workflow_action, document_summary, clarification, out_of_scope
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import Intent, MessageClass
from onepilot.core.logging import get_logger
from onepilot.providers import get_llm_provider
from onepilot.providers.llm.base import LLMProvider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Stage 2: Message class to intent mapping
# ---------------------------------------------------------------------------

# Direct mappings from message class to intent
_MESSAGE_CLASS_TO_INTENT: dict[MessageClass, Intent] = {
    MessageClass.CAPABILITY_OR_HELP: Intent.GENERAL_ASSISTANT,
    MessageClass.CONVERSATIONAL: Intent.GENERAL_ASSISTANT,
    MessageClass.CORRECTION_OR_META: Intent.GENERAL_ASSISTANT,
    MessageClass.BUSINESS_KNOWLEDGE: Intent.KNOWLEDGE_SEARCH,
    MessageClass.UNCLEAR: Intent.CLARIFICATION,
    MessageClass.OUT_OF_SCOPE: Intent.OUT_OF_SCOPE,
}

# Workflow requests need deeper inspection to route correctly
_EMAIL_PATTERNS = [
    re.compile(
        r"\b(draft|write|compose|reply to|send)\b.*\b(email|message|mail|reply|response)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(follow[- ]?up|outreach|cold email|introduction email)\b", re.IGNORECASE),
]

_LEAD_PATTERNS = [
    re.compile(
        r"\b(new (lead|prospect)|interested (customer|buyer)|sales inquiry)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(lead|prospect|customer inquiry|qualify|capture)\b",
        re.IGNORECASE,
    ),
]

_DOCUMENT_SUMMARY_PATTERNS = [
    re.compile(r"\b(summari[sz]e|summary of|tl;dr|key points)\b", re.IGNORECASE),
]

_INTERNAL_COMPARISON_PATTERNS = [
    re.compile(
        r"\bcompare\b.{0,80}\b(our|novaedge|company)\b.{0,40}\b(service|solution|offering)s?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bcompare\b.{0,40}\bwith\b.{0,40}\b(novaedge|our (company )?services?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(market trends?|automation trends?).{0,40}\bcompare\b.{0,40}\b(service|solution)s?\b",
        re.IGNORECASE,
    ),
]

_WORKFLOW_ACTION_PATTERNS = [
    re.compile(
        r"\b(update (?:the )?crm|sync to crm|send invoice|create ticket|approve|reject)\b",
        re.IGNORECASE,
    ),
]

_CALENDAR_AVAILABILITY_PATTERNS = [
    re.compile(
        r"\b(am i free|are we free|check (my )?availability|availability|busy tomorrow|free tomorrow|free next)\b",
        re.IGNORECASE,
    ),
]

_CALENDAR_SCHEDULING_PATTERNS = [
    re.compile(
        r"\b(schedule|book a|book (the|an?)|set up a|create a).{0,40}\b(meeting|call|appointment|slot)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(suggest|propose|offer|recommend).{0,30}\b(slot|time|times|meeting)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbook.{0,20}\b\d{1,3}[- ]?(?:minute|min).{0,20}\bslot\b",
        re.IGNORECASE,
    ),
]

_COMPOUND_WORKFLOW_PATTERNS = [
    re.compile(
        r"(?=.*\b(find|research|search).{0,80}\b(trend|trends|market|news)\b)"
        r"(?=.*\b(draft|write|compose).{0,60}\b(email|mail|message)\b)"
        r"(?=.*\b(schedule|book).{0,60}\b(meeting|call|appointment)\b)",
        re.IGNORECASE | re.DOTALL,
    ),
]

_CALENDAR_AND_EMAIL_PATTERNS = [
    re.compile(
        r"\b(draft|write|compose|send).{0,40}\b(email|mail|message)\b.{0,80}\b(schedule|book).{0,30}\b(meeting|call|appointment)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(schedule|book).{0,40}\b(meeting|call|appointment)\b.{0,80}\b(draft|write|compose|send).{0,40}\b(email|mail|message)\b",
        re.IGNORECASE,
    ),
]

# Minimum message length for intent classification
_MIN_CHARS_FOR_INTENT = 4


@dataclass(slots=True)
class IntentResult:
    """Result of intent classification (Stage 2)."""

    intent: Intent
    confidence: float
    source: str  # "rules" or "llm"
    reason: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(
    message: str,
    message_class: MessageClass | None = None,
    *,
    settings: Settings | None = None,
    llm: LLMProvider | None = None,
    use_llm: bool = False,
) -> IntentResult:
    """Classify a message into an Intent (Stage 2 of routing).

    If message_class is provided, uses Stage 2 mapping logic.
    If not provided, falls back to legacy keyword-based classification for backward compatibility.

    Args:
        message: The user message
        message_class: Optional message class from Stage 1 classification
        settings: Optional settings override
        llm: Optional LLM provider override
        use_llm: Whether to use LLM classification (requires OpenAI)

    Returns:
        IntentResult with intent, confidence, source, and reason
    """
    cleaned = (message or "").strip()
    if len(cleaned) < _MIN_CHARS_FOR_INTENT:
        return IntentResult(
            intent=Intent.CLARIFICATION,
            confidence=0.6,
            source="rules",
            reason="message_too_short",
        )

    # Stage 2: Use message class if provided
    if message_class is not None:
        return _classify_from_message_class(cleaned, message_class)

    # Legacy fallback: keyword-based classification for backward compatibility
    # This path is used when Stage 1 is skipped (e.g., in old tests)
    logger.warning("intent_classifier_called_without_message_class", message_preview=cleaned[:50])
    return _classify_legacy(cleaned, settings=settings, llm=llm, use_llm=use_llm)


def _classify_from_message_class(message: str, message_class: MessageClass) -> IntentResult:
    """Stage 2: Map message class to specific intent.

    Args:
        message: The user message
        message_class: Message class from Stage 1

    Returns:
        IntentResult with mapped intent
    """
    # Direct mappings (most message classes map 1:1 to intents)
    if message_class in _MESSAGE_CLASS_TO_INTENT:
        intent = _MESSAGE_CLASS_TO_INTENT[message_class]
        return IntentResult(
            intent=intent,
            confidence=0.85,
            source="rules",
            reason=f"message_class:{message_class}",
        )

    # Workflow requests need deeper inspection
    if message_class == MessageClass.WORKFLOW_REQUEST:
        return _classify_workflow_intent(message)

    if message_class == MessageClass.EXTERNAL_RESEARCH:
        return _classify_external_research_intent(message)

    # Fallback (shouldn't happen with well-designed Stage 1)
    logger.warning("unexpected_message_class", message_class=message_class)
    return IntentResult(
        intent=Intent.GENERAL_ASSISTANT,
        confidence=0.5,
        source="rules",
        reason=f"fallback_from:{message_class}",
    )


def _classify_external_research_intent(message: str) -> IntentResult:
    """Map external research messages to web-only or web+knowledge intents."""
    for pattern in _INTERNAL_COMPARISON_PATTERNS:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.WEB_AND_KNOWLEDGE,
                confidence=0.88,
                source="rules",
                reason="external_research:internal_comparison",
            )
    return IntentResult(
        intent=Intent.WEB_SEARCH,
        confidence=0.86,
        source="rules",
        reason="external_research:web_only",
    )


def _classify_workflow_intent(message: str) -> IntentResult:
    """Classify workflow requests into specific workflow intents.

    Args:
        message: The user message

    Returns:
        IntentResult with workflow-specific intent
    """
    for pattern in _COMPOUND_WORKFLOW_PATTERNS:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.COMPOUND_WORKFLOW,
                confidence=0.88,
                source="rules",
                reason="workflow:compound_research_email_calendar",
            )

    # Check for combined email + calendar workflow
    for pattern in _CALENDAR_AND_EMAIL_PATTERNS:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.CALENDAR_AND_EMAIL,
                confidence=0.86,
                source="rules",
                reason="workflow:calendar_and_email",
            )

    # Check for email drafting
    for pattern in _EMAIL_PATTERNS:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.EMAIL_DRAFTING,
                confidence=0.82,
                source="rules",
                reason="workflow:email_drafting",
            )

    # Calendar availability (before scheduling and lead support)
    for pattern in _CALENDAR_AVAILABILITY_PATTERNS:
        if pattern.search(message) and not any(p.search(message) for p in _CALENDAR_SCHEDULING_PATTERNS):
            return IntentResult(
                intent=Intent.CALENDAR_AVAILABILITY,
                confidence=0.84,
                source="rules",
                reason="workflow:calendar_availability",
            )

    # Calendar scheduling / slot suggestions (before lead support — "schedule meeting with lead")
    for pattern in _CALENDAR_SCHEDULING_PATTERNS:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.CALENDAR_SCHEDULING,
                confidence=0.84,
                source="rules",
                reason="workflow:calendar_scheduling",
            )

    # Check for lead support
    for pattern in _LEAD_PATTERNS:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.LEAD_SUPPORT,
                confidence=0.85,
                source="rules",
                reason="workflow:lead_support",
            )

    # Check for document summary
    for pattern in _DOCUMENT_SUMMARY_PATTERNS:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.DOCUMENT_SUMMARY,
                confidence=0.78,
                source="rules",
                reason="workflow:document_summary",
            )

    # Check for general workflow actions
    for pattern in _WORKFLOW_ACTION_PATTERNS:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.WORKFLOW_ACTION,
                confidence=0.82,
                source="rules",
                reason="workflow:workflow_action",
            )

    # Fallback: generic workflow action or clarification
    return IntentResult(
        intent=Intent.CLARIFICATION,
        confidence=0.6,
        source="rules",
        reason="workflow:unclear",
    )


# ---------------------------------------------------------------------------
# Legacy classification (backward compatibility)
# ---------------------------------------------------------------------------

# Legacy keyword rules for backward compatibility with old tests
_LEGACY_KEYWORD_RULES: list[tuple[re.Pattern[str], Intent, float]] = [
    # User corrections / meta comments
    (
        re.compile(
            r"\b(not (what|a|the)|wrong|mistake|incorrect|misunderstood|off[-\s]?track|unrelated"
            r"|that'?s not|doesn'?t (help|work|make sense)|this is not)\b",
            re.IGNORECASE,
        ),
        Intent.GENERAL_ASSISTANT,
        0.88,
    ),
    (
        re.compile(
            r"^\s*(nevermind|never mind|forget it|skip|actually|wait|hold on)\b",
            re.IGNORECASE,
        ),
        Intent.GENERAL_ASSISTANT,
        0.85,
    ),
    # Greetings / conversational
    (
        re.compile(
            r"^\s*(hi|hey|hello|yo|thanks|thank you|good (morning|afternoon|evening))\b",
            re.IGNORECASE,
        ),
        Intent.GENERAL_ASSISTANT,
        0.85,
    ),
    # Email drafting
    (
        re.compile(
            r"\b(draft|write|compose|reply to|send)\b.*\b(email|message|mail|reply|response)\b",
            re.IGNORECASE,
        ),
        Intent.EMAIL_DRAFTING,
        0.82,
    ),
    # Lead support
    (
        re.compile(
            r"\b(new (lead|prospect)|interested (customer|buyer)|sales inquiry|lead|prospect|qualify|capture)\b",
            re.IGNORECASE,
        ),
        Intent.LEAD_SUPPORT,
        0.8,
    ),
    # Document summary
    (
        re.compile(r"\b(summari[sz]e|summary of|tl;dr|key points)\b", re.IGNORECASE),
        Intent.DOCUMENT_SUMMARY,
        0.78,
    ),
    # Workflow action
    (
        re.compile(
            r"\b(update (?:the )?crm|sync to crm|send invoice|create ticket|approve)\b",
            re.IGNORECASE,
        ),
        Intent.WORKFLOW_ACTION,
        0.82,
    ),
    # Calendar availability
    (
        re.compile(
            r"\b(am i free|check (my )?availability|free tomorrow|busy tomorrow)\b",
            re.IGNORECASE,
        ),
        Intent.CALENDAR_AVAILABILITY,
        0.84,
    ),
    # Calendar scheduling
    (
        re.compile(
            r"\b(schedule|book a|book (the|an?)|suggest).{0,40}\b(meeting|slot|appointment)\b",
            re.IGNORECASE,
        ),
        Intent.CALENDAR_SCHEDULING,
        0.84,
    ),
    # Knowledge search (lower priority)
    (
        re.compile(
            r"\b(what|how|why|when|where|explain|tell me about|policy|docs?|guide|knowledge base)\b",
            re.IGNORECASE,
        ),
        Intent.KNOWLEDGE_SEARCH,
        0.7,
    ),
    (
        re.compile(r"\?\s*$"),
        Intent.KNOWLEDGE_SEARCH,
        0.55,
    ),
]

_LEGACY_OUT_OF_SCOPE_RULES: list[re.Pattern[str]] = [
    re.compile(r"\b(weather|joke|love poem|stock(s)? tip|crypto price)\b", re.IGNORECASE),
    re.compile(r"\b(write me a story|generate an image|sing a song)\b", re.IGNORECASE),
    re.compile(r"\b(murder|illegal|hack into|bypass authentication)\b", re.IGNORECASE),
]


def _classify_legacy(
    message: str,
    *,
    settings: Settings | None = None,
    llm: LLMProvider | None = None,
    use_llm: bool = False,
) -> IntentResult:
    """Legacy classification using keyword rules (backward compatibility).

    This path is used when message_class is not provided to the classify() function.
    """
    # Check out-of-scope first
    for pattern in _LEGACY_OUT_OF_SCOPE_RULES:
        if pattern.search(message):
            return IntentResult(
                intent=Intent.OUT_OF_SCOPE,
                confidence=0.9,
                source="rules",
                reason=f"legacy_out_of_scope:{pattern.pattern[:50]}",
            )

    # Try keyword rules
    for pattern, intent, conf in _LEGACY_KEYWORD_RULES:
        if pattern.search(message):
            return IntentResult(
                intent=intent,
                confidence=conf,
                source="rules",
                reason=f"legacy_match:{pattern.pattern[:50]}",
            )

    # Try LLM if enabled
    if use_llm:
        settings = settings or get_settings()
        if settings.has_openai:
            try:
                llm_result = _classify_with_llm(message, llm=llm or get_llm_provider(settings))
                return llm_result
            except Exception as exc:
                logger.warning("intent_llm_failed", error=str(exc))

    # Final fallback
    return IntentResult(
        intent=Intent.GENERAL_ASSISTANT,
        confidence=0.5,
        source="rules",
        reason="legacy_no_match",
    )


# JSON schema used for structured LLM intent calls.
_INTENT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [intent.value for intent in Intent],
        },
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["intent", "confidence"],
}


def _classify_with_llm(message: str, *, llm: LLMProvider) -> IntentResult:
    """Use LLM for intent classification (legacy path)."""
    if isinstance(llm, FallbackLLMProvider):
        # Use legacy classification when fallback provider is used
        return _classify_legacy(message)

    system = (
        "You classify user messages for a business productivity assistant. "
        f"Return one of: {', '.join(i.value for i in Intent)}. "
        "If the request is outside business productivity, return out_of_scope. "
        "If the request is ambiguous, return clarification."
    )
    response = llm.chat_structured(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        response_schema=_INTENT_SCHEMA,
    )
    try:
        payload = json.loads(response.content or "{}")
        intent = Intent(payload.get("intent"))
        confidence = float(payload.get("confidence", 0.6))
    except (ValueError, TypeError, json.JSONDecodeError):
        return _classify_legacy(message)

    return IntentResult(
        intent=intent,
        confidence=max(0.0, min(1.0, confidence)),
        source="llm",
        reason=str(payload.get("reason", "")),
    )


__all__ = ["classify", "IntentResult"]
