"""Chat orchestrator service.

Drives the conversation lifecycle:
1. Enforce ``chat_messages`` quota.
2. Resolve (or create) the conversation.
3. Persist the user turn.
4. Build agent state with last-N history.
5. Run the LangGraph workflow.
6. Persist the assistant turn + record usage + audit log.
7. Return the assistant message id for the API layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from onepilot.agents.workflow import run_agent
from onepilot.core.config import Settings
from onepilot.core.constants import UsageFeature
from onepilot.core.logging import get_logger
from onepilot.repositories.models import Conversation, Message
from onepilot.schemas.agents import AgentState
from onepilot.security.auth import Principal
from onepilot.services import (
    audit_service,
    conversation_service,
    quota_service,
    usage_service,
)

logger = get_logger(__name__)


@dataclass(slots=True)
class ChatOutcome:
    conversation: Conversation
    assistant_message: Message
    state: AgentState


def handle_chat(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
    message: str,
    conversation_id: str | None = None,
    context: dict | None = None,
    history_turns: int = 10,
) -> ChatOutcome:
    started = time.monotonic()
    quota_service.check_and_increment(
        session,
        principal.organization_id,
        UsageFeature.CHAT_MESSAGES,
        amount=1,
    )

    conversation = conversation_service.get_or_create_conversation(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        conversation_id=conversation_id,
        title_hint=message,
    )

    conversation_service.append_message(
        session,
        conversation=conversation,
        role="user",
        content=message,
        user_id=principal.user_id,
    )

    history = conversation_service.recent_history(
        session,
        organization_id=principal.organization_id,
        conversation_id=conversation.id,
        limit=history_turns,
    )
    # The latest user turn is already the last entry in history; drop it so the
    # agent sees only prior context.
    if history and history[-1]["role"] == "user":
        history = history[:-1]

    state = run_agent(
        session=session,
        principal=principal,
        settings=settings,
        conversation_id=conversation.id,
        message=message,
        history=history,
        context=context,
    )

    assistant_msg = conversation_service.append_message(
        session,
        conversation=conversation,
        role="assistant",
        content=state.final_response or "",
        user_id=None,
        intent=state.intent.value if state.intent else None,
        confidence=state.confidence,
        citations=[c.model_dump() if hasattr(c, "model_dump") else c for c in state.citations],
        tool_calls=[
            tc.model_dump() if hasattr(tc, "model_dump") else tc for tc in state.tool_calls
        ],
        metadata={
            "approval_required": state.approval_required,
            "approval_id": state.approval_id,
            "safety_flags": state.safety_flags,
            "usage": state.usage_metadata,
        },
    )

    duration_ms = int((time.monotonic() - started) * 1000)
    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=UsageFeature.CHAT_MESSAGES.value,
        provider="onepilot.chat_service",
        tool_calls=len(state.tool_calls),
        latency_ms=duration_ms,
        metadata={
            "intent": state.intent.value if state.intent else None,
            "approval_required": state.approval_required,
            "safety_flags": state.safety_flags,
        },
    )
    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="chat.message_handled",
        resource_type="conversation",
        resource_id=conversation.id,
        detail={
            "intent": state.intent.value if state.intent else None,
            "confidence": state.confidence,
            "approval_required": state.approval_required,
            "safety_flags": state.safety_flags,
        },
    )
    session.commit()
    session.refresh(assistant_msg)
    logger.info(
        "chat_handled",
        organization_id=principal.organization_id,
        conversation_id=conversation.id,
        intent=state.intent.value if state.intent else None,
        approval_required=state.approval_required,
    )
    return ChatOutcome(
        conversation=conversation, assistant_message=assistant_msg, state=state
    )
