from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from onepilot.core.constants import Intent


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = None
    context: dict | None = None


class Citation(BaseModel):
    document_id: str
    document_title: str
    section: str | None = None
    chunk_text: str
    relevance_score: float


class ToolCallTrace(BaseModel):
    tool_name: str
    input_summary: str
    output_summary: str
    duration_ms: int


class TraceStep(BaseModel):
    step: str
    detail: str | None = None
    intent: Intent | None = None
    duration_ms: int = 0


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    intent: Intent
    confidence: float
    final_response: str
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    approval_required: bool = False
    approval_id: str | None = None
    usage: dict = Field(default_factory=dict)
    trace_steps: list[TraceStep] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    intent: str | None = None
    confidence: float = 0.0
    citations: list = Field(default_factory=list)
    tool_calls: list = Field(default_factory=list)
    created_at: str


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    last_intent: str | None = None
    message_count: int = 0
    last_message_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]
    total: int


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    last_intent: str | None = None
    messages: list[MessageResponse]
