from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.repositories.session import get_session
from onepilot.providers import (
    get_billing_provider,
    get_calendar_provider,
    get_crm_provider,
    get_email_provider,
    get_embeddings_provider,
    get_llm_provider,
    get_search_provider,
    get_vector_provider,
)
from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.providers.vector.memory_vector_provider import MemoryVectorProvider
from onepilot.schemas.runtime import (
    ProviderCategory,
    ProviderDiagnostic,
    ProviderDiagnosticResponse,
    ProviderMode,
    RuntimeModelConfigResponse,
)

router = APIRouter(tags=["health"])

_COST_NOTE = (
    "OpenAI chat and embedding usage is metered per token; speech transcription "
    "(Whisper) is metered per audio minute. Fallback and mock providers incur no "
    "external API cost. Configure models via environment variables."
)


def _openai_core_mode(*, configured: bool, using_fallback: bool) -> ProviderMode:
    if not configured:
        return ProviderMode.MISSING
    if using_fallback:
        return ProviderMode.FALLBACK
    return ProviderMode.LIVE


def _openai_core_status(*, configured: bool, using_fallback: bool) -> str:
    return _openai_core_mode(configured=configured, using_fallback=using_fallback).value


def _aggregate_provider_mode(
    *,
    llm_mode: ProviderMode,
    embeddings_mode: ProviderMode,
    vector_mode: ProviderMode,
    redis_mode: ProviderMode,
) -> str:
    core_modes = {llm_mode, embeddings_mode, vector_mode, redis_mode}
    if core_modes == {ProviderMode.LIVE}:
        return "live"
    if ProviderMode.LIVE in core_modes:
        return "mixed"
    return "demo"


@router.get("/runtime/config", response_model=RuntimeModelConfigResponse)
def runtime_model_config(
    settings: Settings = Depends(get_settings),
) -> RuntimeModelConfigResponse:
    """Expose safe, read-only model names and status for reviewers (no secrets)."""
    llm = get_llm_provider(settings)
    embeddings = get_embeddings_provider(settings)
    vector = get_vector_provider(settings)

    llm_fallback = isinstance(llm, FallbackLLMProvider)
    embeddings_fallback = isinstance(embeddings, FallbackEmbeddingsProvider)
    vector_fallback = isinstance(vector, MemoryVectorProvider)

    llm_mode = _openai_core_mode(configured=settings.has_openai, using_fallback=llm_fallback)
    embeddings_mode = _openai_core_mode(
        configured=settings.has_openai,
        using_fallback=embeddings_fallback,
    )
    vector_mode = (
        ProviderMode.MISSING if not settings.has_qdrant else ProviderMode.LIVE
    )
    if settings.has_qdrant and vector_fallback:
        vector_mode = ProviderMode.FALLBACK

    redis_mode = ProviderMode.MISSING if not settings.has_redis else ProviderMode.LIVE

    fallback_active = any(
        mode in {ProviderMode.FALLBACK, ProviderMode.MISSING}
        for mode in (llm_mode, embeddings_mode, vector_mode, redis_mode)
    )

    return RuntimeModelConfigResponse(
        chat_model=settings.OPENAI_MODEL,
        embedding_model=settings.OPENAI_EMBEDDING_MODEL,
        speech_model=settings.OPENAI_SPEECH_MODEL,
        llm_status=_openai_core_status(
            configured=settings.has_openai,
            using_fallback=llm_fallback,
        ),
        embeddings_status=_openai_core_status(
            configured=settings.has_openai,
            using_fallback=embeddings_fallback,
        ),
        speech_status="live" if settings.has_openai else "missing",
        fallback_active=fallback_active,
        provider_mode=_aggregate_provider_mode(
            llm_mode=llm_mode,
            embeddings_mode=embeddings_mode,
            vector_mode=vector_mode,
            redis_mode=redis_mode,
        ),
        cost_note=_COST_NOTE,
        configuration_source="environment",
    )


@router.get("/health")
def health_check(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "providers": {
            "openai": settings.has_openai,
            "qdrant": settings.has_qdrant,
            "redis": settings.has_redis,
            "langsmith": settings.has_langsmith,
            "database": bool(settings.DATABASE_URL),
        },
    }


@router.get("/providers", response_model=ProviderDiagnosticResponse)
def provider_diagnostics(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_session),
) -> ProviderDiagnosticResponse:
    """Comprehensive runtime and provider diagnostics."""
    
    now = datetime.now(timezone.utc)
    diagnostics: list[ProviderDiagnostic] = []
    
    # OpenAI LLM
    llm = get_llm_provider(settings)
    llm_fallback = isinstance(llm, FallbackLLMProvider)
    llm_mode = _openai_core_mode(
        configured=settings.has_openai,
        using_fallback=llm_fallback,
    )
    llm_reason = None
    if llm_mode == ProviderMode.MISSING:
        llm_reason = "OPENAI_API_KEY not set; deterministic fallback responses in use"
    elif llm_mode == ProviderMode.FALLBACK:
        llm_reason = "OpenAI LLM unavailable; deterministic fallback responses in use"
    
    diagnostics.append(
        ProviderDiagnostic(
            name="OpenAI LLM",
            category=ProviderCategory.LLM,
            configured=settings.has_openai,
            healthy=not llm_fallback,
            active=not llm_fallback,
            fallback_used=llm_fallback,
            mode=llm_mode,
            model=settings.OPENAI_MODEL if not llm_fallback else "fallback-v1",
            reason=llm_reason,
            last_checked_at=now,
            details={"provider": "openai" if not llm_fallback else "fallback"},
        )
    )
    
    # OpenAI Embeddings
    embeddings = get_embeddings_provider(settings)
    embeddings_fallback = isinstance(embeddings, FallbackEmbeddingsProvider)
    embeddings_mode = _openai_core_mode(
        configured=settings.has_openai,
        using_fallback=embeddings_fallback,
    )
    embeddings_reason = None
    if embeddings_mode == ProviderMode.MISSING:
        embeddings_reason = "OPENAI_API_KEY not set; hash-based fallback embeddings in use"
    elif embeddings_mode == ProviderMode.FALLBACK:
        embeddings_reason = "OpenAI embeddings unavailable; hash-based fallback embeddings in use"
    
    diagnostics.append(
        ProviderDiagnostic(
            name="OpenAI Embeddings",
            category=ProviderCategory.EMBEDDINGS,
            configured=settings.has_openai,
            healthy=not embeddings_fallback,
            active=not embeddings_fallback,
            fallback_used=embeddings_fallback,
            mode=embeddings_mode,
            model=settings.OPENAI_EMBEDDING_MODEL if not embeddings_fallback else "fallback-embeddings",
            reason=embeddings_reason,
            last_checked_at=now,
            details={
                "provider": "openai" if not embeddings_fallback else "fallback",
                "dimension": embeddings.dimension,
            },
        )
    )
    
    # Qdrant
    vector = get_vector_provider(settings)
    vector_fallback = isinstance(vector, MemoryVectorProvider)
    if not settings.has_qdrant:
        vector_mode = ProviderMode.MISSING
        vector_reason = "QDRANT_URL not set; in-memory vector store in use"
    elif vector_fallback:
        vector_mode = ProviderMode.FALLBACK
        vector_reason = "Qdrant unavailable; in-memory vector store in use"
    else:
        vector_mode = ProviderMode.LIVE
        vector_reason = None
    
    diagnostics.append(
        ProviderDiagnostic(
            name="Qdrant",
            category=ProviderCategory.VECTOR,
            configured=settings.has_qdrant,
            healthy=not vector_fallback,
            active=not vector_fallback,
            fallback_used=vector_fallback,
            mode=vector_mode,
            model=None,
            reason=vector_reason,
            last_checked_at=now,
            details={"provider": "qdrant" if not vector_fallback else "memory"},
        )
    )
    
    # Redis
    redis_configured = settings.has_redis
    redis_healthy = redis_configured
    redis_mode = ProviderMode.LIVE if redis_configured else ProviderMode.MISSING
    redis_reason = None if redis_configured else "REDIS_URL not set; process-local cache in use"
    
    if redis_configured:
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
        except Exception as exc:
            redis_healthy = False
            redis_mode = ProviderMode.UNHEALTHY
            redis_reason = f"Redis connection failed: {exc}"
    
    diagnostics.append(
        ProviderDiagnostic(
            name="Redis",
            category=ProviderCategory.CACHE,
            configured=redis_configured,
            healthy=redis_healthy,
            active=redis_configured and redis_healthy,
            fallback_used=not redis_configured,
            mode=redis_mode,
            model=None,
            reason=redis_reason,
            last_checked_at=now,
            details={"fallback": "Process-local cache"} if not redis_configured else None,
        )
    )
    
    # Postgres
    postgres_healthy = bool(settings.DATABASE_URL)
    postgres_mode = ProviderMode.LIVE
    postgres_reason = None
    
    if postgres_healthy:
        try:
            db.execute(text("SELECT 1"))
        except Exception as exc:
            postgres_healthy = False
            postgres_mode = ProviderMode.UNHEALTHY
            postgres_reason = f"Database connection failed: {exc}"
    
    diagnostics.append(
        ProviderDiagnostic(
            name="Postgres",
            category=ProviderCategory.DATABASE,
            configured=bool(settings.DATABASE_URL),
            healthy=postgres_healthy,
            active=postgres_healthy,
            fallback_used=False,
            mode=postgres_mode,
            model=None,
            reason=postgres_reason,
            last_checked_at=now,
            details=None,
        )
    )
    
    # LangSmith
    langsmith_configured = bool(settings.LANGSMITH_API_KEY)
    langsmith_active = settings.has_langsmith
    langsmith_healthy = True
    langsmith_mode = ProviderMode.LIVE if langsmith_active else ProviderMode.LOCAL
    langsmith_reason = None
    langsmith_details: dict[str, str | int | bool] = {}

    if not langsmith_configured:
        langsmith_mode = ProviderMode.MISSING
        langsmith_reason = "LANGSMITH_API_KEY not set; local trace steps only"
        langsmith_details = {"fallback": "Local trace steps"}
    elif not settings.LANGSMITH_TRACING:
        langsmith_mode = ProviderMode.LOCAL
        langsmith_reason = "LANGSMITH_TRACING is false; local trace steps only"
        langsmith_details = {"fallback": "Local trace steps"}
    else:
        # LangSmith is configured and enabled
        try:
            # Try to initialize to verify it's healthy
            from onepilot.observability.tracing import LangSmithTracingProvider

            provider = LangSmithTracingProvider(
                api_key=settings.LANGSMITH_API_KEY,
                project=settings.LANGSMITH_PROJECT,
                endpoint=settings.LANGSMITH_ENDPOINT if settings.LANGSMITH_ENDPOINT else None,
            )
            provider._ensure_initialized()
            langsmith_details = {
                "project": settings.LANGSMITH_PROJECT,
                "endpoint": settings.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com",
            }
        except ImportError:
            langsmith_healthy = False
            langsmith_mode = ProviderMode.UNHEALTHY
            langsmith_reason = "langsmith package not installed, using local trace steps"
            langsmith_details = {"fallback": "Local trace steps", "error": "missing langsmith package"}
        except Exception as exc:
            langsmith_healthy = False
            langsmith_mode = ProviderMode.UNHEALTHY
            langsmith_reason = f"LangSmith initialization failed: {exc}"
            langsmith_details = {"fallback": "Local trace steps", "error": str(exc)}

    diagnostics.append(
        ProviderDiagnostic(
            name="LangSmith",
            category=ProviderCategory.OBSERVABILITY,
            configured=langsmith_configured,
            healthy=langsmith_healthy,
            active=langsmith_active and langsmith_healthy,
            fallback_used=not (langsmith_active and langsmith_healthy),
            mode=langsmith_mode,
            model=None,
            reason=langsmith_reason,
            last_checked_at=now,
            details=langsmith_details if langsmith_details else None,
        )
    )
    
    # Serper (optional integration; never calls live search without credentials)
    serper_provider = get_search_provider(settings)
    serper_configured = bool(settings.SERPER_API_KEY)
    serper_is_mock = "Mock" in serper_provider.__class__.__name__
    if serper_configured and not serper_is_mock:
        serper_mode = ProviderMode.LIVE
        serper_reason = None
    elif serper_configured and serper_is_mock:
        serper_mode = ProviderMode.MOCK
        serper_reason = "SERPER_API_KEY set but mock adapter active (capstone demo)"
    else:
        serper_mode = ProviderMode.OPTIONAL
        serper_reason = "SERPER_API_KEY not set; web search is optional, mock results in demos"
    
    diagnostics.append(
        ProviderDiagnostic(
            name="Serper",
            category=ProviderCategory.SEARCH,
            configured=serper_configured,
            healthy=True,
            active=not serper_is_mock,
            fallback_used=serper_is_mock,
            mode=serper_mode,
            model=None,
            reason=serper_reason,
            last_checked_at=now,
            details={"mock": serper_is_mock},
        )
    )
    
    # Gmail (capstone-safe mock)
    gmail_provider = get_email_provider()
    gmail_configured = bool(os.environ.get("GMAIL_CREDENTIALS_JSON", ""))
    gmail_is_mock = "Mock" in gmail_provider.__class__.__name__
    gmail_mode = ProviderMode.MOCK
    gmail_reason = (
        "Mock Gmail adapter for capstone-safe demos"
        if gmail_is_mock
        else "Gmail credentials configured; mock adapter still used in this version"
    )
    
    diagnostics.append(
        ProviderDiagnostic(
            name="Gmail",
            category=ProviderCategory.EMAIL,
            configured=gmail_configured,
            healthy=True,
            active=not gmail_is_mock,
            fallback_used=gmail_is_mock,
            mode=gmail_mode,
            model=None,
            reason=gmail_reason,
            last_checked_at=now,
            details={"mock": gmail_is_mock},
        )
    )
    
    # HubSpot (capstone-safe mock)
    hubspot_provider = get_crm_provider()
    hubspot_configured = bool(os.environ.get("HUBSPOT_API_KEY", ""))
    hubspot_is_mock = "Mock" in hubspot_provider.__class__.__name__
    hubspot_mode = ProviderMode.MOCK
    hubspot_reason = (
        "Mock HubSpot adapter for capstone-safe demos"
        if hubspot_is_mock
        else "HubSpot API key configured; mock adapter still used in this version"
    )
    
    diagnostics.append(
        ProviderDiagnostic(
            name="HubSpot",
            category=ProviderCategory.CRM,
            configured=hubspot_configured,
            healthy=True,
            active=not hubspot_is_mock,
            fallback_used=hubspot_is_mock,
            mode=hubspot_mode,
            model=None,
            reason=hubspot_reason,
            last_checked_at=now,
            details={"mock": hubspot_is_mock},
        )
    )
    
    # Google Calendar (capstone-safe mock)
    calendar_provider = get_calendar_provider()
    calendar_configured = bool(os.environ.get("GOOGLE_CALENDAR_CREDENTIALS_JSON", ""))
    calendar_is_mock = "Mock" in calendar_provider.__class__.__name__
    calendar_mode = ProviderMode.MOCK
    calendar_reason = (
        "Mock Google Calendar adapter for capstone-safe demos"
        if calendar_is_mock
        else "Calendar credentials configured; mock adapter still used in this version"
    )
    
    diagnostics.append(
        ProviderDiagnostic(
            name="Google Calendar",
            category=ProviderCategory.CALENDAR,
            configured=calendar_configured,
            healthy=True,
            active=not calendar_is_mock,
            fallback_used=calendar_is_mock,
            mode=calendar_mode,
            model=None,
            reason=calendar_reason,
            last_checked_at=now,
            details={"mock": calendar_is_mock},
        )
    )
    
    # Twilio (capstone-safe mock)
    twilio_configured = bool(os.environ.get("TWILIO_API_KEY", ""))
    twilio_mode = ProviderMode.MOCK
    twilio_reason = "Mock Twilio adapter for capstone-safe demos (SMS not wired live)"
    
    diagnostics.append(
        ProviderDiagnostic(
            name="Twilio",
            category=ProviderCategory.SMS,
            configured=twilio_configured,
            healthy=True,
            active=False,
            fallback_used=True,
            mode=twilio_mode,
            model=None,
            reason=twilio_reason,
            last_checked_at=now,
            details={"mock": True},
        )
    )
    
    # Stripe (capstone-safe mock)
    stripe_provider = get_billing_provider()
    stripe_configured = bool(os.environ.get("STRIPE_SECRET_KEY", ""))
    stripe_is_mock = "Mock" in stripe_provider.__class__.__name__
    stripe_mode = ProviderMode.MOCK
    stripe_reason = (
        "Mock Stripe adapter for capstone-safe demos"
        if stripe_is_mock
        else "Stripe secret configured; mock adapter still used in this version"
    )
    
    diagnostics.append(
        ProviderDiagnostic(
            name="Stripe",
            category=ProviderCategory.BILLING,
            configured=stripe_configured,
            healthy=True,
            active=not stripe_is_mock,
            fallback_used=stripe_is_mock,
            mode=stripe_mode,
            model=None,
            reason=stripe_reason,
            last_checked_at=now,
            details={"mock": stripe_is_mock},
        )
    )
    
    # Multilingual support (application capability)
    diagnostics.append(
        ProviderDiagnostic(
            name="Multilingual Support",
            category=ProviderCategory.APPLICATION,
            configured=True,
            healthy=True,
            active=True,
            fallback_used=False,
            mode=ProviderMode.LIVE,
            model=None,
            reason=None,
            last_checked_at=now,
            details={
                "supported_languages": "en,de,fr,es",
                "preference_modes": "auto,en,de,fr,es",
                "kb_translation": False,
            },
        )
    )

    # OpenAI Speech (Whisper)
    speech_configured = settings.has_openai
    speech_mode = ProviderMode.LIVE if speech_configured else ProviderMode.MISSING
    speech_reason = (
        None
        if speech_configured
        else "OPENAI_API_KEY not set; speech transcription unavailable"
    )

    diagnostics.append(
        ProviderDiagnostic(
            name="OpenAI Speech",
            category=ProviderCategory.SPEECH,
            configured=speech_configured,
            healthy=speech_configured,
            active=speech_configured,
            fallback_used=False,
            mode=speech_mode,
            model=settings.OPENAI_SPEECH_MODEL if speech_configured else None,
            reason=speech_reason,
            last_checked_at=now,
            details={"provider": "openai"} if speech_configured else {},
        )
    )
    
    return ProviderDiagnosticResponse(
        providers=diagnostics,
        checked_at=now,
    )
