"""General chat tool.

Routed when the user has a conversational message that isn't a knowledge
question, a lead capture, or an email draft. Uses the configured LLM provider
(falling back to the deterministic provider). No external actions; no
approval gating.
"""

from __future__ import annotations

import time
from typing import Any

from onepilot.core.constants import UsageFeature
from onepilot.core.logging import get_logger
from onepilot.providers import get_llm_provider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.services import usage_service
from onepilot.tools.base import Tool, ToolContext, ToolResult

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are OnePilot, a business productivity assistant. Be concise, helpful, "
    "and accurate. Never invent facts about the user's company. If you are not "
    "sure, say so and ask a clarifying question."
)


class GeneralChatTool(Tool):
    name = "chat.general"
    description = "Conversational reply for general assistant messages."

    def run(
        self,
        ctx: ToolContext,
        *,
        message: str,
        history: list[dict] | None = None,
        **_: Any,
    ) -> ToolResult:
        llm = get_llm_provider(ctx.settings)
        is_fallback = isinstance(llm, FallbackLLMProvider)

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for entry in (history or [])[-6:]:
            role = entry.get("role")
            content = entry.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        started = time.monotonic()
        response = llm.chat(messages=messages, temperature=0.4, max_tokens=600)
        duration_ms = int((time.monotonic() - started) * 1000)

        usage_service.record(
            ctx.session,
            organization_id=ctx.principal.organization_id,
            user_id=ctx.principal.user_id,
            feature=UsageFeature.CHAT_MESSAGES.value,
            model=response.model,
            provider=type(llm).__name__,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            fallback_used=is_fallback,
            latency_ms=duration_ms,
            metadata={"intent": "general_assistant"},
        )

        return ToolResult(
            tool_name=self.name,
            input_summary=f"general chat: {message[:120]}",
            output_summary=f"chars={len(response.content)} model={response.model}",
            output={
                "reply": response.content,
                "model": response.model,
                "fallback_used": is_fallback,
            },
            duration_ms=duration_ms,
            safety_flags=["fallback_used"] if is_fallback else [],
            usage={"model": response.model, "fallback_used": is_fallback},
        )
