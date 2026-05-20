"""External web search tool (Serper-backed)."""

from __future__ import annotations

import time
from typing import Any

from onepilot.schemas.web_search import WebSearchRequest, WebSearchToolResult
from onepilot.services import web_search_service
from onepilot.tools.base import Tool, ToolContext, ToolResult


class WebSearchTool(Tool):
    name = "external.web_search"
    description = (
        "Search the public web for recent or current information via Serper. "
        "Returns normalized results and external citations."
    )

    def run(
        self,
        ctx: ToolContext,
        *,
        query: str,
        max_results: int | None = None,
        language: str | None = None,
        region: str | None = None,
        reason: str | None = None,
        **_: Any,
    ) -> ToolResult:
        started = time.monotonic()
        limit = max_results or ctx.settings.SERPER_MAX_RESULTS
        request = WebSearchRequest(
            query=query,
            max_results=limit,
            language=language,
            region=region,
            reason=reason,
        )
        outcome = web_search_service.search_web(
            ctx.session,
            principal=ctx.principal,
            request=request,
            settings=ctx.settings,
        )
        duration_ms = int((time.monotonic() - started) * 1000)

        citations = [
            {
                "document_id": "",
                "document_title": c.title,
                "section": c.source,
                "chunk_text": c.snippet[:600],
                "relevance_score": c.relevance_score,
                "citation_type": "external",
                "url": c.url,
                "source": c.source,
            }
            for c in outcome.citations
        ]

        tool_payload = WebSearchToolResult(
            query=query,
            results=outcome.results,
            citations=outcome.citations,
            provider_mode=outcome.provider_mode,
            fallback_used=outcome.fallback_used,
            latency_ms=outcome.latency_ms,
            result_count=outcome.result_count,
            configured=ctx.settings.has_serper,
            summary=(
                f"provider={outcome.provider_mode} results={outcome.result_count} "
                f"fallback={outcome.fallback_used}"
            ),
        )

        safety_flags: list[str] = []
        if outcome.fallback_used:
            safety_flags.append("web_search_fallback")
        if not ctx.settings.has_serper:
            safety_flags.append("web_search_not_configured")

        return ToolResult(
            tool_name=self.name,
            input_summary=f"query: {query[:120]}",
            output_summary=tool_payload.summary,
            output=tool_payload.model_dump(),
            duration_ms=duration_ms,
            safety_flags=safety_flags,
            citations=citations,
            usage={
                "provider": "serper" if ctx.settings.has_serper else "mock",
                "tool_calls": 1,
                "fallback_used": outcome.fallback_used,
                "web_search_results": outcome.result_count,
                "provider_mode": outcome.provider_mode,
            },
        )
