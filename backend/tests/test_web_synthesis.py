"""Web synthesis polish must stay bounded and countable for demo spend controls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from onepilot.agents.workflow import _merge_polish_usage
from onepilot.providers.llm.base import LLMResponse
from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
from onepilot.services.web_synthesis import maybe_llm_polish


def test_maybe_llm_polish_skips_without_openai() -> None:
    draft = "## Summary\nKeep me."
    result = maybe_llm_polish(
        query="SMB trends",
        draft=draft,
        settings=SimpleNamespace(has_openai=False),
    )
    assert result.text == draft
    assert result.input_tokens == 0
    assert result.output_tokens == 0


def test_maybe_llm_polish_skips_fallback_provider() -> None:
    draft = "## Summary\nKeep me."
    with patch(
        "onepilot.providers.get_llm_provider",
        return_value=FallbackLLMProvider(),
    ):
        result = maybe_llm_polish(
            query="SMB trends",
            draft=draft,
            settings=SimpleNamespace(has_openai=True),
        )
    assert result.text == draft
    assert result.input_tokens == 0


def test_maybe_llm_polish_returns_token_usage() -> None:
    draft = "## Summary\nOriginal."
    llm = MagicMock()
    llm.chat.return_value = LLMResponse(
        content="## Summary\nPolished.",
        model="gpt-4o-mini",
        input_tokens=40,
        output_tokens=25,
        finish_reason="stop",
    )
    with patch("onepilot.providers.get_llm_provider", return_value=llm):
        result = maybe_llm_polish(
            query="SMB trends",
            draft=draft,
            settings=SimpleNamespace(has_openai=True),
        )
    assert result.text == "## Summary\nPolished."
    assert result.input_tokens == 40
    assert result.output_tokens == 25
    assert result.model == "gpt-4o-mini"
    llm.chat.assert_called_once()
    assert llm.chat.call_args.kwargs["max_tokens"] == 300


def test_merge_polish_usage_adds_tokens_without_clobbering() -> None:
    from onepilot.services.web_synthesis import PolishResult

    update = {"usage_metadata": {"input_tokens": 10, "output_tokens": 5, "provider": "rag"}}
    text = _merge_polish_usage(
        update,
        PolishResult(
            text="polished", input_tokens=40, output_tokens=25, model="gpt-4o-mini"
        ),
    )
    assert text == "polished"
    assert update["usage_metadata"]["input_tokens"] == 50
    assert update["usage_metadata"]["output_tokens"] == 30
    assert update["usage_metadata"]["model"] == "gpt-4o-mini"
    assert update["usage_metadata"]["provider"] == "rag"
