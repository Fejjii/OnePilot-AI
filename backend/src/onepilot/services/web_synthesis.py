"""Deterministic synthesis for web search and web+RAG combined answers."""

from __future__ import annotations

from onepilot.schemas.web_search import WebSearchCitation, WebSearchResponse


def synthesize_web_only(
    *,
    query: str,
    web: WebSearchResponse,
    configured: bool,
) -> str:
    sections: list[str] = []

    if configured and not web.fallback_used and web.result_count > 0:
        sections.append(
            "External web search was used via Serper to gather current information."
        )
    elif not configured:
        sections.append(
            "External web search is not configured (SERPER_API_KEY is missing). "
            "The answer below uses only available context."
        )
    else:
        sections.append(
            "External web search was attempted but returned limited or mock results."
        )

    sections.append("\n## External web evidence\n")
    sections.append(_format_web_evidence(web.citations))

    sections.append("\n## Recommendation\n")
    sections.append(_web_recommendation(query, web))

    return "\n".join(sections).strip()


def synthesize_combined(
    *,
    query: str,
    web: WebSearchResponse,
    internal_answer: str,
    internal_weak: bool,
    configured: bool,
) -> str:
    sections: list[str] = []

    if configured and web.result_count > 0:
        sections.append(
            "External web search was used via Serper, combined with internal company knowledge."
        )
    elif not configured:
        sections.append(
            "External web search is not configured (SERPER_API_KEY is missing). "
            "Internal company knowledge is used where available."
        )
    else:
        sections.append(
            "Combined research: external web results are limited; internal knowledge is included."
        )

    sections.append("\n## Internal company knowledge\n")
    if internal_answer.strip():
        sections.append(internal_answer.strip())
    elif internal_weak:
        sections.append(
            "The knowledge base did not contain enough confident information for this comparison."
        )
    else:
        sections.append("No internal knowledge base excerpts were retrieved.")

    sections.append("\n## External web evidence\n")
    sections.append(_format_web_evidence(web.citations))

    sections.append("\n## Recommendation\n")
    sections.append(_combined_recommendation(query, web, internal_weak))

    return "\n".join(sections).strip()


def _format_web_evidence(citations: list[WebSearchCitation]) -> str:
    if not citations:
        return "- No external web sources were retrieved."

    lines: list[str] = []
    for item in citations:
        title = item.title or item.url or "Web source"
        url = item.url or ""
        snippet = item.snippet.strip()
        line = f"- **{title}**"
        if url:
            line += f" ({url})"
        if snippet:
            line += f": {snippet}"
        if item.published_date:
            line += f" [published: {item.published_date}]"
        lines.append(line)
    return "\n".join(lines)


def _web_recommendation(query: str, web: WebSearchResponse) -> str:
    if web.result_count == 0:
        return (
            f"Configure SERPER_API_KEY to research '{query[:80]}' with live web results, "
            "or refine the query."
        )
    return (
        "Review the external sources above for current market signals. "
        "Cross-check claims against your internal playbooks before acting."
    )


def _combined_recommendation(query: str, web: WebSearchResponse, internal_weak: bool) -> str:
    parts = [
        "Align external trend signals with NovaEdge offerings where they strengthen your positioning."
    ]
    if internal_weak:
        parts.append(
            "Internal KB coverage was thin — consider uploading or refreshing service documentation."
        )
    if web.result_count == 0:
        parts.append(
            f"Add SERPER_API_KEY to enrich market research for queries like '{query[:60]}'."
        )
    return " ".join(parts)
