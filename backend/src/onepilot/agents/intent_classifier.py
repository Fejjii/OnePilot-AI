"""Intent classifier.

The classifier is deterministic by default — it inspects the user message
against a small, well-tested rule set and assigns one of the ``Intent`` values.
If OpenAI is configured we *could* (optionally) ask the LLM for a structured
JSON classification, but tests never depend on that path. Determinism is more
important than recall for a demo SaaS agent: every routing decision is
auditable and reproducible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import Intent
from onepilot.core.logging import get_logger
from onepilot.providers import get_llm_provider
from onepilot.providers.llm.base import LLMProvider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Rule set (deterministic fallback)
# ---------------------------------------------------------------------------

# Each rule is a (keyword regex, intent, confidence) tuple. The first match
# wins. Order matters; more specific intents should be listed before less
# specific ones (e.g. ``email`` before ``general``).

_KEYWORD_RULES: list[tuple[re.Pattern[str], Intent, float]] = [
    # Greetings / conversational openers — match first to avoid being eaten by
    # the "how/why/?" knowledge_search rule.
    (
        re.compile(
            r"^\s*(hi|hey|hello|yo|thanks|thank you|good (morning|afternoon|evening))\b",
            re.IGNORECASE,
        ),
        Intent.GENERAL_ASSISTANT,
        0.85,
    ),
    (
        re.compile(r"^\s*let'?s\s+(plan|brainstorm|chat|talk)\b", re.IGNORECASE),
        Intent.GENERAL_ASSISTANT,
        0.8,
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
    (
        re.compile(r"\b(follow[- ]?up|outreach|cold email|introduction email)\b", re.IGNORECASE),
        Intent.EMAIL_DRAFTING,
        0.78,
    ),
    # Lead support
    (
        re.compile(
            r"\b(new (lead|prospect)|interested (customer|buyer)|sales inquiry)\b",
            re.IGNORECASE,
        ),
        Intent.LEAD_SUPPORT,
        0.85,
    ),
    (
        re.compile(
            r"\b(lead|prospect|customer inquiry|qualify|capture)\b",
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
    # Workflow action (book / schedule / update CRM / send / approve)
    (
        re.compile(
            r"\b(schedule|book a|book (the|an?)|update (?:the )?crm|sync to crm"
            r"|send invoice|create ticket|approve)\b",
            re.IGNORECASE,
        ),
        Intent.WORKFLOW_ACTION,
        0.82,
    ),
    # Knowledge search (lower-priority, generic "wh-" questions)
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

# Out-of-scope rules — anything that clearly isn't business productivity.
_OUT_OF_SCOPE_RULES: list[re.Pattern[str]] = [
    re.compile(r"\b(weather|joke|love poem|stock(s)? tip|crypto price)\b", re.IGNORECASE),
    re.compile(r"\b(write me a story|generate an image|sing a song)\b", re.IGNORECASE),
    re.compile(r"\b(murder|illegal|hack into|bypass authentication)\b", re.IGNORECASE),
]

# Clarification rules — when the user message is too short or vague.
_MIN_CHARS_FOR_INTENT = 4


@dataclass(slots=True)
class IntentResult:
    intent: Intent
    confidence: float
    source: str  # "rules" or "llm"
    reason: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(
    message: str,
    *,
    settings: Settings | None = None,
    llm: LLMProvider | None = None,
    use_llm: bool = False,
) -> IntentResult:
    """Classify ``message`` into an :class:`Intent`.

    The default path is rule-based and deterministic. Pass ``use_llm=True``
    *and* configure ``OPENAI_API_KEY`` to optionally enable structured LLM
    classification (still falls back to rules on parse error).
    """
    cleaned = (message or "").strip()
    if len(cleaned) < _MIN_CHARS_FOR_INTENT:
        return IntentResult(
            intent=Intent.CLARIFICATION,
            confidence=0.6,
            source="rules",
            reason="message_too_short",
        )

    for pattern in _OUT_OF_SCOPE_RULES:
        if pattern.search(cleaned):
            return IntentResult(
                intent=Intent.OUT_OF_SCOPE,
                confidence=0.9,
                source="rules",
                reason=f"matched:{pattern.pattern}",
            )

    rule_result = _classify_with_rules(cleaned)

    if not use_llm:
        return rule_result

    settings = settings or get_settings()
    if not settings.has_openai:
        return rule_result

    try:
        llm_result = _classify_with_llm(cleaned, llm=llm or get_llm_provider(settings))
    except Exception as exc:  # pragma: no cover - LLM exceptions can be flaky
        logger.warning("intent_llm_failed", error=str(exc))
        return rule_result

    # Combine: if the LLM disagrees but rule was strong, trust rules; otherwise
    # trust LLM. This guards against hallucinated intents.
    if rule_result.confidence >= 0.8 and rule_result.intent != llm_result.intent:
        return rule_result
    return llm_result


def _classify_with_rules(message: str) -> IntentResult:
    for pattern, intent, conf in _KEYWORD_RULES:
        if pattern.search(message):
            return IntentResult(
                intent=intent,
                confidence=conf,
                source="rules",
                reason=f"matched:{pattern.pattern}",
            )
    return IntentResult(
        intent=Intent.GENERAL_ASSISTANT,
        confidence=0.5,
        source="rules",
        reason="no_match",
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
    if isinstance(llm, FallbackLLMProvider):
        return _classify_with_rules(message)

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
        return _classify_with_rules(message)

    return IntentResult(
        intent=intent,
        confidence=max(0.0, min(1.0, confidence)),
        source="llm",
        reason=str(payload.get("reason", "")),
    )
