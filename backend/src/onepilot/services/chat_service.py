"""Chat orchestrator service.

Drives the conversation lifecycle:
1. Enforce API rate limits and prompt-injection guardrails.
2. Enforce ``chat_messages`` quota.
3. Resolve (or create) the conversation.
4. Persist the user turn.
5. Build agent state with last-N history.
6. Run the LangGraph workflow with tracing.
7. Persist the assistant turn + record usage + audit log.
8. Return the assistant message id for the API layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from onepilot.agents.workflow import run_agent
from onepilot.core.config import Settings
from onepilot.core.constants import Intent, LanguagePreference, UsageFeature
from onepilot.core.logging import get_logger
from onepilot.observability.tracing import (
    TraceContext,
    TracingProvider,
    get_tracing_provider,
    sanitize_metadata,
)
from onepilot.repositories.models import Conversation, Message
from onepilot.schemas.agents import AgentState
from onepilot.schemas.chat import TraceStep
from onepilot.security.auth import Principal
from onepilot.security.prompt_injection import SafetyVerdict, check_prompt_injection
from onepilot.security.rate_limit import FEATURE_CHAT, enforce_rate_limit_for_principal
from onepilot.services import (
    audit_service,
    conversation_service,
    quota_service,
    usage_service,
)

logger = get_logger(__name__)

BLOCKED_INJECTION_MESSAGE = (
    "I can't process that request because it appears to contain unsafe instructions. "
    "Please rephrase your message as a normal business task."
)


@dataclass(slots=True)
class ChatOutcome:
    conversation: Conversation
    assistant_message: Message
    state: AgentState


def _handle_prompt_injection_block(
    session: Session,
    *,
    principal: Principal,
    message: str,
    conversation_id: str | None,
    verdict: SafetyVerdict,
    trace_context: TraceContext,
    tracing_provider: TracingProvider,
) -> ChatOutcome:
    """Persist a safe refusal without invoking the agent or tools."""
    tracing_provider.record_event(
        trace_context,
        "safety_check",
        {"blocked": True, "reasons": verdict.reasons},
    )
    tracing_provider.finalize_trace(trace_context)

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

    safety_step = TraceStep(
        step="safety_check",
        detail=", ".join(verdict.reasons),
    )
    state = AgentState(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        conversation_id=conversation.id,
        message=message,
        intent=Intent.GENERAL_ASSISTANT,
        confidence=1.0,
        final_response=BLOCKED_INJECTION_MESSAGE,
        safety_flags=["prompt_injection_blocked"],
        trace_steps=[safety_step],
        trace_mode=trace_context.mode,
        trace_id=trace_context.trace_id,
        trace_url=trace_context.trace_url,
    )

    assistant_msg = conversation_service.append_message(
        session,
        conversation=conversation,
        role="assistant",
        content=BLOCKED_INJECTION_MESSAGE,
        user_id=None,
        intent=state.intent.value,
        confidence=state.confidence,
        metadata={
            "safety_flags": state.safety_flags,
            "trace_mode": state.trace_mode,
            "trace_id": state.trace_id,
            "trace_url": state.trace_url,
        },
    )

    audit_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action="security.prompt_injection_blocked",
        resource_type="conversation",
        resource_id=conversation.id,
        detail={
            "reasons": verdict.reasons,
            "risk_score": verdict.risk_score,
            "message_preview": message[:240],
        },
    )
    session.commit()
    session.refresh(assistant_msg)
    logger.warning(
        "chat_prompt_injection_blocked",
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        conversation_id=conversation.id,
        reasons=verdict.reasons,
    )
    return ChatOutcome(
        conversation=conversation,
        assistant_message=assistant_msg,
        state=state,
    )


def handle_chat(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
    message: str,
    conversation_id: str | None = None,
    context: dict | None = None,
    language_preference: LanguagePreference | str = LanguagePreference.AUTO,
    history_turns: int = 10,
) -> ChatOutcome:
    started = time.monotonic()

    # Start trace
    tracing_provider = get_tracing_provider()
    trace_metadata = sanitize_metadata(
        {
            "organization_id": principal.organization_id,
            "user_id": principal.user_id,
            "conversation_id": conversation_id or "new",
            "message_length": len(message),
            "has_context": bool(context),
            "language_preference": str(language_preference),
        }
    )
    trace_context = tracing_provider.start_trace("chat.handle", trace_metadata)

    enforce_rate_limit_for_principal(principal, FEATURE_CHAT)

    injection_verdict = check_prompt_injection(message)
    if injection_verdict.blocked:
        return _handle_prompt_injection_block(
            session,
            principal=principal,
            message=message,
            conversation_id=conversation_id,
            verdict=injection_verdict,
            trace_context=trace_context,
            tracing_provider=tracing_provider,
        )

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
        language_preference=language_preference,
        trace_context=trace_context,
    )

    # Finalize trace
    tracing_provider.finalize_trace(trace_context)

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
            "trace_mode": state.trace_mode,
            "trace_id": state.trace_id,
            "trace_url": state.trace_url,
            "detected_language": state.detected_language,
            "response_language": state.response_language,
            "language_preference": state.language_preference.value,
        },
    )

    duration_ms = int((time.monotonic() - started) * 1000)
    usage_meta = state.usage_metadata or {}
    usage_service.record(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=UsageFeature.CHAT_MESSAGES.value,
        model=usage_meta.get("model"),
        provider=usage_meta.get("provider"),
        input_tokens=int(usage_meta.get("input_tokens", 0)),
        output_tokens=int(usage_meta.get("output_tokens", 0)),
        fallback_used=bool(usage_meta.get("fallback_used", False)),
        tool_calls=len(state.tool_calls) or int(usage_meta.get("tool_calls", 0)),
        latency_ms=duration_ms,
        metadata={
            "intent": state.intent.value if state.intent else None,
            "approval_required": state.approval_required,
            "safety_flags": state.safety_flags,
            "trace_mode": state.trace_mode,
            "detected_language": state.detected_language,
            "response_language": state.response_language,
            "language_preference": state.language_preference.value,
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
            "trace_mode": state.trace_mode,
            "detected_language": state.detected_language,
            "response_language": state.response_language,
            "language_preference": state.language_preference.value,
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
        trace_mode=state.trace_mode,
    )
    return ChatOutcome(
        conversation=conversation, assistant_message=assistant_msg, state=state
    )
