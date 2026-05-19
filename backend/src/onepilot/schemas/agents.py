"""Pydantic state objects for the LangGraph agent.

The agent state is intentionally a Pydantic model so it can be serialized for
tracing and so each step is explicitly typed. It also doubles as the
``state_schema`` for ``langgraph.graph.StateGraph``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from onepilot.core.constants import Intent, LanguagePreference, MessageClass
from onepilot.schemas.chat import Citation, ToolCallTrace, TraceStep


class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    user_id: str
    conversation_id: str
    message: str

    # Stage 1: Message classification
    message_class: MessageClass | None = None
    message_class_confidence: float = 0.0
    message_class_reason: str = ""

    # Stage 2: Intent classification
    intent: Intent | None = None
    confidence: float = 0.0
    route_reason: str = ""

    selected_tools: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    draft_output: str | None = None
    approval_required: bool = False
    approval_id: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    usage_metadata: dict = Field(default_factory=dict)
    final_response: str | None = None
    trace_steps: list[TraceStep] = Field(default_factory=list)

    # Trace metadata
    trace_mode: str = "local"  # "local" or "langsmith"
    trace_id: str | None = None
    trace_url: str | None = None

    history: list[dict] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)

    language_preference: LanguagePreference = LanguagePreference.AUTO
    detected_language: str = "en"
    response_language: str = "en"
