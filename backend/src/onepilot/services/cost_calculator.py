"""Central cost estimation for usage events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from onepilot.core.pricing_config import (
    DEFAULT_CURRENCY,
    FALLBACK_PROVIDER_COST,
    FEATURE_FLAT_COSTS,
    MODEL_TOKEN_PRICES,
    SPEECH_PRICE_PER_MINUTE,
)

_FALLBACK_PROVIDER_NAMES = frozenset(
    {
        "fallback",
        "fallbackllmprovider",
        "fallbackembeddingsprovider",
        "memoryvectorprovider",
        "mock",
    }
)


@dataclass
class CostEstimate:
    estimated_cost: float
    currency: str
    price_source: str
    calculation_breakdown: dict[str, Any] = field(default_factory=dict)


def _is_fallback_provider(provider: str | None) -> bool:
    if not provider:
        return False
    normalized = provider.lower().replace(" ", "")
    return any(token in normalized for token in _FALLBACK_PROVIDER_NAMES)


def _normalize_model(model: str | None) -> str | None:
    if not model:
        return None
    return model.strip().lower()


def _token_cost(model: str, input_tokens: int, output_tokens: int, embedding_tokens: int) -> tuple[float, dict[str, Any]]:
    prices = MODEL_TOKEN_PRICES.get(model)
    if not prices:
        return 0.0, {"reason": "unknown_model", "model": model}

    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    embed_cost = (embedding_tokens / 1_000_000) * prices.get("input", 0.0)
    total = input_cost + output_cost + embed_cost
    return total, {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "embedding_tokens": embedding_tokens,
        "input_cost": round(input_cost, 8),
        "output_cost": round(output_cost, 8),
        "embedding_cost": round(embed_cost, 8),
    }


def calculate_usage_cost(
    *,
    feature: str,
    provider: str | None = None,
    model: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    embedding_tokens: int = 0,
    audio_seconds: float = 0.0,
    tool_calls: int = 0,
    fallback_used: bool = False,
) -> CostEstimate:
    """Return estimated cost and breakdown for a usage event."""
    if fallback_used or _is_fallback_provider(provider):
        return CostEstimate(
            estimated_cost=FALLBACK_PROVIDER_COST,
            currency=DEFAULT_CURRENCY,
            price_source="fallback_zero",
            calculation_breakdown={
                "feature": feature,
                "provider": provider,
                "fallback_used": True,
            },
        )

    normalized_model = _normalize_model(model)
    breakdown: dict[str, Any] = {"feature": feature, "provider": provider, "model": normalized_model}
    total = 0.0
    price_source = "pricing_config"

    if normalized_model and (
        input_tokens > 0 or output_tokens > 0 or embedding_tokens > 0
    ):
        token_total, token_breakdown = _token_cost(
            normalized_model, input_tokens, output_tokens, embedding_tokens
        )
        total += token_total
        breakdown["token_pricing"] = token_breakdown

    if audio_seconds > 0:
        speech_model = normalized_model or "whisper-1"
        per_minute = SPEECH_PRICE_PER_MINUTE.get(speech_model, SPEECH_PRICE_PER_MINUTE["whisper-1"])
        minutes = audio_seconds / 60.0
        speech_cost = minutes * per_minute
        total += speech_cost
        breakdown["speech"] = {
            "model": speech_model,
            "audio_seconds": audio_seconds,
            "minutes": round(minutes, 6),
            "per_minute": per_minute,
            "cost": round(speech_cost, 8),
        }

    if feature in {"rag_queries", "rag_query"} and total == 0.0:
        flat = FEATURE_FLAT_COSTS["rag_query"]
        total += flat
        breakdown["flat_feature"] = {"key": "rag_query", "cost": flat}

    if feature in {"document_uploads", "document_upload"} and total == 0.0:
        flat = FEATURE_FLAT_COSTS["document_upload"]
        total += flat
        breakdown["flat_feature"] = {"key": "document_upload", "cost": flat}

    if tool_calls > 0:
        tool_cost = tool_calls * FEATURE_FLAT_COSTS["tool_call"]
        total += tool_cost
        breakdown["tool_calls"] = {"count": tool_calls, "cost": round(tool_cost, 8)}

    return CostEstimate(
        estimated_cost=round(total, 8),
        currency=DEFAULT_CURRENCY,
        price_source=price_source,
        calculation_breakdown=breakdown,
    )
