"""Server-side Google OAuth token refresh (refresh-token flow only)."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from onepilot.core.logging import get_logger

log = get_logger(__name__)

_TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass(slots=True)
class GoogleAccessToken:
    access_token: str
    expires_at: float
    token_type: str = "Bearer"


class GoogleOAuthClient:
    """Refresh access tokens using a long-lived refresh token."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._client_id = client_id.strip()
        self._client_secret = client_secret.strip()
        self._refresh_token = refresh_token.strip()
        self._timeout = timeout_seconds
        self._cached: GoogleAccessToken | None = None

    def get_access_token(self) -> str:
        token = self._ensure_token()
        return token.access_token

    def _ensure_token(self) -> GoogleAccessToken:
        now = time.time()
        if self._cached and self._cached.expires_at > now + 60:
            return self._cached

        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(_TOKEN_URL, data=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            log.warning("gmail_oauth_refresh_failed", error=str(exc))
            raise

        access = str(data.get("access_token") or "").strip()
        if not access:
            raise ValueError("OAuth response missing access_token")

        expires_in = int(data.get("expires_in") or 3600)
        self._cached = GoogleAccessToken(
            access_token=access,
            expires_at=now + expires_in,
            token_type=str(data.get("token_type") or "Bearer"),
        )
        return self._cached
