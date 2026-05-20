"""LangGraph agent workflow.

Graph:

    classify_message -> classify_intent -> route -> {branch} -> guardrail -> finalize_response

Stage 1 (classify_message): Message classification into high-level classes
Stage 2 (classify_intent): Intent classification based on message class
Branches (selected by ``route``):
    - knowledge_search   -> RAG tool
    - email_assistant    -> EmailDraft tool
    - lead_assistant     -> LeadSupport tool
    - general_chat       -> GeneralChat tool
    - clarification      -> templated clarification response
    - out_of_scope       -> templated polite refusal

The graph is deterministic when no API keys are configured. Each node returns
a partial state dict so LangGraph can merge updates. We keep the agent itself
free of business logic — every branch delegates to a tool, and tools delegate
to services.

Tracing is integrated throughout the workflow using the observability.tracing
abstraction layer. Supports both local and LangSmith live tracing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from onepilot.agents.intent_classifier import classify as classify_intent_fn
from onepilot.agents.message_classifier import classify_message as classify_message_fn
from onepilot.core.config import Settings
from onepilot.core.constants import Intent, LanguageCode, LanguagePreference
from onepilot.services import i18n_messages
from onepilot.services.language_service import (
    detect_language,
    resolve_response_language,
)
from onepilot.core.logging import get_logger
from onepilot.observability.tracing import TraceContext, sanitize_metadata
from onepilot.schemas.agents import AgentState
from onepilot.schemas.chat import Citation, ToolCallTrace, TraceStep
from onepilot.security.auth import Principal
from onepilot.services import approval_service, calendar_service, gmail_service
from onepilot.services.calendar_format import format_availability_response, format_suggestion_response
from onepilot.tools import registry as _tools_bootstrap  # noqa: F401  ensures tool registration
from onepilot.schemas.web_search import WebSearchCitation, WebSearchResponse
from onepilot.services import web_synthesis
from onepilot.tools.base import ToolContext, ToolResult
from onepilot.tools.registry import registry

logger = get_logger(__name__)


WEAK_EVIDENCE_RESPONSE = (
    "I couldn't find enough information in the knowledge base to answer that "
    "confidently. I've flagged this for a teammate to follow up."
)

OUT_OF_SCOPE_RESPONSE = (
    "I'm built for business productivity (knowledge search, leads, email "
    "drafts, etc.) and can't help with that. Try rephrasing as a work task."
)

CLARIFICATION_RESPONSE = (
    "Could you share a bit more detail? For example: what outcome you want, "
    "who it's for, and any deadline."
)

LOW_CONFIDENCE_THRESHOLD = 0.45


# ---------------------------------------------------------------------------
# Branch selection
# ---------------------------------------------------------------------------

_INTENT_TO_BRANCH: dict[Intent, str] = {
    Intent.KNOWLEDGE_SEARCH: "knowledge_search",
    Intent.DOCUMENT_SUMMARY: "knowledge_search",
    Intent.WEB_SEARCH: "web_search",
    Intent.WEB_AND_KNOWLEDGE: "web_and_knowledge",
    Intent.EMAIL_DRAFTING: "email_assistant",
    Intent.CALENDAR_AVAILABILITY: "calendar_assistant",
    Intent.CALENDAR_SCHEDULING: "calendar_assistant",
    Intent.CALENDAR_AND_EMAIL: "calendar_and_email",
    Intent.LEAD_SUPPORT: "lead_assistant",
    Intent.WORKFLOW_ACTION: "lead_assistant",
    Intent.COMPOUND_WORKFLOW: "compound_workflow",
    Intent.GENERAL_ASSISTANT: "general_chat",
    Intent.OUT_OF_SCOPE: "out_of_scope",
    Intent.CLARIFICATION: "clarification",
}


def branch_for(intent: Intent | None) -> str:
    return _INTENT_TO_BRANCH.get(intent or Intent.GENERAL_ASSISTANT, "general_chat")


# ---------------------------------------------------------------------------
# Agent dependencies
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AgentDeps:
    session: Session
    principal: Principal
    settings: Settings
    trace_context: TraceContext | None = None


def _ctx(deps: AgentDeps) -> ToolContext:
    return ToolContext(session=deps.session, principal=deps.principal, settings=deps.settings)


def _append_trace(state: dict, step: str, *, detail: str = "", duration_ms: int = 0) -> None:
    state.setdefault("trace_steps", []).append(
        TraceStep(step=step, detail=detail, duration_ms=duration_ms).model_dump()
    )


def _record_tool_call(state: dict, result: ToolResult) -> None:
    state.setdefault("tool_calls", []).append(
        ToolCallTrace(
            tool_name=result.tool_name,
            input_summary=result.input_summary,
            output_summary=result.output_summary,
            duration_ms=result.duration_ms,
        ).model_dump()
    )
    if result.citations:
        existing = state.setdefault("citations", [])
        for citation in result.citations:
            existing.append(
                Citation(
                    document_id=str(citation.get("document_id", "")),
                    document_title=str(citation.get("document_title", "Source")),
                    section=citation.get("section"),
                    chunk_text=str(citation.get("chunk_text", ""))[:600],
                    relevance_score=float(citation.get("relevance_score", 0.0)),
                    citation_type=str(citation.get("citation_type", "internal")),
                    url=citation.get("url"),
                    source=citation.get("source"),
                ).model_dump()
            )
    if result.safety_flags:
        flags = state.setdefault("safety_flags", [])
        for flag in result.safety_flags:
            if flag not in flags:
                flags.append(flag)
    if result.usage:
        usage = state.setdefault("usage_metadata", {})
        usage.update(result.usage)


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


def make_workflow(deps: AgentDeps):  # type: ignore[no-untyped-def]
    """Build a compiled LangGraph for one request."""

    def classify_message_node(state: AgentState) -> dict:
        """Stage 1: Classify message into high-level message class."""
        started = time.monotonic()
        result = classify_message_fn(state.message)
        duration_ms = int((time.monotonic() - started) * 1000)
        update: dict[str, Any] = {
            "message_class": result.message_class,
            "message_class_confidence": result.confidence,
            "message_class_reason": result.reason,
            "trace_steps": list(state.trace_steps)
            + [
                TraceStep(
                    step="classify_message",
                    detail=f"class={result.message_class} reason={result.reason}",
                    duration_ms=duration_ms,
                ).model_dump()
            ],
        }
        return update

    def resolve_language_node(state: AgentState) -> dict:
        """Detect user language and resolve assistant response language."""
        started = time.monotonic()
        context_lang = state.context.get("detected_language")
        detection = detect_language(
            state.message,
            settings=deps.settings,
            context_language=str(context_lang) if context_lang else None,
        )
        response_lang = resolve_response_language(
            state.language_preference,
            detection.language,
            detection.confidence,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "detected_language": detection.language.value,
            "response_language": response_lang.value,
            "trace_steps": list(state.trace_steps)
            + [
                TraceStep(
                    step="resolve_language",
                    detail=(
                        f"detected={detection.language.value} "
                        f"confidence={detection.confidence:.2f} "
                        f"response={response_lang.value} "
                        f"preference={state.language_preference.value}"
                    ),
                    duration_ms=duration_ms,
                ).model_dump()
            ],
        }

    def classify_intent_node(state: AgentState) -> dict:
        """Stage 2: Map message class to specific intent."""
        started = time.monotonic()
        result = classify_intent_fn(
            state.message,
            message_class=state.message_class,
            settings=deps.settings,
            use_llm=False,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        update: dict[str, Any] = {
            "intent": result.intent,
            "confidence": result.confidence,
            "route_reason": f"message_class={state.message_class} -> intent={result.intent}",
            "trace_steps": list(state.trace_steps)
            + [
                TraceStep(
                    step="classify_intent",
                    detail=f"{result.source}:{result.reason}",
                    intent=result.intent,
                    duration_ms=duration_ms,
                ).model_dump()
            ],
        }
        if result.confidence < LOW_CONFIDENCE_THRESHOLD:
            update["safety_flags"] = list(state.safety_flags) + ["low_confidence"]
        return update

    def route_node(state: AgentState) -> dict:
        branch = branch_for(state.intent)
        return {
            "selected_tools": list(state.selected_tools) + [_branch_to_tool_name(branch)],
            "trace_steps": list(state.trace_steps)
            + [TraceStep(step="route", detail=branch).model_dump()],
        }

    def knowledge_search_node(state: AgentState) -> dict:
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
        }
        result = registry.get("rag.answer").run(
            _ctx(deps),
            query=state.message,
            response_language=state.response_language,
            detected_language=state.detected_language,
        )
        _record_tool_call(update, result)
        update["draft_output"] = result.output.get("answer", "")
        rag_confidence = float(result.output.get("confidence", 0.0))
        if "weak_evidence" in result.safety_flags:
            update["confidence"] = rag_confidence
        else:
            update["confidence"] = max(state.confidence, rag_confidence)
        _append_trace(update, "execute_tool:rag.answer", duration_ms=result.duration_ms)
        return update

    def email_assistant_node(state: AgentState) -> dict:
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
        }
        email_action = gmail_service.infer_email_action(state.message, state.context)
        result = registry.get("email.draft").run(
            _ctx(deps),
            context=state.message,
            tone=state.context.get("tone", "professional"),
            recipient_name=state.context.get("recipient_name"),
            recipient_email=state.context.get("recipient_email"),
            action=email_action,
        )
        _record_tool_call(update, result)
        draft = result.output.get("draft", {})
        update["draft_output"] = _format_email(draft)
        if result.approval_required and result.approval_action_type:
            approval = approval_service.create(
                deps.session,
                principal=deps.principal,
                action_type=result.approval_action_type,
                title=result.approval_title or "Approval required",
                description=draft.get("body", "")[:1024],
                proposed_payload=result.approval_payload or {},
                risk_level=result.approval_risk,
                reason="Agent proposed an external action.",
            )
            update["approval_required"] = True
            update["approval_id"] = approval.id
        _append_trace(update, "execute_tool:email.draft", duration_ms=result.duration_ms)
        return update

    def calendar_assistant_node(state: AgentState) -> dict:
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
        }
        tool_key = calendar_service.infer_calendar_tool(state.message, state.context)
        tool_name = f"calendar.{tool_key}"
        result = registry.get(tool_name).run(
            _ctx(deps),
            message=state.message,
            context=state.context,
        )
        _record_tool_call(update, result)
        update["draft_output"] = _format_calendar_output(result)
        output = result.output if isinstance(result.output, dict) else {}
        mode = output.get("mode") or output.get("provider_mode")
        if mode == "live" and output.get("status") != "error":
            update["confidence"] = max(state.confidence, 0.88)
        elif mode in {"unhealthy", "missing"} or output.get("status") == "error":
            update["confidence"] = min(state.confidence, 0.5)
        elif mode == "mock" or output.get("fallback_used"):
            update["confidence"] = min(state.confidence, 0.55)
        if result.approval_required and result.approval_action_type:
            approval = approval_service.create(
                deps.session,
                principal=deps.principal,
                action_type=result.approval_action_type,
                title=result.approval_title or "Calendar approval required",
                description=update["draft_output"][:1024],
                proposed_payload=result.approval_payload or {},
                risk_level=result.approval_risk,
                reason="Agent proposed a calendar event creation.",
            )
            update["approval_required"] = True
            update["approval_id"] = approval.id
        _append_trace(update, f"execute_tool:{tool_name}", duration_ms=result.duration_ms)
        return update

    def calendar_and_email_node(state: AgentState) -> dict:
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
            "approval_required": False,
        }
        email_action = gmail_service.infer_email_action(state.message, state.context)
        email_result = registry.get("email.draft").run(
            _ctx(deps),
            context=state.message,
            tone=state.context.get("tone", "professional"),
            recipient_name=state.context.get("recipient_name"),
            recipient_email=state.context.get("recipient_email"),
            action=email_action,
        )
        _record_tool_call(update, email_result)
        calendar_result = registry.get("calendar.create_event_request").run(
            _ctx(deps),
            message=state.message,
            context=state.context,
        )
        _record_tool_call(update, calendar_result)

        sections = [
            "Email draft",
            _format_email(email_result.output.get("draft", {})),
            "",
            "Calendar proposal",
            _format_calendar_output(calendar_result),
        ]
        update["draft_output"] = "\n".join(sections)

        approval_ids: list[str] = []
        if email_result.approval_required and email_result.approval_action_type:
            email_approval = approval_service.create(
                deps.session,
                principal=deps.principal,
                action_type=email_result.approval_action_type,
                title=email_result.approval_title or "Gmail approval required",
                description=sections[1][:1024],
                proposed_payload=email_result.approval_payload or {},
                risk_level=email_result.approval_risk,
                reason="Agent proposed an external email action.",
            )
            approval_ids.append(email_approval.id)
        if calendar_result.approval_required and calendar_result.approval_action_type:
            calendar_approval = approval_service.create(
                deps.session,
                principal=deps.principal,
                action_type=calendar_result.approval_action_type,
                title=calendar_result.approval_title or "Calendar approval required",
                description=sections[-1][:1024],
                proposed_payload=calendar_result.approval_payload or {},
                risk_level=calendar_result.approval_risk,
                reason="Agent proposed a calendar event creation.",
            )
            approval_ids.append(calendar_approval.id)

        if approval_ids:
            update["approval_required"] = True
            update["approval_id"] = approval_ids[0]
        _append_trace(
            update,
            "execute_tool:calendar_and_email",
            duration_ms=email_result.duration_ms + calendar_result.duration_ms,
        )
        return update

    def lead_assistant_node(state: AgentState) -> dict:
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
        }
        result = registry.get("lead.support").run(
            _ctx(deps),
            message=state.message,
            name=state.context.get("lead_name"),
            email=state.context.get("lead_email"),
            company=state.context.get("lead_company"),
            force_capture=bool(state.context.get("force_capture", False)),
        )
        _record_tool_call(update, result)
        update["draft_output"] = _format_lead(result.output)
        _append_trace(update, "execute_tool:lead.support", duration_ms=result.duration_ms)
        return update

    def compound_workflow_node(state: AgentState) -> dict:
        """Sequential multi-tool workflow: research → email draft → calendar proposal."""
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
            "approval_required": False,
        }
        web_result = registry.get("external.web_search").run(
            _ctx(deps),
            query=state.message,
            reason="compound_workflow_research",
        )
        _record_tool_call(update, web_result)
        web = _web_response_from_tool(web_result)
        research_summary = web_synthesis.synthesize_web_only(
            query=state.message,
            web=web,
            configured=deps.settings.has_serper,
        )

        email_action = gmail_service.infer_email_action(state.message, state.context)
        email_result = registry.get("email.draft").run(
            _ctx(deps),
            context=state.message,
            tone=state.context.get("tone", "professional"),
            recipient_name=state.context.get("recipient_name"),
            recipient_email=state.context.get("recipient_email"),
            action=email_action,
        )
        _record_tool_call(update, email_result)

        calendar_result = registry.get("calendar.create_event_request").run(
            _ctx(deps),
            message=state.message,
            context=state.context,
        )
        _record_tool_call(update, calendar_result)

        sections = [
            "## External market research",
            research_summary,
            "",
            "## Draft email preview",
            _format_email(email_result.output.get("draft", {})),
            "",
            "## Meeting proposal",
            _format_calendar_output(calendar_result),
        ]
        update["draft_output"] = "\n".join(sections)

        approval_ids: list[str] = []
        if calendar_result.approval_required and calendar_result.approval_action_type:
            calendar_approval = approval_service.create(
                deps.session,
                principal=deps.principal,
                action_type=calendar_result.approval_action_type,
                title=calendar_result.approval_title or "Calendar approval required",
                description=sections[-1][:1024],
                proposed_payload=calendar_result.approval_payload or {},
                risk_level=calendar_result.approval_risk,
                reason="Compound workflow proposed a calendar event.",
            )
            approval_ids.append(calendar_approval.id)
        if email_result.approval_required and email_result.approval_action_type:
            email_approval = approval_service.create(
                deps.session,
                principal=deps.principal,
                action_type=email_result.approval_action_type,
                title=email_result.approval_title or "Gmail approval required",
                description=sections[3][:1024],
                proposed_payload=email_result.approval_payload or {},
                risk_level=email_result.approval_risk,
                reason="Compound workflow proposed an email action.",
            )
            approval_ids.append(email_approval.id)

        if approval_ids:
            update["approval_required"] = True
            update["approval_id"] = approval_ids[0]

        unhealthy = (calendar_result.output or {}).get("provider_mode") == "unhealthy" or (
            calendar_result.output or {}
        ).get("mode") == "unhealthy"
        if unhealthy:
            update["confidence"] = min(state.confidence, 0.5)

        _append_trace(
            update,
            "execute_tool:compound_workflow",
            duration_ms=web_result.duration_ms
            + email_result.duration_ms
            + calendar_result.duration_ms,
        )
        return update

    def web_search_node(state: AgentState) -> dict:
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
        }
        result = registry.get("external.web_search").run(
            _ctx(deps),
            query=state.message,
            reason="external_research",
        )
        _record_tool_call(update, result)
        web = _web_response_from_tool(result)
        update["draft_output"] = web_synthesis.synthesize_web_only(
            query=state.message,
            web=web,
            configured=deps.settings.has_serper,
        )
        _append_trace(
            update,
            "execute_tool:external.web_search",
            detail=f"results={web.result_count} mode={web.provider_mode}",
            duration_ms=result.duration_ms,
        )
        return update

    def web_and_knowledge_node(state: AgentState) -> dict:
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
        }
        web_result = registry.get("external.web_search").run(
            _ctx(deps),
            query=state.message,
            reason="external_research_with_internal_comparison",
        )
        _record_tool_call(update, web_result)
        web = _web_response_from_tool(web_result)

        rag_result = registry.get("rag.answer").run(
            _ctx(deps),
            query=state.message,
            response_language=state.response_language,
            detected_language=state.detected_language,
        )
        _record_tool_call(update, rag_result)

        internal_answer = str(rag_result.output.get("answer", ""))
        internal_weak = "weak_evidence" in rag_result.safety_flags
        update["draft_output"] = web_synthesis.synthesize_combined(
            query=state.message,
            web=web,
            internal_answer=internal_answer,
            internal_weak=internal_weak,
            configured=deps.settings.has_serper,
        )
        rag_confidence = float(rag_result.output.get("confidence", 0.0))
        update["confidence"] = max(state.confidence, rag_confidence)
        if internal_weak:
            flags = list(update["safety_flags"])
            if "weak_evidence" not in flags:
                flags.append("weak_evidence")
            update["safety_flags"] = flags
        _append_trace(
            update,
            "execute_tool:web_and_knowledge",
            detail=f"web_results={web.result_count} rag_weak={internal_weak}",
            duration_ms=web_result.duration_ms + rag_result.duration_ms,
        )
        return update

    def general_chat_node(state: AgentState) -> dict:
        update: dict[str, Any] = {
            "trace_steps": list(state.trace_steps),
            "tool_calls": list(state.tool_calls),
            "citations": list(state.citations),
            "safety_flags": list(state.safety_flags),
            "usage_metadata": dict(state.usage_metadata),
        }
        result = registry.get("chat.general").run(
            _ctx(deps),
            message=state.message,
            history=state.history,
            message_class=state.message_class,
            response_language=state.response_language,
        )
        _record_tool_call(update, result)
        update["draft_output"] = result.output.get("reply", "")
        _append_trace(update, "execute_tool:chat.general", duration_ms=result.duration_ms)
        return update

    def clarification_node(state: AgentState) -> dict:
        flags = list(state.safety_flags)
        if "clarification_requested" not in flags:
            flags.append("clarification_requested")
        lang = LanguageCode(state.response_language)
        return {
            "draft_output": i18n_messages.get_message(i18n_messages.CLARIFICATION, lang),
            "safety_flags": flags,
            "trace_steps": list(state.trace_steps)
            + [TraceStep(step="execute_tool:clarification").model_dump()],
        }

    def out_of_scope_node(state: AgentState) -> dict:
        flags = list(state.safety_flags)
        if "out_of_scope" not in flags:
            flags.append("out_of_scope")
        lang = LanguageCode(state.response_language)
        return {
            "draft_output": i18n_messages.get_message(i18n_messages.OUT_OF_SCOPE, lang),
            "safety_flags": flags,
            "trace_steps": list(state.trace_steps)
            + [TraceStep(step="execute_tool:out_of_scope").model_dump()],
        }

    def guardrail_node(state: AgentState) -> dict:
        """Apply final safety checks before finalize."""
        flags = list(state.safety_flags)
        draft = state.draft_output or ""

        # Weak-evidence rewrite for knowledge search.
        if "weak_evidence" in flags and state.intent in {
            Intent.KNOWLEDGE_SEARCH,
            Intent.DOCUMENT_SUMMARY,
        }:
            lang = LanguageCode(state.response_language)
            draft = i18n_messages.get_message(i18n_messages.WEAK_EVIDENCE, lang)

        # Low-confidence intents that propose an external action get gated.
        approval_required = state.approval_required
        approval_id = state.approval_id
        if state.confidence < LOW_CONFIDENCE_THRESHOLD and _is_external(state.intent):
            if "low_confidence" not in flags:
                flags.append("low_confidence")
            if not approval_required:
                approval = approval_service.create(
                    deps.session,
                    principal=deps.principal,
                    action_type="low_confidence_action",
                    title="Low confidence action requires review",
                    description=f"Intent={state.intent}; message={state.message[:240]}",
                    proposed_payload={"intent": state.intent, "message": state.message[:1024]},
                    risk_level="medium",
                    reason="Confidence below threshold for external action.",
                )
                approval_required = True
                approval_id = approval.id

        return {
            "draft_output": draft,
            "safety_flags": flags,
            "approval_required": approval_required,
            "approval_id": approval_id,
            "trace_steps": list(state.trace_steps)
            + [TraceStep(step="guardrail", detail=",".join(flags)).model_dump()],
        }

    def finalize_node(state: AgentState) -> dict:
        final = state.draft_output or "I don't have a response for that yet."
        if state.approval_required:
            lang = LanguageCode(state.response_language)
            final = final.rstrip() + i18n_messages.get_message(
                i18n_messages.APPROVAL_FOOTNOTE, lang
            )
        return {
            "final_response": final,
            "trace_steps": list(state.trace_steps)
            + [TraceStep(step="finalize_response").model_dump()],
        }

    graph: StateGraph = StateGraph(AgentState)
    graph.add_node("classify_message", classify_message_node)
    graph.add_node("resolve_language", resolve_language_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("route", route_node)
    graph.add_node("knowledge_search", knowledge_search_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("web_and_knowledge", web_and_knowledge_node)
    graph.add_node("email_assistant", email_assistant_node)
    graph.add_node("calendar_assistant", calendar_assistant_node)
    graph.add_node("calendar_and_email", calendar_and_email_node)
    graph.add_node("compound_workflow", compound_workflow_node)
    graph.add_node("lead_assistant", lead_assistant_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("out_of_scope", out_of_scope_node)
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("finalize_response", finalize_node)

    graph.set_entry_point("classify_message")
    graph.add_edge("classify_message", "resolve_language")
    graph.add_edge("resolve_language", "classify_intent")
    graph.add_edge("classify_intent", "route")
    graph.add_conditional_edges(
        "route",
        lambda s: branch_for(s.intent),
        {
            "knowledge_search": "knowledge_search",
            "web_search": "web_search",
            "web_and_knowledge": "web_and_knowledge",
            "email_assistant": "email_assistant",
            "calendar_assistant": "calendar_assistant",
            "calendar_and_email": "calendar_and_email",
            "compound_workflow": "compound_workflow",
            "lead_assistant": "lead_assistant",
            "general_chat": "general_chat",
            "clarification": "clarification",
            "out_of_scope": "out_of_scope",
        },
    )
    for branch in (
        "knowledge_search",
        "web_search",
        "web_and_knowledge",
        "email_assistant",
        "calendar_assistant",
        "calendar_and_email",
        "compound_workflow",
        "lead_assistant",
        "general_chat",
        "clarification",
        "out_of_scope",
    ):
        graph.add_edge(branch, "guardrail")
    graph.add_edge("guardrail", "finalize_response")
    graph.add_edge("finalize_response", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _branch_to_tool_name(branch: str) -> str:
    return {
        "knowledge_search": "rag.answer",
        "web_search": "external.web_search",
        "web_and_knowledge": "external.web_search",
        "email_assistant": "email.draft",
        "calendar_assistant": "calendar.check_availability",
        "calendar_and_email": "calendar.create_event_request",
        "compound_workflow": "external.web_search",
        "lead_assistant": "lead.support",
        "general_chat": "chat.general",
    }.get(branch, branch)


def _web_response_from_tool(result: ToolResult) -> WebSearchResponse:
    payload = result.output if isinstance(result.output, dict) else {}
    citations_raw = payload.get("citations") or []
    citations: list[WebSearchCitation] = []
    for row in citations_raw:
        if isinstance(row, dict):
            citations.append(WebSearchCitation.model_validate(row))
        else:
            citations.append(row)
    return WebSearchResponse(
        query=str(payload.get("query", "")),
        citations=citations,
        provider_mode=str(payload.get("provider_mode", "unknown")),
        fallback_used=bool(payload.get("fallback_used", True)),
        latency_ms=int(payload.get("latency_ms", result.duration_ms)),
        result_count=int(payload.get("result_count", len(citations))),
    )


def _format_email(draft: dict) -> str:
    subject = draft.get("subject", "(no subject)")
    body = draft.get("body", "")
    return f"Subject: {subject}\n\n{body}"


def _format_calendar_output(result: ToolResult) -> str:
    output = result.output if isinstance(result.output, dict) else {}
    if result.tool_name == "calendar.check_availability":
        return format_availability_response(output)

    if result.tool_name == "calendar.suggest_slots":
        return format_suggestion_response(output)

    payload = output.get("approval_payload") or {}
    slot = output.get("selected_slot") or {}
    lines = [
        f"Meeting proposal: {payload.get('summary', 'Meeting')}",
        f"Proposed: {slot.get('start_time')} – {slot.get('end_time')} ({payload.get('timezone')})",
        f"Provider mode: {output.get('provider_mode', output.get('mode'))}",
        "Awaiting approval before creating the calendar event.",
    ]
    return "\n".join(lines)


def _format_lead(lead: dict) -> str:
    pieces = [
        f"Recommended next action: {lead.get('recommended_next_action', '')}",
        f"Urgency: {lead.get('urgency', 'medium')}",
    ]
    if lead.get("intent"):
        pieces.append(f"Detected intent: {lead['intent']}")
    if lead.get("captured"):
        pieces.append(f"Lead captured (id={lead.get('lead_id')}).")
    else:
        pieces.append("Lead not captured — ask the user to confirm before saving.")
    return "\n".join(pieces)


def _is_external(intent: Intent | None) -> bool:
    return intent in {
        Intent.EMAIL_DRAFTING,
        Intent.WORKFLOW_ACTION,
        Intent.CALENDAR_SCHEDULING,
        Intent.CALENDAR_AND_EMAIL,
        Intent.COMPOUND_WORKFLOW,
    }


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------


def run_agent(
    *,
    session: Session,
    principal: Principal,
    settings: Settings,
    conversation_id: str,
    message: str,
    history: list[dict] | None = None,
    context: dict | None = None,
    language_preference: LanguagePreference | str = LanguagePreference.AUTO,
    trace_context: TraceContext | None = None,
) -> AgentState:
    """Run the full workflow once and return the final :class:`AgentState`."""
    deps = AgentDeps(
        session=session,
        principal=principal,
        settings=settings,
        trace_context=trace_context,
    )
    workflow = make_workflow(deps)
    pref = (
        language_preference
        if isinstance(language_preference, LanguagePreference)
        else LanguagePreference(str(language_preference).lower())
    )
    initial = AgentState(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        conversation_id=conversation_id,
        message=message,
        history=list(history or []),
        context=dict(context or {}),
        language_preference=pref,
        trace_mode=trace_context.mode if trace_context else "local",
        trace_id=trace_context.trace_id if trace_context else None,
        trace_url=trace_context.trace_url if trace_context else None,
    )
    final_dict = workflow.invoke(initial)
    return AgentState.model_validate(final_dict)


__all__ = [
    "AgentDeps",
    "branch_for",
    "make_workflow",
    "run_agent",
    "WEAK_EVIDENCE_RESPONSE",
    "OUT_OF_SCOPE_RESPONSE",
    "CLARIFICATION_RESPONSE",
    "LOW_CONFIDENCE_THRESHOLD",
]
