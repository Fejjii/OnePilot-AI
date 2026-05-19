"""Tests for language detection and response-language resolution."""

from __future__ import annotations

import pytest

from onepilot.core.constants import LanguageCode, LanguagePreference
from onepilot.services.language_service import (
    build_english_retrieval_queries,
    cap_confidence_for_weak_evidence,
    detect_language,
    detect_language_heuristic,
    resolve_response_language,
)

GERMAN_QUERIES = [
    "Welche Integrationen unterstützt NovaEdge Solutions?",
    "Welche Dienste bietet NovaEdge Solutions an?",
    "Wie funktioniert das Onboarding?",
    "Was ist die Rückerstattungsrichtlinie?",
]

FRENCH_QUERIES = [
    "Quels services propose NovaEdge Solutions?",
    "Quelles intégrations sont prises en charge?",
    "Quelle est la politique de remboursement?",
]

SPANISH_QUERIES = [
    "Qué integraciones admite NovaEdge Solutions?",
    "Qué servicios ofrece NovaEdge Solutions?",
    "Cuál es la política de reembolso?",
]


class TestLanguageDetectionHeuristic:
    def test_detects_english(self) -> None:
        result = detect_language_heuristic(
            "What services does NovaEdge Solutions offer?"
        )
        assert result.language == LanguageCode.EN
        assert result.confidence > 0

    @pytest.mark.parametrize("query", GERMAN_QUERIES)
    def test_detects_german(self, query: str) -> None:
        result = detect_language_heuristic(query)
        assert result.language == LanguageCode.DE, f"Expected de for: {query}"

    @pytest.mark.parametrize("query", FRENCH_QUERIES)
    def test_detects_french(self, query: str) -> None:
        result = detect_language_heuristic(query)
        assert result.language == LanguageCode.FR, f"Expected fr for: {query}"

    @pytest.mark.parametrize("query", SPANISH_QUERIES)
    def test_detects_spanish(self, query: str) -> None:
        result = detect_language_heuristic(query)
        assert result.language == LanguageCode.ES, f"Expected es for: {query}"

    def test_german_integration_not_french(self) -> None:
        result = detect_language_heuristic(
            "Welche Integrationen unterstützt NovaEdge Solutions?"
        )
        assert result.language == LanguageCode.DE
        assert result.language != LanguageCode.FR

    def test_uncertain_text_falls_back_to_english(self) -> None:
        result = detect_language_heuristic("12345 ???")
        assert result.language == LanguageCode.EN
        assert result.confidence < 0.5


class TestResolveResponseLanguage:
    def test_auto_mode_uses_detected(self) -> None:
        lang = resolve_response_language(
            LanguagePreference.AUTO,
            LanguageCode.DE,
            0.8,
        )
        assert lang == LanguageCode.DE

    def test_explicit_preference_overrides(self) -> None:
        lang = resolve_response_language(
            LanguagePreference.EN,
            LanguageCode.ES,
            0.9,
        )
        assert lang == LanguageCode.EN

    def test_explicit_german_overrides_english_input(self) -> None:
        lang = resolve_response_language(
            LanguagePreference.DE,
            LanguageCode.EN,
            0.95,
        )
        assert lang == LanguageCode.DE

    def test_low_confidence_auto_defaults_english(self) -> None:
        lang = resolve_response_language(
            LanguagePreference.AUTO,
            LanguageCode.FR,
            0.2,
        )
        assert lang == LanguageCode.EN


class TestDetectLanguage:
    def test_context_override_from_speech(self) -> None:
        result = detect_language(
            "hello",
            context_language="de",
        )
        assert result.language == LanguageCode.DE
        assert result.method == "context_override"


class TestEnglishRetrievalQueries:
    def test_german_integrations_expansion(self) -> None:
        queries = build_english_retrieval_queries(
            "Welche Integrationen unterstützt NovaEdge Solutions?",
            LanguageCode.DE,
        )
        assert queries
        combined = " ".join(queries).lower()
        assert "hubspot" in combined
        assert "integration" in combined

    def test_french_services_expansion(self) -> None:
        queries = build_english_retrieval_queries(
            "Quels services propose NovaEdge Solutions?",
            LanguageCode.FR,
        )
        assert queries
        combined = " ".join(queries).lower()
        assert "services" in combined
        assert "lead qualification" in combined or "customer support" in combined


class TestWeakEvidenceConfidenceCap:
    def test_caps_high_confidence(self) -> None:
        assert cap_confidence_for_weak_evidence(0.85, weak_evidence=True) <= 0.6

    def test_does_not_cap_when_not_weak(self) -> None:
        assert cap_confidence_for_weak_evidence(0.85, weak_evidence=False) == 0.85
