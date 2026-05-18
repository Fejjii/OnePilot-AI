from __future__ import annotations

import json

from openai import OpenAI
from openai.types.chat import ChatCompletion

from onepilot.core.errors import ProviderUnavailableError
from onepilot.providers.llm.base import LLMProvider, LLMResponse


OPENAI_LLM_IMPLEMENTED = True


class OpenAILLMProvider(LLMProvider):
    """OpenAI ChatCompletion-backed LLM provider."""

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini") -> None:
        if not api_key:
            raise ProviderUnavailableError("OpenAI API key not configured")
        self._api_key = api_key
        self._default_model = default_model
        self._client = OpenAI(api_key=api_key)

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Call OpenAI chat completion API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with content and metadata
            
        Raises:
            ProviderUnavailableError: If API call fails
        """
        try:
            response: ChatCompletion = self._client.chat.completions.create(
                model=model or self._default_model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
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
        except Exception as exc:
            raise ProviderUnavailableError(f"OpenAI API call failed: {exc}") from exc

    def chat_structured(
        self,
        messages: list[dict],
        response_schema: dict,
        model: str | None = None,
    ) -> LLMResponse:
        """Call OpenAI with structured output (JSON mode).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            response_schema: JSON schema for structured response
            model: Model to use (defaults to configured model)
            
        Returns:
            LLMResponse with JSON content
            
        Raises:
            ProviderUnavailableError: If API call fails
        """
        try:
            # Add system instruction for JSON formatting
            enhanced_messages = messages.copy()
            if enhanced_messages and enhanced_messages[0].get("role") == "system":
                enhanced_messages[0]["content"] += (
                    f"\n\nYou must respond with valid JSON matching this schema: "
                    f"{json.dumps(response_schema)}"
                )
            else:
                enhanced_messages.insert(0, {
                    "role": "system",
                    "content": f"Respond with valid JSON matching this schema: {json.dumps(response_schema)}"
                })
            
            response: ChatCompletion = self._client.chat.completions.create(
                model=model or self._default_model,
                messages=enhanced_messages,  # type: ignore
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            
            choice = response.choices[0]
            content = choice.message.content or "{}"
            
            # Validate JSON
            try:
                json.loads(content)
            except json.JSONDecodeError as je:
                raise ProviderUnavailableError(f"OpenAI returned invalid JSON: {je}") from je
            
            return LLMResponse(
                content=content,
                model=response.model,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )
        except Exception as exc:
            if isinstance(exc, ProviderUnavailableError):
                raise
            raise ProviderUnavailableError(f"OpenAI structured API call failed: {exc}") from exc
