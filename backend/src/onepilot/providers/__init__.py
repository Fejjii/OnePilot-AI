"""Provider registry.

Returns real implementations when env keys are present, otherwise a mock or
deterministic fallback. The vector and embedding providers are memoized at
module scope so that data written during one request remains visible to
subsequent requests in the same process. This is required for the in-memory
fallback to behave correctly across upload, search, and answer calls
(especially in tests).
"""

from __future__ import annotations

import os

import structlog

from onepilot.core.config import Settings
from onepilot.providers.billing.base import BillingProvider
from onepilot.providers.calendar.base import CalendarProvider
from onepilot.providers.crm.base import CRMProvider
from onepilot.providers.email.base import EmailProvider
from onepilot.providers.embeddings.base import EmbeddingsProvider
from onepilot.providers.llm.base import LLMProvider
from onepilot.providers.search.base import SearchProvider
from onepilot.providers.vector.base import VectorProvider

log = structlog.get_logger(__name__)


_vector_singleton: VectorProvider | None = None
_embeddings_singleton: EmbeddingsProvider | None = None
_llm_singleton: LLMProvider | None = None


def reset_provider_cache() -> None:
    """Drop cached singletons; intended for test fixtures."""
    global _vector_singleton, _embeddings_singleton, _llm_singleton
    _vector_singleton = None
    _embeddings_singleton = None
    _llm_singleton = None


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

def get_llm_provider(settings: Settings) -> LLMProvider:
    global _llm_singleton
    if _llm_singleton is not None:
        return _llm_singleton

    if settings.has_openai:
        from onepilot.providers.llm.openai_provider import OPENAI_LLM_IMPLEMENTED

        if OPENAI_LLM_IMPLEMENTED:
            try:
                from onepilot.providers.llm.openai_provider import OpenAILLMProvider

                log.info("llm_provider.init", provider="openai", model=settings.OPENAI_MODEL)
                _llm_singleton = OpenAILLMProvider(
                    api_key=settings.OPENAI_API_KEY,
                    default_model=settings.OPENAI_MODEL,
                )
                return _llm_singleton
            except Exception as exc:
                log.warning(
                    "llm_provider.fallback",
                    reason=f"OpenAI initialization failed: {exc}",
                    provider="openai",
                )

        else:
            log.warning(
                "llm_provider.fallback",
                reason="OPENAI_API_KEY set but OpenAI LLM is not implemented",
            )
    else:
        log.warning("llm_provider.fallback", reason="OPENAI_API_KEY not set")

    from onepilot.providers.llm.fallback_provider import FallbackLLMProvider

    log.info("llm_provider.init", provider="fallback")
    _llm_singleton = FallbackLLMProvider()
    return _llm_singleton


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def get_embeddings_provider(settings: Settings) -> EmbeddingsProvider:
    global _embeddings_singleton
    if _embeddings_singleton is not None:
        return _embeddings_singleton

    if settings.has_openai:
        from onepilot.providers.embeddings.openai_embeddings import (
            OPENAI_EMBEDDINGS_IMPLEMENTED,
        )

        if OPENAI_EMBEDDINGS_IMPLEMENTED:
            try:
                from onepilot.providers.embeddings.openai_embeddings import (
                    OpenAIEmbeddingsProvider,
                )

                log.info("embeddings_provider.init", provider="openai", model=settings.OPENAI_EMBEDDING_MODEL)
                _embeddings_singleton = OpenAIEmbeddingsProvider(
                    api_key=settings.OPENAI_API_KEY,
                    default_model=settings.OPENAI_EMBEDDING_MODEL,
                )
                return _embeddings_singleton
            except Exception as exc:
                log.warning(
                    "embeddings_provider.fallback",
                    reason=f"OpenAI initialization failed: {exc}",
                    provider="openai",
                )

        else:
            log.warning(
                "embeddings_provider.fallback",
                reason="OPENAI_API_KEY set but OpenAI embeddings are not implemented",
            )
    else:
        log.warning("embeddings_provider.fallback", reason="OPENAI_API_KEY not set")

    from onepilot.providers.embeddings.fallback_embeddings import (
        FallbackEmbeddingsProvider,
    )

    log.info("embeddings_provider.init", provider="fallback")
    _embeddings_singleton = FallbackEmbeddingsProvider()
    return _embeddings_singleton


# ---------------------------------------------------------------------------
# Vector
# ---------------------------------------------------------------------------

def get_vector_provider(settings: Settings) -> VectorProvider:
    global _vector_singleton
    if _vector_singleton is not None:
        return _vector_singleton

    if settings.has_qdrant:
        from onepilot.providers.vector.qdrant_provider import QdrantVectorProvider

        log.info("vector_provider.init", provider="qdrant")
        _vector_singleton = QdrantVectorProvider(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        return _vector_singleton

    from onepilot.providers.vector.memory_vector_provider import MemoryVectorProvider

    log.warning("vector_provider.fallback", reason="QDRANT_URL not set")
    _vector_singleton = MemoryVectorProvider()
    return _vector_singleton


# ---------------------------------------------------------------------------
# CRM
# ---------------------------------------------------------------------------

def get_crm_provider() -> CRMProvider:
    hubspot_key = os.environ.get("HUBSPOT_API_KEY", "")
    if hubspot_key:
        from onepilot.providers.crm.hubspot_provider import HubSpotProvider

        log.info("crm_provider.init", provider="hubspot")
        return HubSpotProvider(api_key=hubspot_key)

    from onepilot.providers.crm.mock_hubspot_provider import MockHubSpotProvider

    log.warning("crm_provider.fallback", reason="HUBSPOT_API_KEY not set")
    return MockHubSpotProvider()


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def get_email_provider() -> EmailProvider:
    gmail_creds = os.environ.get("GMAIL_CREDENTIALS_JSON", "")
    if gmail_creds:
        from onepilot.providers.email.gmail_provider import GmailProvider

        log.info("email_provider.init", provider="gmail")
        return GmailProvider(credentials_json=gmail_creds)

    from onepilot.providers.email.mock_email_provider import MockEmailProvider

    log.warning("email_provider.fallback", reason="GMAIL_CREDENTIALS_JSON not set")
    return MockEmailProvider()


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def get_calendar_provider() -> CalendarProvider:
    gcal_creds = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS_JSON", "")
    if gcal_creds:
        from onepilot.providers.calendar.google_calendar_provider import GoogleCalendarProvider

        log.info("calendar_provider.init", provider="google_calendar")
        return GoogleCalendarProvider(credentials_json=gcal_creds)

    from onepilot.providers.calendar.mock_calendar_provider import MockCalendarProvider

    log.warning("calendar_provider.fallback", reason="GOOGLE_CALENDAR_CREDENTIALS_JSON not set")
    return MockCalendarProvider()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def get_search_provider(settings: Settings) -> SearchProvider:
    if settings.SERPER_API_KEY:
        from onepilot.providers.search.serper_provider import SerperSearchProvider

        log.info("search_provider.init", provider="serper")
        return SerperSearchProvider(api_key=settings.SERPER_API_KEY)

    from onepilot.providers.search.mock_search_provider import MockSearchProvider

    log.warning("search_provider.fallback", reason="SERPER_API_KEY not set")
    return MockSearchProvider()


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------

def get_billing_provider() -> BillingProvider:
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if stripe_key:
        from onepilot.providers.billing.stripe_provider import StripeProvider

        log.info("billing_provider.init", provider="stripe")
        return StripeProvider(api_key=stripe_key)

    from onepilot.providers.billing.mock_stripe_provider import MockStripeProvider

    log.warning("billing_provider.fallback", reason="STRIPE_SECRET_KEY not set")
    return MockStripeProvider()


__all__ = [
    "get_llm_provider",
    "get_embeddings_provider",
    "get_vector_provider",
    "get_crm_provider",
    "get_email_provider",
    "get_calendar_provider",
    "get_search_provider",
    "get_billing_provider",
    "reset_provider_cache",
    "BillingProvider",
    "CalendarProvider",
    "CRMProvider",
    "EmailProvider",
    "EmbeddingsProvider",
    "LLMProvider",
    "SearchProvider",
    "VectorProvider",
]
