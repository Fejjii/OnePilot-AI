"""Message class classifier (Stage 1 of routing).

This module provides semantic, generalizable classification of user messages into
high-level message classes. It uses scored semantic indicators rather than
hardcoded phrase matching to ensure robustness across different wordings.

The classifier is deterministic and rule-based for auditability and reproducibility.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from onepilot.core.constants import MessageClass
from onepilot.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Semantic indicator patterns
# ---------------------------------------------------------------------------

# Each pattern group scores presence of semantic indicators for a message class.
# Higher score = stronger signal for that class.

# Capability/Help indicators
_CAPABILITY_PATTERNS = [
    # Assistant/system references (only when not talking about business services)
    (re.compile(r"\bassistant\b", re.IGNORECASE), 1.5),
    (re.compile(r"\bonepilot\b", re.IGNORECASE), 2.0),
    # Help/capability/feature questions (assistant-focused)
    (
        re.compile(
            r"\bwhat (can|do|does) (you|this|the assistant)\b.*\b(do|help|assist)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
    (
        re.compile(
            r"\b(help|capability|capabilities|feature|features|tool|tools|function|functions"
            r"|able to|available)(\s+me|\s+you|\s+do)?\b",
            re.IGNORECASE,
        ),
        2.0,
    ),
    # Direct capability questions
    (re.compile(r"\bshow me what (you can|this can)\b", re.IGNORECASE), 2.5),
]

# Conversational indicators
_CONVERSATIONAL_PATTERNS = [
    # Greetings (even very short ones)
    (re.compile(r"^\s*(hi|hey|hello|yo|sup|howdy|greetings)(\s|!|\.|\?|$)", re.IGNORECASE), 3.5),
    # Thanks
    (re.compile(r"\b(thanks?|thank you|thx|appreciate|grateful)\b", re.IGNORECASE), 2.5),
    # Acknowledgments (even short ones)
    (re.compile(r"^\s*(ok|okay|got it|sure|alright|sounds good|perfect)(\s|!|\.|\?|$)", re.IGNORECASE), 3.0),
    # Small talk
    (
        re.compile(
            r"\b(how are you|how'?s (it going|your day)|nice to meet|good (morning|afternoon|evening))\b",
            re.IGNORECASE,
        ),
        2.5,
    ),
    # Testing/checking (do not match email addresses like test@example.com)
    (
        re.compile(
            r"\b(test|testing)\b(?!@)"
            r"|\b(can you (hear|read|see) me|are you (there|listening))\b",
            re.IGNORECASE,
        ),
        2.0,
    ),
]

_EMAIL_DRAFT_WORKFLOW = re.compile(
    r"\b(draft|write|compose|reply to)\b.{0,160}\b(email|message|mail)\b",
    re.IGNORECASE | re.DOTALL,
)

# Correction/Meta indicators
_CORRECTION_META_PATTERNS = [
    # Correction phrases
    (
        re.compile(
            r"\b(not (what|a|the)|wrong|mistake|incorrect|misunderstood|off[-\s]?track"
            r"|that'?s not|doesn'?t (help|work|make sense)|this is not)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
    # Cancellation/direction change
    (
        re.compile(
            r"^\s*(nevermind|never mind|forget (it|that)|skip|actually|wait|hold on|stop|cancel)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
    # Meta conversation
    (re.compile(r"\b(unrelated|different (topic|subject)|change (topic|subject)|back to)\b", re.IGNORECASE), 2.5),
]

# Multi-step workflow: external research + email + calendar
_COMPOUND_WORKFLOW_PATTERN = re.compile(
    r"(?=.*\b(find|research|search).{0,80}\b(trend|trends|market|news)\b)"
    r"(?=.*\b(draft|write|compose).{0,60}\b(email|mail|message)\b)"
    r"(?=.*\b(schedule|book).{0,60}\b(meeting|call|appointment)\b)",
    re.IGNORECASE | re.DOTALL,
)

# External / current web research indicators
_EXTERNAL_RESEARCH_PATTERNS = [
    (
        re.compile(
            r"\b(search the web|web search|google search|look up online)\b",
            re.IGNORECASE,
        ),
        3.5,
    ),
    (
        re.compile(
            r"\b(bitcoin|btc|ethereum|eth|crypto(currency)?|stock price|share price|market price)\b",
            re.IGNORECASE,
        ),
        3.5,
    ),
    (re.compile(r"\b(recent|latest|current|up[- ]?to[- ]?date)\b", re.IGNORECASE), 2.5),
    (re.compile(r"\b(news|headline|press release)\b", re.IGNORECASE), 2.5),
    (
        re.compile(
            r"\b(market trends?|industry trends?|competitor research|benchmarks?)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
    (
        re.compile(
            r"\b(external research|web search|live information|public web)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
    (
        re.compile(
            r"\b(find|research|search).{0,40}\b(trends?|news|market|competitors?)\b",
            re.IGNORECASE,
        ),
        2.5,
    ),
    (
        re.compile(
            r"\bcompare\b.{0,60}\b(market trends?|industry trends?)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
]

# Business knowledge indicators
_BUSINESS_KNOWLEDGE_PATTERNS = [
    # Business entity/topic terms - even with "you/your"
    (
        re.compile(
            r"\b(company|business|organization|service|services|product|products"
            r"|offering|offerings|solution|solutions)\b",
            re.IGNORECASE,
        ),
        2.5,  # Increased weight
    ),
    # Policy/documentation terms
    (
        re.compile(
            r"\b(policy|policies|guide|guides|documentation|docs?|knowledge base"
            r"|faq|manual|handbook|procedure|process)\b",
            re.IGNORECASE,
        ),
        2.5,
    ),
    # Business domains
    # Generic product/pricing questions (internal by default in demo context)
    (
        re.compile(
            r"\b(how much (does|do)|what (does|do)|what('s| is) the cost|pricing tiers?)\b",
            re.IGNORECASE,
        ),
        2.5,
    ),
    (
        re.compile(
            r"\b(pricing|refund|payment|billing|subscription"
            r"|integration|integrations|api|support|security|privacy"
            r"|onboarding|setup|configuration|deployment|escalation)\b",
            re.IGNORECASE,
        ),
        3.0,  # Increased weight
    ),
    # Internal price/cost questions (avoid matching public market prices)
    (
        re.compile(
            r"\b(our|your|novaedge|company|plan|service).{0,40}\b(price|pricing|cost)\b"
            r"|\b(price|pricing|cost).{0,40}\b(our|your|novaedge|plan|service|subscription)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
    # Search/explain intent with business context
    (
        re.compile(
            r"\b(what|how|why|when|where|explain|tell me about|describe|details? about)\b.*\b(service|integration|policy|pricing|support|onboarding)\b",
            re.IGNORECASE,
        ),
        2.5,
    ),
    # "Your/you" in business context (e.g., "your services", "your pricing")
    (
        re.compile(
            r"\b(your|you)\b.{0,50}\b(service|product|solution|pricing|policy|integration|api|platform|system)\b",
            re.IGNORECASE,
        ),
        2.0,
    ),
    # Multilingual business knowledge (German, French, Spanish)
    (
        re.compile(
            r"\b(integrationen?|intégrations?|integraciones?|unterstützt|unterstütz|"
            r"bietet|propose|ofrece|admite|richtlinie|politique|política|politica|"
            r"rückerstatt|ruckerstatt|remboursement|reembolso|dienstleistungen?|servicios?)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
    (
        re.compile(
            r"\b(welche|quelle|quelles?|cuáles?|qué|wie|comment|como|cómo)\b",
            re.IGNORECASE,
        ),
        1.5,
    ),
]

# Workflow/action indicators
_WORKFLOW_PATTERNS = [
    # Action verbs
    (
        re.compile(
            r"\b(draft|write|compose|create|update|schedule|book|send|approve|reject"
            r"|qualify|capture|save|store|remember|log|summarize|sync|set up)\b",
            re.IGNORECASE,
        ),
        2.0,
    ),
    # Business objects + customer/lead context
    (
        re.compile(
            r"\b(email|message|mail|reply|lead|prospect|customer|meeting|appointment"
            r"|crm|ticket|invoice|document|report|summary|call)\b",
            re.IGNORECASE,
        ),
        1.5,
    ),
    # Customer/lead mentions (e.g., "new customer", "interested customer")
    (
        re.compile(
            r"\b(new|interested|potential)\s+(customer|lead|prospect|client)\b",
            re.IGNORECASE,
        ),
        2.5,
    ),
    # Combined action + object
    (
        re.compile(
            r"\b(draft|write|compose).*(email|message|mail)"
            r"|\b(create|update|qualify|capture).*(lead|prospect)"
            r"|\b(schedule|book|set up).*(meeting|appointment|call)"
            r"|\b(approve|reject).*(request|action|proposal)"
            r"|\b(summarize|key points).*(document|report|this)"
            r"|\b(am i free|are we free|check (my )?availability|free tomorrow|busy tomorrow)"
            r"|\b(suggest|propose|offer|recommend).*(slot|time|times|meeting)\b",
            re.IGNORECASE,
        ),
        3.0,
    ),
]

# Out-of-scope indicators
_OUT_OF_SCOPE_PATTERNS = [
    (
        re.compile(
            r"\b(weather|joke|love poem|story|song|game|play|entertain"
            r"|stock\s+tip|lottery|gambling)\b",
            re.IGNORECASE,
        ),
        3.5,
    ),
    (
        re.compile(
            r"\b(write (me )?a (story|poem|song)|generate an? image|draw|paint"
            r"|sing|tell (me )?a joke)\b",
            re.IGNORECASE,
        ),
        3.5,
    ),
    (
        re.compile(
            r"\b(murder|kill|harm|illegal|hack into|bypass authentication|exploit)\b",
            re.IGNORECASE,
        ),
        4.0,
    ),
]

# Deterministic pre-routing: internal NovaEdge KB vs external current facts
_INTERNAL_BUSINESS_CONTEXT = re.compile(
    r"\b("
    r"novaedge|our\b|we\b|company|knowledge base|"
    r"refund policy|pricing plan|subscription plan|pro plan|team plan|"
    r"your (service|product|solution|pricing|policy|plan|refund|support|onboarding|security)"
    r")\b",
    re.IGNORECASE,
)

_UNSAFE_REQUEST = re.compile(
    r"\b("
    r"stock\s+tips?|financial advice|"
    r"ignore\s+(previous|all|your)\s+instructions|"
    r"reveal\s+(system\s+secrets?|your\s+system\s+prompt)|"
    r"print\s+environment(\s+variable)?s?|"
    r"google\s+refresh\s+tokens?|refresh\s+tokens?|"
    r"railway\s+variables?|vercel\s+variables?|"
    r"oauth\s+secrets?|client\s+secrets?|provider\s+credentials?"
    r")\b",
    re.IGNORECASE,
)

_EXTERNAL_FACT_ENTITY = re.compile(
    r"\b("
    r"bitcoin|btc|ethereum|eth|dogecoin|solana|"
    r"crypto(currency)?s?|"
    r"stock\s+(price|prices|market)|share\s+(price|prices)|"
    r"commodit(y|ies)|gold|silver|oil|barrel|baril|pétrole|petrole|"
    r"nasdaq|s&p|forex|exchange rate|"
    r"tesla|apple|microsoft|google|amazon|nvidia"
    r")\b",
    re.IGNORECASE,
)

_MULTILINGUAL_EXTERNAL_FACT = re.compile(
    r"\b("
    r"température|temperature|météo|meteo|wetter|temperatur|"
    r"prix|preis|precio|baril|pétrole|petrole|ölpreis|olpreis|"
    r"actualité|actualite|aktuell|actuel|cours|kurs|"
    r"action|aktie|bitcoin|crypto|marché|marche|börse|borse"
    r")\b",
    re.IGNORECASE,
)

_CURRENT_FACT_CUE = re.compile(
    r"\b("
    r"aujourd'hui|aujourd hui|today|heute|now|current|latest|"
    r"right now|en ce moment|gerade"
    r")\b",
    re.IGNORECASE,
)

# Minimum message length for classification
_MIN_CHARS_FOR_CLASSIFICATION = 4

# Thresholds for classification
_SCORE_THRESHOLD_HIGH = 2.8  # Strong signal (lowered slightly)
_SCORE_THRESHOLD_MEDIUM = 2.0  # Medium signal
_SCORE_THRESHOLD_LOW = 1.5  # Weak signal


@dataclass(slots=True)
class MessageClassResult:
    """Result of message classification."""

    message_class: MessageClass
    confidence: float
    reason: str
    scores: dict[MessageClass, float]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_message(message: str) -> MessageClassResult:
    """Classify a user message into a high-level MessageClass.

    Uses semantic scoring rather than exact phrase matching for robustness.
    Priority order:
    1. Out of scope (highest priority)
    2. Correction/meta
    3. Conversational
    4. Capability/help
    5. Workflow request
    6. Business knowledge
    7. Unclear (fallback)

    Args:
        message: The user message to classify

    Returns:
        MessageClassResult with classification, confidence, and scoring details
    """
    cleaned = (message or "").strip()

    # Very short messages: check if they're greetings/acknowledgments first
    if len(cleaned) < _MIN_CHARS_FOR_CLASSIFICATION:
        # Check if it's a very short greeting or acknowledgment
        for pattern, _ in _CONVERSATIONAL_PATTERNS:
            if pattern.search(cleaned):
                return MessageClassResult(
                    message_class=MessageClass.CONVERSATIONAL,
                    confidence=0.75,
                    reason="short_conversational",
                    scores={},
                )
        # Otherwise, it's too short to classify
        return MessageClassResult(
            message_class=MessageClass.UNCLEAR,
            confidence=0.6,
            reason="message_too_short",
            scores={},
        )

    # Deterministic pre-routing before semantic scoring
    if _UNSAFE_REQUEST.search(cleaned):
        return MessageClassResult(
            message_class=MessageClass.OUT_OF_SCOPE,
            confidence=0.92,
            reason="unsafe_or_disallowed_request",
            scores={},
        )

    if _looks_like_external_current_facts(cleaned):
        return MessageClassResult(
            message_class=MessageClass.EXTERNAL_RESEARCH,
            confidence=0.9,
            reason="external_current_facts_heuristic",
            scores={},
        )

    if _EMAIL_DRAFT_WORKFLOW.search(cleaned):
        return MessageClassResult(
            message_class=MessageClass.WORKFLOW_REQUEST,
            confidence=0.9,
            reason="email_draft_workflow_heuristic",
            scores={},
        )

    # Calculate scores for each message class
    scores: dict[MessageClass, float] = {
        MessageClass.OUT_OF_SCOPE: _score_patterns(cleaned, _OUT_OF_SCOPE_PATTERNS),
        MessageClass.CORRECTION_OR_META: _score_patterns(cleaned, _CORRECTION_META_PATTERNS),
        MessageClass.CONVERSATIONAL: _score_patterns(cleaned, _CONVERSATIONAL_PATTERNS),
        MessageClass.CAPABILITY_OR_HELP: _score_patterns(cleaned, _CAPABILITY_PATTERNS),
        MessageClass.EXTERNAL_RESEARCH: _score_patterns(cleaned, _EXTERNAL_RESEARCH_PATTERNS),
        MessageClass.WORKFLOW_REQUEST: _score_patterns(cleaned, _WORKFLOW_PATTERNS),
        MessageClass.BUSINESS_KNOWLEDGE: _score_patterns(cleaned, _BUSINESS_KNOWLEDGE_PATTERNS),
    }

    # Apply priority-based classification
    # 1. Out of scope (highest priority)
    if scores[MessageClass.OUT_OF_SCOPE] >= _SCORE_THRESHOLD_HIGH:
        return MessageClassResult(
            message_class=MessageClass.OUT_OF_SCOPE,
            confidence=_score_to_confidence(scores[MessageClass.OUT_OF_SCOPE]),
            reason="out_of_scope_indicators",
            scores=scores,
        )

    # 2. Correction/meta (high priority to catch user feedback early)
    if scores[MessageClass.CORRECTION_OR_META] >= _SCORE_THRESHOLD_MEDIUM:
        return MessageClassResult(
            message_class=MessageClass.CORRECTION_OR_META,
            confidence=_score_to_confidence(scores[MessageClass.CORRECTION_OR_META]),
            reason="correction_or_meta_indicators",
            scores=scores,
        )

    # 3. Conversational (greetings, thanks, acknowledgments)
    if scores[MessageClass.CONVERSATIONAL] >= _SCORE_THRESHOLD_MEDIUM:
        return MessageClassResult(
            message_class=MessageClass.CONVERSATIONAL,
            confidence=_score_to_confidence(scores[MessageClass.CONVERSATIONAL]),
            reason="conversational_indicators",
            scores=scores,
        )

    # 4. Compound multi-tool workflow (before web-only external research)
    if _COMPOUND_WORKFLOW_PATTERN.search(cleaned):
        return MessageClassResult(
            message_class=MessageClass.WORKFLOW_REQUEST,
            confidence=0.9,
            reason="compound_workflow_indicators",
            scores=scores,
        )

    # 5. External web research (before internal business knowledge)
    if scores[MessageClass.EXTERNAL_RESEARCH] >= _SCORE_THRESHOLD_MEDIUM:
        return MessageClassResult(
            message_class=MessageClass.EXTERNAL_RESEARCH,
            confidence=_score_to_confidence(scores[MessageClass.EXTERNAL_RESEARCH]),
            reason="external_research_indicators",
            scores=scores,
        )

    # 5. Capability/help questions (before general knowledge search)
    if scores[MessageClass.CAPABILITY_OR_HELP] >= _SCORE_THRESHOLD_MEDIUM:
        # Disambiguate: "What services do you offer?" vs "What can you do for me?"
        # If business knowledge is also medium/strong, prefer business knowledge
        if scores[MessageClass.BUSINESS_KNOWLEDGE] >= _SCORE_THRESHOLD_MEDIUM:
            return MessageClassResult(
                message_class=MessageClass.BUSINESS_KNOWLEDGE,
                confidence=_score_to_confidence(scores[MessageClass.BUSINESS_KNOWLEDGE]),
                reason="business_knowledge_trumps_capability",
                scores=scores,
            )
        return MessageClassResult(
            message_class=MessageClass.CAPABILITY_OR_HELP,
            confidence=_score_to_confidence(scores[MessageClass.CAPABILITY_OR_HELP]),
            reason="capability_or_help_indicators",
            scores=scores,
        )

    # 6. Workflow request (actions on business objects)
    if scores[MessageClass.WORKFLOW_REQUEST] >= _SCORE_THRESHOLD_HIGH:
        return MessageClassResult(
            message_class=MessageClass.WORKFLOW_REQUEST,
            confidence=_score_to_confidence(scores[MessageClass.WORKFLOW_REQUEST]),
            reason="workflow_request_indicators",
            scores=scores,
        )

    # 7. Business knowledge (lower threshold, but must have some signal)
    if scores[MessageClass.BUSINESS_KNOWLEDGE] >= _SCORE_THRESHOLD_LOW:
        return MessageClassResult(
            message_class=MessageClass.BUSINESS_KNOWLEDGE,
            confidence=_score_to_confidence(scores[MessageClass.BUSINESS_KNOWLEDGE]),
            reason="business_knowledge_indicators",
            scores=scores,
        )

    # 8. Fallback: unclear if no strong signals
    max_score = max(scores.values()) if scores else 0.0
    if max_score < _SCORE_THRESHOLD_LOW:
        return MessageClassResult(
            message_class=MessageClass.UNCLEAR,
            confidence=0.5,
            reason="no_strong_indicators",
            scores=scores,
        )

    # Edge case: some signal but not enough for classification
    best_class = max(scores, key=scores.get)  # type: ignore[arg-type]
    return MessageClassResult(
        message_class=best_class,
        confidence=0.6,
        reason="weak_indicators",
        scores=scores,
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _looks_like_external_current_facts(message: str) -> bool:
    """Route public/current-fact questions to web search instead of internal KB."""
    if _INTERNAL_BUSINESS_CONTEXT.search(message):
        return False
    if _EXTERNAL_FACT_ENTITY.search(message):
        return True
    if _MULTILINGUAL_EXTERNAL_FACT.search(message) and _CURRENT_FACT_CUE.search(message):
        return True
    if _MULTILINGUAL_EXTERNAL_FACT.search(message) and re.search(
        r"\b(berlin|paris|london|new york|tokyo|münchen|munich|frankfurt)\b",
        message,
        re.IGNORECASE,
    ):
        return True
    return False


def _score_patterns(message: str, patterns: list[tuple[re.Pattern[str], float]]) -> float:
    """Score a message against a list of patterns.

    Args:
        message: The message to score
        patterns: List of (pattern, score) tuples

    Returns:
        Total score (sum of all matching pattern scores)
    """
    score = 0.0
    for pattern, weight in patterns:
        if pattern.search(message):
            score += weight
    return score


def _score_to_confidence(score: float) -> float:
    """Convert a raw score to a confidence value between 0.0 and 1.0.

    Uses a sigmoid-like transformation to map scores to confidence.
    Higher scores = higher confidence, capped at 0.95.

    Args:
        score: Raw pattern matching score

    Returns:
        Confidence value between 0.0 and 1.0
    """
    if score >= 5.0:
        return 0.95
    elif score >= 4.0:
        return 0.90
    elif score >= 3.0:
        return 0.85
    elif score >= 2.5:
        return 0.80
    elif score >= 2.0:
        return 0.75
    elif score >= 1.5:
        return 0.70
    elif score >= 1.0:
        return 0.65
    else:
        return 0.60


__all__ = ["classify_message", "MessageClassResult"]
