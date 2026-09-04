"""HTTP endpoints for chat (LangGraph agent) and conversation history."""

from __future__ import annotations

from fastapi import APIRouter, Request

from onepilot.api.deps import CurrentPrincipal, DBSession, SettingsDep
from onepilot.core.constants import Intent
from onepilot.repositories.models import Message
from onepilot.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageResponse,
)
from onepilot.security.permissions import require_member
from onepilot.security.rate_limit import client_ip_from_request
from onepilot.services import chat_service, conversation_service
from onepilot.services.execution_trace import (
    build_execution_trace,
    execution_trace_from_metadata,
    sanitize_public_trace_steps,
    sanitize_tool_calls,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: Request,
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
        language_preference=body.language_preference,
        client_ip=client_ip_from_request(request),
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
        tool_calls=sanitize_tool_calls(state.tool_calls),
        approval_required=state.approval_required,
        approval_id=state.approval_id,
        usage=state.usage_metadata,
        trace_steps=sanitize_public_trace_steps(state.trace_steps),
        execution_trace=build_execution_trace(
            trace_steps=state.trace_steps,
            tool_calls=state.tool_calls,
            approval_required=state.approval_required,
        ),
        safety_flags=state.safety_flags,
        trace_mode=state.trace_mode,
        trace_id=state.trace_id,
        trace_url=state.trace_url,
        detected_language=state.detected_language,
        response_language=state.response_language,
        language_preference=state.language_preference,
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
        messages=[_message_response(m) for m in msgs],
    )


@conversations_router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    principal: CurrentPrincipal,
    session: DBSession,
) -> None:
    require_member(principal)
    conversation_service.delete_conversation(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        conversation_id=conversation_id,
    )


def _message_response(message: Message) -> MessageResponse:
    """Map a persisted message to the public conversation payload.

    Historical rows without execution-trace metadata render as an empty
    trace list. Tool summaries are re-sanitized so older stored query text
    is not returned to the client.
    """
    meta = message.msg_metadata or {}
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        intent=message.intent,
        confidence=message.confidence,
        citations=list(message.citations or []),
        tool_calls=sanitize_tool_calls(message.tool_calls or []),
        created_at=message.created_at.isoformat(),
        trace_mode=meta.get("trace_mode"),
        trace_id=meta.get("trace_id"),
        trace_url=meta.get("trace_url"),
        span_count=meta.get("span_count"),
        execution_trace=execution_trace_from_metadata(meta),
        approval_required=bool(meta.get("approval_required", False)),
        approval_id=meta.get("approval_id"),
        safety_flags=list(meta.get("safety_flags") or []),
        detected_language=meta.get("detected_language"),
        response_language=meta.get("response_language"),
        language_preference=meta.get("language_preference"),
    )
