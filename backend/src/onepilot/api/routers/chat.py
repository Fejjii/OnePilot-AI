"""HTTP endpoints for chat (LangGraph agent) and conversation history."""

from __future__ import annotations

from fastapi import APIRouter

from onepilot.api.deps import CurrentPrincipal, DBSession, SettingsDep
from onepilot.core.constants import Intent
from onepilot.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageResponse,
    ToolCallTrace,
    TraceStep,
)
from onepilot.security.permissions import require_member
from onepilot.services import chat_service, conversation_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    principal: CurrentPrincipal,
    session: DBSession,
    settings: SettingsDep,
) -> ChatResponse:
    require_member(principal)
    outcome = chat_service.handle_chat(
        session,
        principal=principal,
        settings=settings,
        message=body.message,
        conversation_id=body.conversation_id,
        context=body.context,
    )
    state = outcome.state
    return ChatResponse(
        conversation_id=outcome.conversation.id,
        message_id=outcome.assistant_message.id,
        intent=state.intent or Intent.GENERAL_ASSISTANT,
        confidence=state.confidence,
        final_response=state.final_response or "",
        citations=[
            Citation(**(c.model_dump() if hasattr(c, "model_dump") else c))
            for c in state.citations
        ],
        tool_calls=[
            ToolCallTrace(**(t.model_dump() if hasattr(t, "model_dump") else t))
            for t in state.tool_calls
        ],
        approval_required=state.approval_required,
        approval_id=state.approval_id,
        usage=state.usage_metadata,
        trace_steps=[
            TraceStep(**(s.model_dump() if hasattr(s, "model_dump") else s))
            for s in state.trace_steps
        ],
        safety_flags=state.safety_flags,
    )


conversations_router = APIRouter(prefix="/conversations", tags=["conversations"])


@conversations_router.get("", response_model=ConversationListResponse)
def list_conversations(
    principal: CurrentPrincipal,
    session: DBSession,
    offset: int = 0,
    limit: int = 50,
) -> ConversationListResponse:
    require_member(principal)
    items, total = conversation_service.list_conversations(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        offset=offset,
        limit=limit,
    )
    summaries = [
        ConversationSummary(
            id=conv.id,
            title=conv.title,
            last_intent=conv.last_intent,
            message_count=0,
            last_message_at=conv.last_message_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
        )
        for conv in items
    ]
    return ConversationListResponse(items=summaries, total=total)


@conversations_router.get(
    "/{conversation_id}", response_model=ConversationDetailResponse
)
def get_conversation(
    conversation_id: str,
    principal: CurrentPrincipal,
    session: DBSession,
) -> ConversationDetailResponse:
    require_member(principal)
    conv, msgs = conversation_service.get_conversation_with_messages(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        conversation_id=conversation_id,
    )
    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        last_intent=conv.last_intent,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                confidence=m.confidence,
                citations=list(m.citations or []),
                tool_calls=list(m.tool_calls or []),
                created_at=m.created_at.isoformat(),
            )
            for m in msgs
        ],
    )
