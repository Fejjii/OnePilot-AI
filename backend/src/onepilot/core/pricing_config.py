"""Configurable estimated pricing for usage-based billing.

Prices are estimates for capstone demos. Verify against provider pricing
before production billing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Currency = Literal["USD"]

# Per 1M tokens unless noted otherwise.
MODEL_TOKEN_PRICES: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
}

# Per minute of audio (whisper-1).
SPEECH_PRICE_PER_MINUTE: dict[str, float] = {
    "whisper-1": 0.006,
}

# Flat estimated costs for non-token features (USD).
FEATURE_FLAT_COSTS: dict[str, float] = {
    "rag_query": 0.0001,
    "document_upload": 0.001,
    "tool_call": 0.00005,
}

DEFAULT_CURRENCY: Currency = "USD"
FALLBACK_PROVIDER_COST = 0.0


@dataclass(frozen=True)
class PlanEntitlementConfig:
    """Included usage per billing period for a plan tier."""

    included_chat_messages: int
    included_rag_queries: int
    included_speech_minutes: int
    included_document_uploads: int
    included_storage_mb: int
    included_team_members: int
    base_price_cents: int
    overage_policy: str = "block_at_limit"  # placeholder: block | metered | unlimited


PLAN_ENTITLEMENTS: dict[str, PlanEntitlementConfig] = {
    "free": PlanEntitlementConfig(
        included_chat_messages=50,
        included_rag_queries=20,
        included_speech_minutes=10,
        included_document_uploads=5,
        included_storage_mb=100,
        included_team_members=1,
        base_price_cents=0,
    ),
    "pro": PlanEntitlementConfig(
        included_chat_messages=500,
        included_rag_queries=200,
        included_speech_minutes=120,
        included_document_uploads=50,
        included_storage_mb=1000,
        included_team_members=1,
        base_price_cents=2900,
    ),
    "team": PlanEntitlementConfig(
        included_chat_messages=2000,
        included_rag_queries=1000,
        included_speech_minutes=600,
        included_document_uploads=200,
        included_storage_mb=5000,
        included_team_members=10,
        base_price_cents=7900,
    ),
    "business": PlanEntitlementConfig(
        included_chat_messages=10000,
        included_rag_queries=5000,
        included_speech_minutes=3000,
        included_document_uploads=1000,
        included_storage_mb=25000,
        included_team_members=50,
        base_price_cents=19900,
    ),
}
