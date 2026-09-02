from __future__ import annotations

import json

from openai import OpenAI
from openai.types.chat import ChatCompletion

from onepilot.core.errors import ProviderUnavailableError
from onepilot.core.logging import get_logger
from onepilot.providers.llm.base import LLMProvider, LLMResponse
from onepilot.security.redaction import redact_sensitive

log = get_logger(__name__)

OPENAI_LLM_IMPLEMENTED = True
_GENERIC_FAILURE = "The language model is temporarily unavailable. Please try again shortly."


def uses_max_completion_tokens(model: str) -> bool:
    """GPT-5 / o-series chat models reject max_tokens and often temperature."""
    name = (model or "").strip().lower()
    return name.startswith(("gpt-5", "o1", "o3", "o4"))


class OpenAILLMProvider(LLMProvider):
    """OpenAI ChatCompletion-backed LLM provider."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o-mini",
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        max_output_tokens: int = 1024,
    ) -> None:
        if not api_key:
            raise ProviderUnavailableError("OpenAI API key not configured")
        self._api_key = api_key
        self._default_model = default_model
        self._max_output_tokens = max(1, int(max_output_tokens))
        self._client = OpenAI(
            api_key=api_key,
            timeout=float(timeout_seconds),
            max_retries=max(0, int(max_retries)),
        )

    def _capped_tokens(self, requested: int) -> int:
        return max(1, min(int(requested), self._max_output_tokens))

    def _completion_kwargs(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        extra: dict | None = None,
    ) -> dict:
        kwargs: dict = {
            "model": model,
            "messages": messages,
        }
        if extra:
            kwargs.update(extra)
        capped = self._capped_tokens(max_tokens)
        if uses_max_completion_tokens(model):
            kwargs["max_completion_tokens"] = capped
        else:
            kwargs["max_tokens"] = capped
            kwargs["temperature"] = temperature
        return kwargs

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        chosen = model or self._default_model
        try:
            response: ChatCompletion = self._client.chat.completions.create(
                **self._completion_kwargs(
                    model=chosen,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )

            choice = response.choices[0]
            content = choice.message.content or ""

            return LLMResponse(
                content=content,
                model=response.model,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            log.warning(
                "openai_chat_failed", error=redact_sensitive(str(exc)), model=chosen
            )
            raise ProviderUnavailableError(_GENERIC_FAILURE) from exc

    def chat_structured(
        self,
        messages: list[dict],
        response_schema: dict,
        model: str | None = None,
    ) -> LLMResponse:
        chosen = model or self._default_model
        try:
            enhanced_messages = messages.copy()
            if enhanced_messages and enhanced_messages[0].get("role") == "system":
                enhanced_messages[0]["content"] += (
                    f"\n\nYou must respond with valid JSON matching this schema: "
                    f"{json.dumps(response_schema)}"
                )
            else:
                enhanced_messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": (
                            "Respond with valid JSON matching this schema: "
                            f"{json.dumps(response_schema)}"
                        ),
                    },
                )

            response: ChatCompletion = self._client.chat.completions.create(
                **self._completion_kwargs(
                    model=chosen,
                    messages=enhanced_messages,
                    temperature=0.2,
                    max_tokens=self._max_output_tokens,
                    extra={"response_format": {"type": "json_object"}},
                )
            )

            choice = response.choices[0]
            content = choice.message.content or "{}"

            try:
                json.loads(content)
            except json.JSONDecodeError as je:
                log.warning(
                    "openai_invalid_json", error=redact_sensitive(str(je)), model=chosen
                )
                raise ProviderUnavailableError(_GENERIC_FAILURE) from je

            return LLMResponse(
                content=content,
                model=response.model,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            log.warning(
                "openai_structured_failed",
                error=redact_sensitive(str(exc)),
                model=chosen,
            )
            raise ProviderUnavailableError(_GENERIC_FAILURE) from exc
