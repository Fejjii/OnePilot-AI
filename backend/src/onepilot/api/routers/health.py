from __future__ import annotations

from fastapi import APIRouter, Depends

from onepilot.core.config import Settings, get_settings
from onepilot.providers import (
    get_embeddings_provider,
    get_llm_provider,
    get_vector_provider,
)
from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.providers.vector.memory_vector_provider import MemoryVectorProvider

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


@router.get("/providers")
def provider_status(settings: Settings = Depends(get_settings)) -> dict:
    """Detailed provider status and diagnostics."""
    
    # Check LLM provider
    llm = get_llm_provider(settings)
    llm_fallback = isinstance(llm, FallbackLLMProvider)
    llm_status = {
        "configured": settings.has_openai,
        "active": not llm_fallback,
        "fallback_used": llm_fallback,
        "provider": "openai" if not llm_fallback else "fallback",
        "model": settings.OPENAI_MODEL if not llm_fallback else "fallback-v1",
    }
    if llm_fallback:
        llm_status["reason"] = "OPENAI_API_KEY not set" if not settings.has_openai else "OpenAI LLM not implemented"
    
    # Check embeddings provider
    embeddings = get_embeddings_provider(settings)
    embeddings_fallback = isinstance(embeddings, FallbackEmbeddingsProvider)
    embeddings_status = {
        "configured": settings.has_openai,
        "active": not embeddings_fallback,
        "fallback_used": embeddings_fallback,
        "provider": "openai" if not embeddings_fallback else "fallback",
        "model": settings.OPENAI_EMBEDDING_MODEL if not embeddings_fallback else "fallback-embeddings",
        "dimension": embeddings.dimension,
    }
    if embeddings_fallback:
        embeddings_status["reason"] = "OPENAI_API_KEY not set" if not settings.has_openai else "OpenAI embeddings not implemented"
    
    # Check vector provider
    vector = get_vector_provider(settings)
    vector_fallback = isinstance(vector, MemoryVectorProvider)
    vector_status = {
        "configured": settings.has_qdrant,
        "active": not vector_fallback,
        "fallback_used": vector_fallback,
        "provider": "qdrant" if not vector_fallback else "memory",
    }
    if vector_fallback:
        vector_status["reason"] = "QDRANT_URL not set"
    
    return {
        "llm": llm_status,
        "embeddings": embeddings_status,
        "vector": vector_status,
    }
