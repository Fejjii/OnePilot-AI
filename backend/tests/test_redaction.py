"""Tests for secret redaction (OP-019)."""

from onepilot.security.redaction import redact_sensitive


def test_redacts_legacy_sk_keys() -> None:
    text = "key=sk-abcdefghijklmnopqrstuvwxyz123456"
    assert "[API_KEY_REDACTED]" in redact_sensitive(text)
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in redact_sensitive(text)


def test_redacts_sk_proj_keys() -> None:
    text = "OPENAI_API_KEY=sk-proj-abc_DEF-1234567890abcdefghijklmnop"
    assert "[API_KEY_REDACTED]" in redact_sensitive(text)
    assert "sk-proj-" not in redact_sensitive(text)
