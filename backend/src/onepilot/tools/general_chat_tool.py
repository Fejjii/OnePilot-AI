"""General chat tool.

Routed when the user has a conversational message that isn't a knowledge
question, a lead capture, or an email draft. Handles different message classes
appropriately:
- capability_or_help: Explains what the assistant can do
- conversational: Responds naturally to greetings, thanks, small talk
- correction_or_meta: Acknowledges corrections and asks for direction
- out_of_scope: Politely explains focus and redirects

Uses the configured LLM provider (falling back to the deterministic provider).
No external actions; no approval gating.
"""

from __future__ import annotations

import time
from typing import Any

from onepilot.core.constants import LanguageCode, MessageClass, UsageFeature
from onepilot.services.language_service import response_language_instruction
from onepilot.tools import general_chat_i18n
from onepilot.core.logging import get_logger
from onepilot.providers import get_llm_provider
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.services import usage_service
from onepilot.tools.base import Tool, ToolContext, ToolResult

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are OnePilot, a helpful business productivity assistant. You can assist with:\n"
    "- Searching knowledge bases and documents\n"
    "- Drafting emails and messages\n"
    "- Managing leads and customer inquiries\n"
    "- General business productivity questions and support\n\n"
    "Guidelines:\n"
    "- Be conversational, helpful, and concise\n"
    "- Handle user corrections gracefully - if they say something is wrong or unrelated, "
    "acknowledge it and ask what they'd like to do instead\n"
    "- For small talk or general questions, respond naturally and redirect to business tasks when appropriate\n"
    "- Never invent facts about the user's company or data\n"
    "- If unsure, ask clarifying questions\n"
    "- Keep responses professional but friendly"
)

# Message class specific prompts
CORRECTION_PROMPT = (
    "The user is correcting you or saying the previous response was not what they meant. "
    "Acknowledge this briefly without over-apologizing, and ask what they'd like to focus on instead. "
    "Keep your response short and redirect to helping them with their actual goal."
)

CONVERSATIONAL_PROMPT = (
    "The user is making small talk, greeting you, or thanking you. "
    "Respond naturally and briefly. Don't force business productivity messaging unless they ask. "
    "Be friendly and human. If appropriate, gently ask if there's anything you can help with."
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
        message_class: MessageClass | None = None,
        response_language: str = "en",
        memory_block: str = "",
        **_: Any,
    ) -> ToolResult:
        lang = response_language
        # Handle capability/help questions with template response
        if message_class == MessageClass.CAPABILITY_OR_HELP:
            return ToolResult(
                tool_name=self.name,
                input_summary=f"capability question: {message[:120]}",
                output_summary="template_capability_response",
                output={
                    "reply": general_chat_i18n.get_capability(lang),
                    "model": "template",
                    "fallback_used": False,
                },
                duration_ms=0,
                safety_flags=[],
                usage={"model": "template", "fallback_used": False},
            )

        # Handle out-of-scope with template response
        if message_class == MessageClass.OUT_OF_SCOPE:
            return ToolResult(
                tool_name=self.name,
                input_summary=f"out_of_scope: {message[:120]}",
                output_summary="template_out_of_scope_response",
                output={
                    "reply": general_chat_i18n.get_out_of_scope(lang),
                    "model": "template",
                    "fallback_used": False,
                },
                duration_ms=0,
                safety_flags=["out_of_scope"],
                usage={"model": "template", "fallback_used": False},
            )

        # For other message classes, use LLM with appropriate system prompt
        llm = get_llm_provider(ctx.settings)
        is_fallback = isinstance(llm, FallbackLLMProvider)

        try:
            lang_code = LanguageCode(str(lang).lower())
        except ValueError:
            lang_code = LanguageCode.EN

        # Build system prompt based on message class
        system_prompt = SYSTEM_PROMPT + "\n\n" + response_language_instruction(lang_code)
        if message_class == MessageClass.CORRECTION_OR_META:
            system_prompt = system_prompt + "\n\n" + CORRECTION_PROMPT
        elif message_class == MessageClass.CONVERSATIONAL:
            system_prompt = system_prompt + "\n\n" + CONVERSATIONAL_PROMPT
        if memory_block:
            system_prompt = system_prompt + "\n\n" + memory_block

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for entry in (history or [])[-6:]:
            role = entry.get("role")
            content = entry.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        # Current user message is always separate from stored memory.
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
            metadata={
                "intent": "general_assistant",
                "message_class": str(message_class) if message_class else None,
                "response_language": lang_code.value,
            },
        )

        return ToolResult(
            tool_name=self.name,
            input_summary=f"general chat ({message_class}): {message[:120]}",
            output_summary=f"chars={len(response.content)} model={response.model}",
            output={
                "reply": response.content,
                "model": response.model,
                "fallback_used": is_fallback,
            },
            duration_ms=duration_ms,
            safety_flags=["fallback_used"] if is_fallback else [],
            usage={
                "model": response.model,
                "provider": type(llm).__name__,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "fallback_used": is_fallback,
            },
        )
