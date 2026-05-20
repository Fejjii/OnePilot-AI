"""RAG tool: grounded answers over the tenant's knowledge base."""

from __future__ import annotations

import time
from typing import Any

from onepilot.services import rag_service
from onepilot.tools.base import Tool, ToolContext, ToolResult


class RAGTool(Tool):
    name = "rag.answer"
    description = (
        "Answer a user question using the tenant's knowledge base. "
        "Returns citations and weak-evidence flag."
    )

    def run(
        self,
        ctx: ToolContext,
        *,
        query: str,
        top_k: int = 5,
        response_language: str = "en",
        detected_language: str | None = None,
        **_: Any,
    ) -> ToolResult:
        started = time.monotonic()
        outcome = rag_service.answer(
            ctx.session,
            principal=ctx.principal,
            query=query,
            top_k=top_k,
            settings=ctx.settings,
            response_language=response_language,
            detected_language=detected_language,
        )
        duration_ms = int((time.monotonic() - started) * 1000)

        citations = [
            {
                "document_id": hit.chunk.document_id,
                "document_title": hit.document_title,
                "section": hit.chunk.section,
                "chunk_text": hit.chunk.content[:600],
                "relevance_score": hit.score,
                "citation_type": "internal",
            }
            for hit in outcome.hits
        ]

        safety_flags: list[str] = []
        if outcome.weak_evidence:
            safety_flags.append("weak_evidence")
        if outcome.fallback_used:
            safety_flags.append("fallback_used")

        return ToolResult(
            tool_name=self.name,
            input_summary=f"query: {query[:120]}",
            output_summary=(
                f"hits={len(outcome.hits)} weak_evidence={outcome.weak_evidence} "
                f"model={outcome.model}"
            ),
            output={
                "answer": outcome.answer,
                "confidence": outcome.confidence,
                "weak_evidence": outcome.weak_evidence,
                "fallback_used": outcome.fallback_used,
                "model": outcome.model,
                "citations": citations,
                "source_titles": sorted({c["document_title"] for c in citations}),
            },
            duration_ms=duration_ms,
            safety_flags=safety_flags,
            citations=citations,
            usage={
                "model": outcome.model,
                "provider": "rag.answer",
                "fallback_used": outcome.fallback_used,
            },
        )
