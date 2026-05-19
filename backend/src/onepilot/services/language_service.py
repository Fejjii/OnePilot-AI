"""Lightweight language detection and response-language resolution.

Uses weighted deterministic heuristics first. Optionally calls OpenAI when
heuristics are ambiguous and an API key is configured.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from onepilot.core.config import Settings
from onepilot.core.constants import LanguageCode, LanguagePreference
from onepilot.core.logging import get_logger
from onepilot.services.facets import FACET_EXPANSION_TEMPLATES, detect_facets

logger = get_logger(__name__)

LOW_CONFIDENCE_THRESHOLD = 0.45
WEAK_EVIDENCE_MAX_CONFIDENCE = 0.60

# Tokens that should not influence language detection (brand names, etc.)
_STOP_TOKENS: frozenset[str] = frozenset(
    {
        "novaedge",
        "solutions",
        "solution",
    }
)

# Distinctive characters (higher weight) vs shared Romance accents (lower weight)
_UNIQUE_CHAR_MARKERS: dict[LanguageCode, tuple[str, ...]] = {
    LanguageCode.DE: ("ä", "ö", "ü", "ß"),
    LanguageCode.FR: ("ç", "œ", "æ", "ù", "û", "î", "ï"),
    LanguageCode.ES: ("ñ", "¿", "¡"),
}

_SHARED_ROMANCE_CHAR_MARKERS: tuple[str, ...] = (
    "á",
    "é",
    "í",
    "ó",
    "ú",
    "è",
    "ê",
    "ë",
    "à",
    "â",
)

# (token, weight) — higher weight = more distinctive for that language
_WEIGHTED_WORD_MARKERS: dict[LanguageCode, tuple[tuple[str, float], ...]] = {
    LanguageCode.DE: (
        ("welche", 4.0),
        ("welcher", 4.0),
        ("welches", 4.0),
        ("unterstützt", 4.0),
        ("unterstutzt", 3.5),
        ("integrationen", 3.5),
        ("dienste", 3.5),
        ("dienst", 3.0),
        ("bietet", 3.5),
        ("funktioniert", 3.5),
        ("rückerstattung", 4.0),
        ("ruckerstattung", 3.5),
        ("richtlinie", 3.5),
        ("wie", 2.0),
        ("was", 2.0),
        ("und", 1.0),
        ("der", 1.0),
        ("die", 1.0),
        ("das", 1.0),
        ("ist", 1.0),
        ("mit", 1.0),
        ("für", 1.5),
        ("nicht", 1.5),
    ),
    LanguageCode.FR: (
        ("quels", 4.0),
        ("quelles", 4.0),
        ("quelle", 4.0),
        ("quel", 3.5),
        ("intégrations", 4.0),
        ("integrations", 2.0),
        ("prises", 3.0),
        ("charge", 2.5),
        ("propose", 3.5),
        ("politique", 3.5),
        ("remboursement", 4.0),
        ("comment", 2.5),
        ("sont", 2.0),
        ("est", 1.5),
        ("avec", 1.5),
        ("pour", 1.5),
        ("les", 1.0),
        ("des", 1.0),
        ("une", 1.0),
        ("services", 1.5),
    ),
    LanguageCode.ES: (
        ("qué", 4.0),
        ("que", 2.0),
        ("cuál", 4.0),
        ("cual", 3.5),
        ("integraciones", 4.0),
        ("integracion", 3.5),
        ("admite", 3.5),
        ("servicios", 3.5),
        ("servicio", 3.0),
        ("ofrece", 3.5),
        ("política", 3.5),
        ("politica", 3.0),
        ("reembolso", 4.0),
        ("cómo", 2.5),
        ("como", 1.5),
        ("son", 2.0),
        ("es", 1.5),
        ("con", 1.5),
        ("para", 1.5),
        ("los", 1.0),
        ("las", 1.0),
    ),
    LanguageCode.EN: (
        ("what", 3.0),
        ("which", 3.0),
        ("how", 2.5),
        ("does", 2.5),
        ("support", 0.5),
        ("integrations", 0.5),
        ("services", 0.5),
        ("offer", 2.0),
        ("the", 1.0),
        ("you", 1.0),
        ("can", 1.0),
    ),
}


@dataclass(frozen=True, slots=True)
class LanguageDetectionResult:
    language: LanguageCode
    confidence: float
    method: str  # heuristic | openai | context_override


def _word_hit(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text.lower()))


def _char_hits(text: str, chars: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for ch in chars if ch in lowered)


def _score_language(text: str, lang: LanguageCode) -> float:
    """Weighted score for a single language."""
    lowered = text.lower()
    score = 0.0

    for token, weight in _WEIGHTED_WORD_MARKERS.get(lang, ()):
        if token in _STOP_TOKENS:
            continue
        if _word_hit(lowered, token):
            score += weight

    unique_chars = _UNIQUE_CHAR_MARKERS.get(lang, ())
    score += _char_hits(lowered, unique_chars) * 2.5

    if lang in (LanguageCode.FR, LanguageCode.ES):
        score += _char_hits(lowered, _SHARED_ROMANCE_CHAR_MARKERS) * 0.75

    return score


def detect_language_heuristic(text: str) -> LanguageDetectionResult:
    """Score languages from weighted character and word markers."""
    stripped = text.strip()
    if not stripped:
        return LanguageDetectionResult(
            language=LanguageCode.EN, confidence=0.0, method="heuristic"
        )

    scores: dict[LanguageCode, float] = {
        lang: _score_language(stripped, lang)
        for lang in (LanguageCode.DE, LanguageCode.FR, LanguageCode.ES, LanguageCode.EN)
    }

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_lang, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    if best_score <= 0:
        return LanguageDetectionResult(
            language=LanguageCode.EN, confidence=0.2, method="heuristic"
        )

    margin = best_score - second_score

    # Romance tie-break: prefer higher word-marker score over shared accents alone
    if margin < 1.0 and best_lang in (LanguageCode.FR, LanguageCode.ES):
        fr_word = sum(
            w for t, w in _WEIGHTED_WORD_MARKERS[LanguageCode.FR] if _word_hit(stripped, t)
        )
        es_word = sum(
            w for t, w in _WEIGHTED_WORD_MARKERS[LanguageCode.ES] if _word_hit(stripped, t)
        )
        if es_word > fr_word:
            best_lang = LanguageCode.ES
            best_score = scores[LanguageCode.ES]
            second_score = scores[LanguageCode.FR]
            margin = best_score - second_score
        elif fr_word > es_word:
            best_lang = LanguageCode.FR
            best_score = scores[LanguageCode.FR]
            second_score = scores[LanguageCode.ES]
            margin = best_score - second_score

    confidence = min(0.95, 0.35 + (best_score * 0.06) + (margin * 0.08))
    return LanguageDetectionResult(
        language=best_lang, confidence=confidence, method="heuristic"
    )


def detect_language_openai(text: str, settings: Settings) -> LanguageDetectionResult | None:
    """Optional LLM detection when heuristics are inconclusive."""
    if not settings.has_openai:
        return None
    try:
        from onepilot.providers import get_llm_provider

        llm = get_llm_provider(settings)
        response = llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Detect the language of the user message. "
                        "Reply with exactly one code: en, de, fr, or es."
                    ),
                },
                {"role": "user", "content": text[:500]},
            ],
            temperature=0.0,
            max_tokens=8,
        )
        raw = response.content.strip().lower()
        code = raw[:2] if raw[:2] in {"en", "de", "fr", "es"} else raw
        mapping = {
            "en": LanguageCode.EN,
            "de": LanguageCode.DE,
            "fr": LanguageCode.FR,
            "es": LanguageCode.ES,
        }
        if code in mapping:
            return LanguageDetectionResult(
                language=mapping[code], confidence=0.75, method="openai"
            )
    except Exception as exc:
        logger.warning("language_detection_openai_failed", error=str(exc))
    return None


def detect_language(
    text: str,
    *,
    settings: Settings | None = None,
    context_language: str | None = None,
) -> LanguageDetectionResult:
    """Detect user message language; prefer speech/context hint when provided."""
    if context_language:
        try:
            lang = LanguageCode(context_language.lower())
            return LanguageDetectionResult(
                language=lang, confidence=0.9, method="context_override"
            )
        except ValueError:
            pass

    heuristic = detect_language_heuristic(text)

    # Trust clear heuristic winners even when absolute confidence is moderate
    scores = {
        lang: _score_language(text, lang)
        for lang in (LanguageCode.DE, LanguageCode.FR, LanguageCode.ES, LanguageCode.EN)
    }
    ranked_scores = sorted(scores.values(), reverse=True)
    margin = ranked_scores[0] - ranked_scores[1] if len(ranked_scores) > 1 else ranked_scores[0]

    if heuristic.confidence >= 0.55 or margin >= 2.0:
        return heuristic

    if settings is not None:
        llm_result = detect_language_openai(text, settings)
        if llm_result is not None:
            return llm_result

    return heuristic


def resolve_response_language(
    preference: LanguagePreference | str,
    detected: LanguageCode | str,
    detection_confidence: float,
    *,
    low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> LanguageCode:
    """Pick the language the assistant should reply in."""
    pref = (
        preference
        if isinstance(preference, LanguagePreference)
        else LanguagePreference(str(preference).lower())
    )
    det = (
        detected
        if isinstance(detected, LanguageCode)
        else LanguageCode(str(detected).lower())
    )

    if pref != LanguagePreference.AUTO:
        return LanguageCode(pref.value)

    if detection_confidence < low_confidence_threshold:
        return LanguageCode.EN
    return det


def language_display_name(code: LanguageCode | str) -> str:
    names = {
        LanguageCode.EN: "English",
        LanguageCode.DE: "German",
        LanguageCode.FR: "French",
        LanguageCode.ES: "Spanish",
    }
    if isinstance(code, str):
        try:
            code = LanguageCode(code)
        except ValueError:
            return code
    return names.get(code, str(code))


def preference_display_name(pref: LanguagePreference | str) -> str:
    if str(pref).lower() == LanguagePreference.AUTO:
        return "Auto"
    return language_display_name(str(pref))


def build_english_retrieval_queries(
    query: str, detected: LanguageCode
) -> list[str]:
    """Build English retrieval query variants for non-English KB search.

    Uses facet detection plus language-aware keyword mapping. Deterministic —
    does not require an LLM.
    """
    if detected == LanguageCode.EN:
        return []

    queries: list[str] = []
    facet_result = detect_facets(query)

    for facet in facet_result.detected_facets:
        expansion = FACET_EXPANSION_TEMPLATES.get(facet, "").strip()
        if expansion:
            queries.append(f"{expansion} NovaEdge Solutions")

    if not queries:
        fallback = _fallback_english_expansion(query, detected)
        if fallback:
            queries.append(fallback)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(q)
    return unique


def _fallback_english_expansion(query: str, detected: LanguageCode) -> str | None:
    """Heuristic English expansion when no facets were detected."""
    lowered = query.lower()
    parts: list[str] = ["NovaEdge Solutions"]

    if detected == LanguageCode.DE:
        if any(w in lowered for w in ("integration", "unterstütz")):
            parts.insert(0, "supported integrations HubSpot Gmail Google Calendar")
        if any(w in lowered for w in ("dienst", "bietet", "service")):
            parts.insert(
                0,
                "services offered customer support lead qualification email triage",
            )
        if any(w in lowered for w in ("rückerstatt", "ruckerstatt", "richtlinie")):
            parts.insert(0, "refund policy cancellation reimbursement")
        if "onboarding" in lowered or "funktioniert" in lowered:
            parts.insert(0, "onboarding implementation setup getting started")
    elif detected == LanguageCode.FR:
        if any(w in lowered for w in ("intégr", "integr")):
            parts.insert(0, "supported integrations HubSpot Gmail Google Calendar")
        if any(w in lowered for w in ("service", "propose")):
            parts.insert(
                0,
                "services offered customer support lead qualification email triage "
                "internal knowledge search appointment booking",
            )
        if any(w in lowered for w in ("remboursement", "politique")):
            parts.insert(0, "refund policy cancellation reimbursement")
    elif detected == LanguageCode.ES:
        if any(w in lowered for w in ("integrac", "admite")):
            parts.insert(0, "supported integrations HubSpot Gmail Google Calendar")
        if any(w in lowered for w in ("servicio", "ofrece")):
            parts.insert(
                0,
                "services offered customer support lead qualification email triage",
            )
        if any(w in lowered for w in ("reembolso", "política", "politica")):
            parts.insert(0, "refund policy cancellation reimbursement")

    if len(parts) <= 1:
        return None
    return " ".join(parts)


def expand_query_for_retrieval(
    query: str,
    detected: LanguageCode,
    *,
    settings: Settings | None = None,
) -> str | None:
    """English query expansion for non-English retrieval (KB in English).

    Prefers deterministic facet-based expansion; optionally augments via LLM.
    """
    if detected == LanguageCode.EN:
        return None

    built = build_english_retrieval_queries(query, detected)
    if built:
        return built[0]

    if settings is None or not settings.has_openai:
        return _fallback_english_expansion(query, detected)

    try:
        from onepilot.providers import get_llm_provider

        llm = get_llm_provider(settings)
        response = llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate the following business question to concise English "
                        "for document search. Reply with only the English query."
                    ),
                },
                {"role": "user", "content": query[:800]},
            ],
            temperature=0.0,
            max_tokens=120,
        )
        english = response.content.strip()
        return english if english and english.lower() != query.lower() else None
    except Exception as exc:
        logger.warning("query_expansion_failed", error=str(exc))
        return _fallback_english_expansion(query, detected)


def cap_confidence_for_weak_evidence(confidence: float, *, weak_evidence: bool) -> float:
    """Ensure weak-evidence answers never report high confidence."""
    if weak_evidence:
        return min(confidence, WEAK_EVIDENCE_MAX_CONFIDENCE)
    return confidence


def response_language_instruction(code: LanguageCode | str) -> str:
    """System-prompt suffix instructing the model which language to use."""
    lang = code if isinstance(code, LanguageCode) else LanguageCode(str(code).lower())
    names = {
        LanguageCode.EN: "English",
        LanguageCode.DE: "German",
        LanguageCode.FR: "French",
        LanguageCode.ES: "Spanish",
    }
    name = names.get(lang, "English")
    return (
        f"Respond entirely in {name}. "
        "Keep source document titles and section names in their original language "
        "when citing; do not translate citation labels."
    )
