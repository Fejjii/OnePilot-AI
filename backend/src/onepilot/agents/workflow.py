"""LangGraph agent workflow.

Graph:

    classify_intent -> route -> {branch} -> guardrail -> finalize_response

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
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from onepilot.agents.intent_classifier import classify as classify_intent_fn
from onepilot.core.config import Settings
from onepilot.core.constants import Intent
from onepilot.core.logging import get_logger
from onepilot.schemas.agents import AgentState
from onepilot.schemas.chat import Citation, ToolCallTrace, TraceStep
from onepilot.security.auth import Principal
from onepilot.services import approval_service
from onepilot.tools import registry as _tools_bootstrap  # noqa: F401  ensures tool registration
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
    Intent.EMAIL_DRAFTING: "email_assistant",
    Intent.LEAD_SUPPORT: "lead_assistant",
    Intent.WORKFLOW_ACTION: "lead_assistant",
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

    def classify_intent_node(state: AgentState) -> dict:
        started = time.monotonic()
        result = classify_intent_fn(state.message, settings=deps.settings, use_llm=False)
        duration_ms = int((time.monotonic() - started) * 1000)
        update: dict[str, Any] = {
            "intent": result.intent,
            "confidence": result.confidence,
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
        result = registry.get("rag.answer").run(_ctx(deps), query=state.message)
        _record_tool_call(update, result)
        update["draft_output"] = result.output.get("answer", "")
        update["confidence"] = max(state.confidence, float(result.output.get("confidence", 0.0)))
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
        result = registry.get("email.draft").run(
            _ctx(deps),
            context=state.message,
            tone=state.context.get("tone", "professional"),
            recipient_name=state.context.get("recipient_name"),
            recipient_email=state.context.get("recipient_email"),
            action=state.context.get("action", "draft_only"),
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
        )
        _record_tool_call(update, result)
        update["draft_output"] = result.output.get("reply", "")
        _append_trace(update, "execute_tool:chat.general", duration_ms=result.duration_ms)
        return update

    def clarification_node(state: AgentState) -> dict:
        flags = list(state.safety_flags)
        if "clarification_requested" not in flags:
            flags.append("clarification_requested")
        return {
            "draft_output": CLARIFICATION_RESPONSE,
            "safety_flags": flags,
            "trace_steps": list(state.trace_steps)
            + [TraceStep(step="execute_tool:clarification").model_dump()],
        }

    def out_of_scope_node(state: AgentState) -> dict:
        flags = list(state.safety_flags)
        if "out_of_scope" not in flags:
            flags.append("out_of_scope")
        return {
            "draft_output": OUT_OF_SCOPE_RESPONSE,
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
            draft = WEAK_EVIDENCE_RESPONSE

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
            final = (
                final.rstrip()
                + "\n\n*Pending approval before any external action is taken.*"
            )
        return {
            "final_response": final,
            "trace_steps": list(state.trace_steps)
            + [TraceStep(step="finalize_response").model_dump()],
        }

    graph: StateGraph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("route", route_node)
    graph.add_node("knowledge_search", knowledge_search_node)
    graph.add_node("email_assistant", email_assistant_node)
    graph.add_node("lead_assistant", lead_assistant_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("out_of_scope", out_of_scope_node)
    graph.add_node("guardrail", guardrail_node)
    graph.add_node("finalize_response", finalize_node)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "route")
    graph.add_conditional_edges(
        "route",
        lambda s: branch_for(s.intent),
        {
            "knowledge_search": "knowledge_search",
            "email_assistant": "email_assistant",
            "lead_assistant": "lead_assistant",
            "general_chat": "general_chat",
            "clarification": "clarification",
            "out_of_scope": "out_of_scope",
        },
    )
    for branch in (
        "knowledge_search",
        "email_assistant",
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
        "email_assistant": "email.draft",
        "lead_assistant": "lead.support",
        "general_chat": "chat.general",
    }.get(branch, branch)


def _format_email(draft: dict) -> str:
    subject = draft.get("subject", "(no subject)")
    body = draft.get("body", "")
    return f"Subject: {subject}\n\n{body}"


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
) -> AgentState:
    """Run the full workflow once and return the final :class:`AgentState`."""
    deps = AgentDeps(session=session, principal=principal, settings=settings)
    workflow = make_workflow(deps)
    initial = AgentState(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        conversation_id=conversation_id,
        message=message,
        history=list(history or []),
        context=dict(context or {}),
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
