"""Deterministic synthesis for web search and web+RAG combined answers."""

from __future__ import annotations

from onepilot.schemas.web_search import WebSearchCitation, WebSearchResponse


def synthesize_web_only(
    *,
    query: str,
    web: WebSearchResponse,
    configured: bool,
) -> str:
    summary = _web_summary(query, web, configured)
    key_points = _web_key_points(web)
    evidence = _format_web_evidence(web.citations)
    next_action = _web_next_action(query, web, configured)

    return _format_structured_answer(
        summary=summary,
        key_points=key_points,
        evidence=evidence,
        next_action=next_action,
    )


def synthesize_combined(
    *,
    query: str,
    web: WebSearchResponse,
    internal_answer: str,
    internal_weak: bool,
    configured: bool,
) -> str:
    summary = _combined_summary(query, web, internal_weak, configured)
    key_points = _combined_key_points(web, internal_answer, internal_weak)
    evidence_sections = []
    if internal_answer.strip():
        evidence_sections.append("**Internal knowledge**\n" + internal_answer.strip())
    elif internal_weak:
        evidence_sections.append(
            "**Internal knowledge**\n"
            "The knowledge base did not contain enough confident information for this comparison."
        )
    evidence_sections.append("**Web sources**\n" + _format_web_evidence(web.citations))
    evidence = "\n\n".join(evidence_sections)
    next_action = _combined_next_action(query, web, internal_weak, configured)

    return _format_structured_answer(
        summary=summary,
        key_points=key_points,
        evidence=evidence,
        next_action=next_action,
    )


def _format_structured_answer(
    *,
    summary: str,
    key_points: list[str],
    evidence: str,
    next_action: str,
) -> str:
    sections = [
        "## Summary",
        summary.strip(),
        "",
        "## Key points",
    ]
    if key_points:
        sections.extend(f"- {point}" for point in key_points)
    else:
        sections.append("- No strong points were extracted from the available sources.")

    sections.extend(
        [
            "",
            "## Evidence or sources",
            evidence.strip(),
            "",
            "## Suggested next action",
            next_action.strip(),
        ]
    )
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


def _web_summary(query: str, web: WebSearchResponse, configured: bool) -> str:
    if configured and not web.fallback_used and web.result_count > 0:
        return (
            f"This answer is based on external web search (Serper) for: {query.strip()}."
        )
    if not configured:
        return (
            "External web search is not configured (SERPER_API_KEY is missing). "
            "Live web results are unavailable for this query."
        )
    return (
        "External web search was attempted but returned limited or mock results. "
        "Treat the evidence below as incomplete."
    )


def _web_key_points(web: WebSearchResponse) -> list[str]:
    points: list[str] = []
    for item in web.citations[:3]:
        snippet = item.snippet.strip()
        if not snippet:
            continue
        title = item.title or item.url or "Web source"
        points.append(f"{title}: {snippet[:220]}")
    if not points and web.result_count == 0:
        points.append("No live web snippets were returned for this query.")
    return points


def _web_next_action(query: str, web: WebSearchResponse, configured: bool) -> str:
    if not configured:
        return (
            f"Configure SERPER_API_KEY to research '{query[:80]}' with live web results, "
            "or refine the query."
        )
    if web.result_count == 0:
        return "Refine the search query or try a more specific timeframe or topic."
    return (
        "Review the web sources above, verify claims against a second source, "
        "and decide whether follow-up research or internal playbook review is needed."
    )


def _combined_summary(
    query: str, web: WebSearchResponse, internal_weak: bool, configured: bool
) -> str:
    parts = [f"Combined research for: {query.strip()}."]
    if configured and web.result_count > 0:
        parts.append("External web search (Serper) was combined with internal company knowledge.")
    elif not configured:
        parts.append("External web search is not configured; internal knowledge was used where available.")
    if internal_weak:
        parts.append("Internal knowledge base coverage was limited for this comparison.")
    return " ".join(parts)


def _combined_key_points(
    web: WebSearchResponse, internal_answer: str, internal_weak: bool
) -> list[str]:
    points: list[str] = []
    if internal_answer.strip() and not internal_weak:
        first_sentence = internal_answer.strip().split(".")[0].strip()
        if first_sentence:
            points.append(f"Internal: {first_sentence}.")
    elif internal_weak:
        points.append("Internal KB did not provide confident coverage for this topic.")

    for item in web.citations[:2]:
        snippet = item.snippet.strip()
        if snippet:
            title = item.title or item.url or "Web source"
            points.append(f"External: {title} — {snippet[:180]}")

    return points


def _combined_next_action(
    query: str, web: WebSearchResponse, internal_weak: bool, configured: bool
) -> str:
    parts = [
        "Align external trend signals with NovaEdge offerings where they strengthen positioning."
    ]
    if internal_weak:
        parts.append(
            "Consider uploading or refreshing internal service documentation to improve comparisons."
        )
    if not configured or web.result_count == 0:
        parts.append(
            f"Add SERPER_API_KEY to enrich market research for queries like '{query[:60]}'."
        )
    return " ".join(parts)
