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
)

router = APIRouter(tags=["health"])


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
    llm_mode = ProviderMode.FALLBACK if llm_fallback else ProviderMode.LIVE
    llm_reason = None
    if llm_fallback:
        llm_reason = "OPENAI_API_KEY not set" if not settings.has_openai else "OpenAI LLM not implemented"
    
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
    embeddings_mode = ProviderMode.FALLBACK if embeddings_fallback else ProviderMode.LIVE
    embeddings_reason = None
    if embeddings_fallback:
        embeddings_reason = "OPENAI_API_KEY not set" if not settings.has_openai else "OpenAI embeddings not implemented"
    
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
    vector_mode = ProviderMode.FALLBACK if vector_fallback else ProviderMode.LIVE
    vector_reason = None
    if vector_fallback:
        vector_reason = "QDRANT_URL not set"
    
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
    redis_mode = ProviderMode.LIVE if redis_configured else ProviderMode.FALLBACK
    redis_reason = None if redis_configured else "REDIS_URL not set"
    
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
    langsmith_details = {}

    if not langsmith_configured:
        langsmith_reason = "LANGSMITH_API_KEY not set, using local trace steps"
        langsmith_details = {"fallback": "Local trace steps"}
    elif not settings.LANGSMITH_TRACING:
        langsmith_reason = "LANGSMITH_TRACING is false, using local trace steps"
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
    
    # Serper
    serper_provider = get_search_provider(settings)
    serper_configured = bool(settings.SERPER_API_KEY)
    serper_is_mock = "Mock" in serper_provider.__class__.__name__
    serper_mode = ProviderMode.LIVE if serper_configured else ProviderMode.MOCK
    serper_reason = None if serper_configured else "SERPER_API_KEY not set, using mock provider"
    
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
    
    # Gmail
    gmail_provider = get_email_provider()
    gmail_configured = bool(os.environ.get("GMAIL_CREDENTIALS_JSON", ""))
    gmail_is_mock = "Mock" in gmail_provider.__class__.__name__
    gmail_mode = ProviderMode.LIVE if gmail_configured else ProviderMode.MOCK
    gmail_reason = None if gmail_configured else "GMAIL_CREDENTIALS_JSON not set, using mock provider"
    
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
    
    # HubSpot
    hubspot_provider = get_crm_provider()
    hubspot_configured = bool(os.environ.get("HUBSPOT_API_KEY", ""))
    hubspot_is_mock = "Mock" in hubspot_provider.__class__.__name__
    hubspot_mode = ProviderMode.LIVE if hubspot_configured else ProviderMode.MOCK
    hubspot_reason = None if hubspot_configured else "HUBSPOT_API_KEY not set, using mock provider"
    
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
    
    # Google Calendar
    calendar_provider = get_calendar_provider()
    calendar_configured = bool(os.environ.get("GOOGLE_CALENDAR_CREDENTIALS_JSON", ""))
    calendar_is_mock = "Mock" in calendar_provider.__class__.__name__
    calendar_mode = ProviderMode.LIVE if calendar_configured else ProviderMode.MOCK
    calendar_reason = None if calendar_configured else "GOOGLE_CALENDAR_CREDENTIALS_JSON not set, using mock provider"
    
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
    
    # Twilio (not implemented yet, but show as missing)
    twilio_configured = bool(os.environ.get("TWILIO_API_KEY", ""))
    twilio_mode = ProviderMode.MOCK
    twilio_reason = "Provider adapter not implemented, mock only"
    
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
    
    # Stripe
    stripe_provider = get_billing_provider()
    stripe_configured = bool(os.environ.get("STRIPE_SECRET_KEY", ""))
    stripe_is_mock = "Mock" in stripe_provider.__class__.__name__
    stripe_mode = ProviderMode.LIVE if stripe_configured else ProviderMode.MOCK
    stripe_reason = None if stripe_configured else "STRIPE_SECRET_KEY not set, using mock provider"
    
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
    speech_reason = None if speech_configured else "OPENAI_API_KEY not set, speech transcription unavailable"
    
    diagnostics.append(
        ProviderDiagnostic(
            name="OpenAI Speech",
            category=ProviderCategory.SPEECH,
            configured=speech_configured,
            healthy=speech_configured,
            active=speech_configured,
            fallback_used=False,
            mode=speech_mode,
            model="whisper-1" if speech_configured else None,
            reason=speech_reason,
            last_checked_at=now,
            details={"provider": "openai"} if speech_configured else {},
        )
    )
    
    return ProviderDiagnosticResponse(
        providers=diagnostics,
        checked_at=now,
    )
