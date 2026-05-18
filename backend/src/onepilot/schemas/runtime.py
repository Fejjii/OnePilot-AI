"""Runtime and provider diagnostic schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProviderMode(str, Enum):
    LIVE = "live"
    FALLBACK = "fallback"
    MOCK = "mock"
    LOCAL = "local"
    MISSING = "missing"
    UNHEALTHY = "unhealthy"


class ProviderCategory(str, Enum):
    LLM = "llm"
    EMBEDDINGS = "embeddings"
    VECTOR = "vector"
    CACHE = "cache"
    DATABASE = "database"
    OBSERVABILITY = "observability"
    SEARCH = "search"
    EMAIL = "email"
    CRM = "crm"
    CALENDAR = "calendar"
    SMS = "sms"
    BILLING = "billing"
    SPEECH = "speech"


class ProviderDiagnostic(BaseModel):
    name: str = Field(..., description="Provider display name")
    category: ProviderCategory = Field(..., description="Provider category")
    configured: bool = Field(..., description="Environment variables are set")
    healthy: bool = Field(..., description="Provider is operational")
    active: bool = Field(..., description="Real provider is in use (not fallback/mock)")
    fallback_used: bool = Field(..., description="Fallback provider is active")
    mode: ProviderMode = Field(..., description="Current operational mode")
    model: str | None = Field(None, description="Model or version in use")
    reason: str | None = Field(None, description="Explanation if not live")
    last_checked_at: datetime = Field(..., description="Timestamp of this check")
    details: dict[str, str | int | bool] | None = Field(None, description="Additional metadata")


class ProviderDiagnosticResponse(BaseModel):
    providers: list[ProviderDiagnostic] = Field(..., description="All provider diagnostics")
    checked_at: datetime = Field(..., description="When these diagnostics were generated")
