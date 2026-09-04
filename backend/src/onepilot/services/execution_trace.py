"""Recruiter-facing execution traces.

Internal LangGraph ``trace_steps`` include classifier reasons, memory flags,
and other hidden routing detail. This module maps only observable application
actions to concise, safe labels and strips anything that must never reach the
UI or persisted message metadata:

- chain-of-thought / hidden reasoning
- prompts
- secrets, tokens, credentials
- raw provider payloads
- internal exceptions
- sensitive / raw IDs
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

from onepilot.schemas.chat import ExecutionTraceStep, ToolCallTrace, TraceStep

# Observable steps shown to recruiters. Keys are stable for tests and UI.
UNDERSTANDING_REQUEST = "understanding_request"
READING_CRM_CONTEXT = "reading_crm_context"
SEARCHING_COMPANY_KNOWLEDGE = "searching_company_knowledge"
RETRIEVING_RAG_EVIDENCE = "retrieving_rag_evidence"
SEARCHING_THE_WEB = "searching_the_web"
DRAFTING_EMAIL = "drafting_email"
CHECKING_CALENDAR = "checking_calendar"
FINDING_MEETING_TIMES = "finding_meeting_times"
CREATING_APPROVAL = "creating_approval"
REVIEWING_WORKSPACE = "reviewing_workspace"
DRAFTING_REPLY = "drafting_reply"
ASKING_CLARIFICATION = "asking_clarification"
CHECKING_REQUEST_SCOPE = "checking_request_scope"
SAFETY_CHECK = "safety_check"

_STEP_LABELS: dict[str, str] = {
    UNDERSTANDING_REQUEST: "Understanding request",
    READING_CRM_CONTEXT: "Reading CRM context",
    SEARCHING_COMPANY_KNOWLEDGE: "Searching company knowledge",
    RETRIEVING_RAG_EVIDENCE: "Retrieving RAG evidence",
    SEARCHING_THE_WEB: "Searching the web",
    DRAFTING_EMAIL: "Drafting email",
    CHECKING_CALENDAR: "Checking calendar",
    FINDING_MEETING_TIMES: "Finding meeting times",
    CREATING_APPROVAL: "Creating approval",
    REVIEWING_WORKSPACE: "Reviewing workspace activity",
    DRAFTING_REPLY: "Drafting reply",
    ASKING_CLARIFICATION: "Asking for clarification",
    CHECKING_REQUEST_SCOPE: "Checking request scope",
    SAFETY_CHECK: "Safety check",
}

# Internal graph nodes that must never be shown as-is.
_HIDDEN_INTERNAL_STEPS = {
    "resolve_language",
    "recall_memory",
    "route",
    "router",
    "persist_memory",
    "finalize_response",
    "guardrail",
}

# Compound nodes are expanded from the individual tool calls instead.
_COMPOUND_INTERNAL_STEPS = {
    "execute_tool:calendar_and_email",
    "execute_tool:compound_workflow",
    "execute_tool:web_and_knowledge",
}

_INTERNAL_STEP_TO_KEY: dict[str, str] = {
    "classify_message": UNDERSTANDING_REQUEST,
    "classify_intent": UNDERSTANDING_REQUEST,
    "safety_check": SAFETY_CHECK,
    "execute_tool:rag.answer": RETRIEVING_RAG_EVIDENCE,
    "execute_tool:email.draft": DRAFTING_EMAIL,
    "execute_tool:calendar.check_availability": CHECKING_CALENDAR,
    "execute_tool:calendar.suggest_slots": FINDING_MEETING_TIMES,
    "execute_tool:calendar.create_event_request": CREATING_APPROVAL,
    "execute_tool:lead.support": READING_CRM_CONTEXT,
    "execute_tool:external.web_search": SEARCHING_THE_WEB,
    "execute_tool:workspace.insights": REVIEWING_WORKSPACE,
    "execute_tool:chat.general": DRAFTING_REPLY,
    "execute_tool:clarification": ASKING_CLARIFICATION,
    "execute_tool:out_of_scope": CHECKING_REQUEST_SCOPE,
}

_TOOL_TO_KEY: dict[str, str] = {
    "rag.answer": RETRIEVING_RAG_EVIDENCE,
    "knowledge.search": SEARCHING_COMPANY_KNOWLEDGE,
    "email.draft": DRAFTING_EMAIL,
    "calendar.check_availability": CHECKING_CALENDAR,
    "calendar.suggest_slots": FINDING_MEETING_TIMES,
    "calendar.create_event_request": CREATING_APPROVAL,
    "lead.support": READING_CRM_CONTEXT,
    "external.web_search": SEARCHING_THE_WEB,
    "workspace.insights": REVIEWING_WORKSPACE,
    "chat.general": DRAFTING_REPLY,
}

_TOOL_LABELS: dict[str, str] = {
    "rag.answer": "Knowledge",
    "knowledge.search": "Knowledge",
    "email.draft": "Email",
    "calendar.check_availability": "Calendar",
    "calendar.suggest_slots": "Calendar",
    "calendar.create_event_request": "Calendar",
    "lead.support": "CRM",
    "external.web_search": "Web",
    "workspace.insights": "Insights",
    "chat.general": "Chat",
}

_SAFE_TOOL_SUMMARIES: dict[str, tuple[str, str]] = {
    "rag.answer": ("Company knowledge search", "Retrieved knowledge evidence"),
    "knowledge.search": ("Company knowledge search", "Retrieved knowledge evidence"),
    "email.draft": ("Email draft request", "Prepared email draft"),
    "calendar.check_availability": ("Calendar availability check", "Checked availability"),
    "calendar.suggest_slots": ("Meeting-time search", "Suggested meeting times"),
    "calendar.create_event_request": ("Calendar event request", "Created approval"),
    "lead.support": ("CRM context lookup", "Read CRM context"),
    "external.web_search": ("Web search", "Retrieved web results"),
    "workspace.insights": ("Workspace activity review", "Summarized workspace activity"),
    "chat.general": ("Assistant reply", "Drafted reply"),
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|password|secret|token|authorization|bearer|credential)s?\b"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{8,}"),
    re.compile(r"(?i)eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(postgres|mysql|mongodb|redis|amqp)://\S+"),
)
_UNSAFE_DETAIL = re.compile(
    r"(?i)(traceback|exception|stack trace|system prompt|hidden reasoning|"
    r"chain.of.thought|prompt=|reason=|class=|message_class=)"
)
_RAW_ID = re.compile(r"\b(?:msg|conv|org|usr|user|approval|lead)_[A-Za-z0-9]+\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def step_label(key: str) -> str:
    """Return the recruiter-facing label for an execution-trace key."""
    return _STEP_LABELS.get(key, "Application action")


def tool_label(tool_name: str) -> str:
    """Return a concise recruiter-facing badge label for a tool identifier."""
    if tool_name in _TOOL_LABELS:
        return _TOOL_LABELS[tool_name]
    if tool_name.startswith("calendar."):
        return "Calendar"
    if tool_name.startswith("email."):
        return "Email"
    return "Tool"


def build_execution_trace(
    *,
    trace_steps: Iterable[TraceStep | dict[str, Any]] | None = None,
    tool_calls: Iterable[ToolCallTrace | dict[str, Any]] | None = None,
    approval_required: bool = False,
) -> list[ExecutionTraceStep]:
    """Derive a safe, de-duplicated list of observable execution steps."""
    steps: list[ExecutionTraceStep] = []
    seen: set[str] = set()

    def add(key: str, *, duration_ms: int = 0) -> None:
        if key in seen or key not in _STEP_LABELS:
            return
        seen.add(key)
        steps.append(
            ExecutionTraceStep(
                key=key,
                label=_STEP_LABELS[key],
                detail=None,
                duration_ms=max(0, int(duration_ms)),
            )
        )

    for raw in trace_steps or []:
        step_name = _step_name(raw)
        if not step_name or step_name in _HIDDEN_INTERNAL_STEPS:
            continue
        if step_name in _COMPOUND_INTERNAL_STEPS:
            continue
        key = _INTERNAL_STEP_TO_KEY.get(step_name)
        if key is None:
            continue
        add(key, duration_ms=_duration_ms(raw))

    for raw in tool_calls or []:
        name = _tool_name(raw)
        key = _TOOL_TO_KEY.get(name)
        if key is None and name.startswith("calendar."):
            key = CHECKING_CALENDAR
        if key is None:
            continue
        add(key, duration_ms=_duration_ms(raw))

    if approval_required:
        add(CREATING_APPROVAL)

    return steps


def sanitize_public_trace_steps(
    trace_steps: Iterable[TraceStep | dict[str, Any]] | None,
) -> list[TraceStep]:
    """Keep internal step names for API compatibility, drop unsafe details."""
    public: list[TraceStep] = []
    for raw in trace_steps or []:
        name = _step_name(raw)
        if not name:
            continue
        public.append(
            TraceStep(
                step=name,
                detail=None,
                intent=_optional_intent(raw),
                duration_ms=_duration_ms(raw),
            )
        )
    return public


def sanitize_tool_calls(
    tool_calls: Iterable[ToolCallTrace | dict[str, Any]] | None,
) -> list[ToolCallTrace]:
    """Return tool traces with safe labels and non-sensitive summaries."""
    sanitized: list[ToolCallTrace] = []
    for raw in tool_calls or []:
        name = _tool_name(raw)
        if not name:
            continue
        input_summary, output_summary = _SAFE_TOOL_SUMMARIES.get(
            name, ("Application action", "Completed")
        )
        sanitized.append(
            ToolCallTrace(
                tool_name=name,
                label=tool_label(name),
                input_summary=input_summary,
                output_summary=output_summary,
                duration_ms=_duration_ms(raw),
            )
        )
    return sanitized


def execution_trace_from_metadata(metadata: dict[str, Any] | None) -> list[ExecutionTraceStep]:
    """Load persisted traces; missing or malformed history yields an empty list."""
    if not metadata:
        return []
    raw = metadata.get("execution_trace")
    if not isinstance(raw, list):
        return []
    steps: list[ExecutionTraceStep] = []
    for item in raw:
        step = _safe_persisted_step(item)
        if step is not None:
            steps.append(step)
    return steps


def execution_trace_as_dicts(steps: Iterable[ExecutionTraceStep]) -> list[dict[str, Any]]:
    """JSON-ready payload for message metadata."""
    return [step.model_dump() for step in steps]


def is_safe_public_text(value: str | None) -> bool:
    """True when a short label/detail is safe to show to recruiters."""
    if value is None:
        return False
    text = value.strip()
    if not text or len(text) > 160:
        return False
    if _SECRET_PATTERNS[0].search(text) or _UNSAFE_DETAIL.search(text):
        return False
    if any(pattern.search(text) for pattern in _SECRET_PATTERNS[1:]):
        return False
    return not (_RAW_ID.search(text) or _EMAIL.search(text))


def _safe_persisted_step(item: Any) -> ExecutionTraceStep | None:
    if not isinstance(item, dict):
        return None
    key = str(item.get("key") or "").strip()
    label = str(item.get("label") or "").strip()
    if key not in _STEP_LABELS:
        return None
    expected = _STEP_LABELS[key]
    if label != expected:
        label = expected
    detail_raw = item.get("detail")
    detail = str(detail_raw).strip() if isinstance(detail_raw, str) else None
    if detail and not is_safe_public_text(detail):
        detail = None
    try:
        duration_ms = max(0, int(item.get("duration_ms") or 0))
    except (TypeError, ValueError):
        duration_ms = 0
    return ExecutionTraceStep(
        key=key, label=label, detail=detail, duration_ms=duration_ms
    )


def _step_name(raw: TraceStep | dict[str, Any]) -> str:
    if isinstance(raw, TraceStep):
        return raw.step
    if isinstance(raw, dict):
        return str(raw.get("step") or "")
    return ""


def _tool_name(raw: ToolCallTrace | dict[str, Any]) -> str:
    if isinstance(raw, ToolCallTrace):
        return raw.tool_name
    if isinstance(raw, dict):
        return str(raw.get("tool_name") or "")
    return ""


def _duration_ms(raw: Any) -> int:
    if isinstance(raw, (TraceStep, ToolCallTrace)):
        return max(0, int(raw.duration_ms))
    if isinstance(raw, dict):
        try:
            return max(0, int(raw.get("duration_ms") or 0))
        except (TypeError, ValueError):
            return 0
    return 0


def _optional_intent(raw: TraceStep | dict[str, Any]) -> Any:
    if isinstance(raw, TraceStep):
        return raw.intent
    if isinstance(raw, dict):
        return raw.get("intent")
    return None
