"""External web search service (Serper-backed)."""

from __future__ import annotations

import time

from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import UsageFeature
from onepilot.providers import get_search_provider
from onepilot.providers.search.mock_search_provider import MockSearchProvider
from onepilot.providers.search.serper_provider import SerperSearchProvider
from onepilot.schemas.web_search import (
    WebSearchCitation,
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResult,
)
from onepilot.security.auth import Principal
from onepilot.services import usage_service


def search_web(
    session: Session,
    *,
    principal: Principal,
    request: WebSearchRequest,
    settings: Settings | None = None,
) -> WebSearchResponse:
    """Run external web search and record usage."""
    settings = settings or get_settings()
    started = time.monotonic()

    provider = get_search_provider(settings)
    configured = settings.has_serper
    is_mock = isinstance(provider, MockSearchProvider)
    is_live = isinstance(provider, SerperSearchProvider)

    if configured and is_live:
        provider_mode = "live"
    elif configured and is_mock:
        provider_mode = "fallback"
    elif not configured and is_mock:
        provider_mode = "missing"
    else:
        provider_mode = "fallback"

    max_results = min(request.max_results, settings.SERPER_MAX_RESULTS)
    raw_hits: list[dict] = []
    error: str | None = None

    if configured and is_live:
        raw_hits = provider.search_web(
            request.query,
            max_results,
            language=request.language,
            region=request.region,
        )
        if not raw_hits:
            error = "no_results"
    elif not configured:
        error = "not_configured"
    else:
        raw_hits = provider.search_web(
            request.query,
            max_results,
            language=request.language,
            region=request.region,
        )

    results = [_to_result(row) for row in raw_hits]
    citations = _to_citations(results)
    fallback_used = not configured or is_mock or (configured and not raw_hits)
    latency_ms = int((time.monotonic() - started) * 1000)

    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=UsageFeature.WEB_SEARCH.value,
        provider="serper" if is_live else "mock",
        tool_calls=1,
        fallback_used=fallback_used,
        latency_ms=latency_ms,
        metadata={
            "query_preview": request.query[:120],
            "result_count": len(results),
            "provider_mode": provider_mode,
            "configured": configured,
            "reason": request.reason,
        },
    )

    return WebSearchResponse(
        query=request.query,
        results=results,
        citations=citations,
        provider_mode=provider_mode,
        fallback_used=fallback_used,
        latency_ms=latency_ms,
        result_count=len(results),
        error=error,
    )


def _to_result(row: dict) -> WebSearchResult:
    return WebSearchResult(
        title=str(row.get("title", "")),
        url=str(row.get("url", "")),
        snippet=str(row.get("snippet", "")),
        source=str(row.get("source", "web")),
        published_date=row.get("published_date"),
        rank=int(row.get("rank", 1)),
        provider=str(row.get("provider", "unknown")),
    )


def _to_citations(results: list[WebSearchResult]) -> list[WebSearchCitation]:
    citations: list[WebSearchCitation] = []
    for item in results:
        score = max(0.35, 1.0 - (item.rank - 1) * 0.08)
        citations.append(
            WebSearchCitation(
                title=item.title,
                url=item.url,
                snippet=item.snippet,
                source=item.source,
                published_date=item.published_date,
                rank=item.rank,
                relevance_score=round(score, 3),
            )
        )
    return citations
