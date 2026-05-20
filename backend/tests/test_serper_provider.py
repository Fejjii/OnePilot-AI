"""Tests for Serper web search provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from onepilot.providers.search.serper_provider import SerperSearchProvider


def test_serper_success_normalizes_results() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "organic": [
            {
                "title": "SMB Automation Trends 2026",
                "link": "https://example.com/smb-trends",
                "snippet": "Small businesses adopt workflow automation.",
                "date": "2026-03-01",
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_response

    with patch("onepilot.providers.search.serper_provider.httpx.Client", return_value=mock_client):
        provider = SerperSearchProvider(api_key="test-key")
        results = provider.search_web("SMB automation trends", 3)

    assert len(results) == 1
    row = results[0]
    assert row["title"] == "SMB Automation Trends 2026"
    assert row["url"] == "https://example.com/smb-trends"
    assert row["snippet"].startswith("Small businesses")
    assert row["provider"] == "serper"
    assert row["rank"] == 1


def test_serper_missing_api_key_returns_empty() -> None:
    provider = SerperSearchProvider(api_key="")
    assert provider.search_web("test query", 5) == []


def test_serper_timeout_returns_empty() -> None:
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.side_effect = httpx.TimeoutException("timeout")

    with patch("onepilot.providers.search.serper_provider.httpx.Client", return_value=mock_client):
        provider = SerperSearchProvider(api_key="test-key")
        results = provider.search_web("timeout query", 5)

    assert results == []


def test_serper_http_error_returns_empty() -> None:
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.side_effect = httpx.HTTPError("boom")

    with patch("onepilot.providers.search.serper_provider.httpx.Client", return_value=mock_client):
        provider = SerperSearchProvider(api_key="test-key")
        results = provider.search_web("error query", 5)

    assert results == []


def test_serper_malformed_response_returns_empty() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = "not-json-shape"

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_response

    with patch("onepilot.providers.search.serper_provider.httpx.Client", return_value=mock_client):
        provider = SerperSearchProvider(api_key="test-key")
        results = provider.search_web("bad payload", 5)

    assert results == []
