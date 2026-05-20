from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from onepilot.core.logging import get_logger
from onepilot.providers.search.base import SearchProvider

log = get_logger(__name__)


class SerperSearchProvider(SearchProvider):
    """Serper.dev-backed web search provider."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://google.serper.dev/search",
        timeout_seconds: int = 10,
    ) -> None:
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = float(timeout_seconds)

    def search_web(
        self,
        query: str,
        num_results: int = 5,
        *,
        language: str | None = None,
        region: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._api_key:
            return []

        payload: dict[str, Any] = {"q": query, "num": max(1, min(num_results, 20))}
        if language:
            payload["hl"] = language
        if region:
            payload["gl"] = region

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    self._base_url,
                    json=payload,
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException:
            log.warning("serper_search_timeout", query_preview=query[:80])
            return []
        except httpx.HTTPError as exc:
            log.warning("serper_search_http_error", error=str(exc), query_preview=query[:80])
            return []
        except Exception as exc:
            log.warning("serper_search_failed", error=str(exc), query_preview=query[:80])
            return []

        return _normalize_serper_response(data, num_results=num_results)


def _normalize_serper_response(data: Any, *, num_results: int) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []

    organic = data.get("organic")
    if not isinstance(organic, list):
        return []

    results: list[dict[str, Any]] = []
    for index, item in enumerate(organic[:num_results], start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("link") or item.get("url") or "").strip()
        snippet = str(item.get("snippet") or item.get("description") or "").strip()
        if not title and not url:
            continue
        published = item.get("date") or item.get("published_date")
        published_date = str(published).strip() if published else None
        source = _hostname(url) or "web"
        results.append(
            {
                "title": title or url,
                "url": url,
                "snippet": snippet,
                "source": source,
                "published_date": published_date,
                "rank": index,
                "provider": "serper",
            }
        )
    return results


def _hostname(url: str) -> str:
    try:
        host = urlparse(url).netloc
        return host.removeprefix("www.") if host else ""
    except Exception:
        return ""
