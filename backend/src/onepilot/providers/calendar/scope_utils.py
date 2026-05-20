"""Safe Google OAuth scope checks for Calendar (never logs tokens)."""

from __future__ import annotations

import httpx

from onepilot.core.logging import get_logger

log = get_logger(__name__)

CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"

_REQUIRED_CALENDAR_SCOPES = frozenset({CALENDAR_READONLY_SCOPE, CALENDAR_EVENTS_SCOPE})

_TOKENINFO_URL = "https://www.googleapis.com/oauth2/v1/tokeninfo"


def scopes_from_tokeninfo(access_token: str, *, timeout_seconds: float = 10.0) -> set[str] | None:
    """Return granted scopes for an access token, or None if tokeninfo failed."""
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(
                _TOKENINFO_URL,
                params={"access_token": access_token},
            )
            if response.status_code != 200:
                log.warning("calendar_tokeninfo_failed", status_code=response.status_code)
                return None
            data = response.json()
            raw = str(data.get("scope") or "")
            return {part.strip() for part in raw.split() if part.strip()}
    except httpx.HTTPError as exc:
        log.warning("calendar_tokeninfo_transport_error", error=str(exc))
        return None


def missing_calendar_scopes(granted: set[str] | None) -> list[str]:
    """Return missing required Calendar scope URLs (empty if all present)."""
    if granted is None:
        return []
    missing: list[str] = []
    for scope in sorted(_REQUIRED_CALENDAR_SCOPES):
        if scope not in granted:
            missing.append(scope)
    return missing


def has_calendar_scopes(granted: set[str] | None) -> bool:
    if granted is None:
        return True
    return not missing_calendar_scopes(granted)
