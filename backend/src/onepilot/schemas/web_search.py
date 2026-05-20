"""Pydantic schemas for external web search (Serper)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2048)
    max_results: int = Field(default=5, ge=1, le=20)
    language: str | None = Field(default=None, max_length=16)
    region: str | None = Field(default=None, max_length=16)
    reason: str | None = Field(default=None, max_length=512)


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    published_date: str | None = None
    rank: int = Field(ge=1)
    provider: str


class WebSearchCitation(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    published_date: str | None = None
    rank: int = Field(ge=1)
    relevance_score: float = Field(ge=0.0, le=1.0)


class WebSearchResponse(BaseModel):
    query: str
    results: list[WebSearchResult] = Field(default_factory=list)
    citations: list[WebSearchCitation] = Field(default_factory=list)
    provider_mode: str
    fallback_used: bool = False
    latency_ms: int = 0
    result_count: int = 0
    error: str | None = None


class WebSearchToolResult(BaseModel):
    query: str = ""
    results: list[WebSearchResult] = Field(default_factory=list)
    citations: list[WebSearchCitation] = Field(default_factory=list)
    provider_mode: str
    fallback_used: bool = False
    latency_ms: int = 0
    result_count: int = 0
    configured: bool = True
    summary: str = ""
