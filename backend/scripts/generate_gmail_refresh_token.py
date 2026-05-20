#!/usr/bin/env python3
"""Developer-only helper: obtain a Google OAuth refresh token for Gmail (local .env).

Security:
- Does not write tokens to disk.
- Does not log client secrets or full refresh tokens.
- Copy the masked refresh token hint into your local .env manually.

Usage (from repo root or backend/):
  cd backend
  set GOOGLE_CLIENT_ID=... and GOOGLE_CLIENT_SECRET=...  (or use project-root .env)
  uv run python scripts/generate_gmail_refresh_token.py
  uv run python scripts/generate_gmail_refresh_token.py --include-send   # optional gmail.send scope

Preferred Google Cloud OAuth client type: **Desktop app** (loopback redirect).

For Gmail + Calendar scopes, use:
  uv run python scripts/generate_google_workspace_refresh_token.py
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

# Load project-root .env without printing values
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent


def _load_dotenv() -> None:
    for path in (_PROJECT_ROOT / ".env", _BACKEND_ROOT / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _mask_token(token: str) -> str:
    token = token.strip()
    if len(token) <= 12:
        return "****"
    return f"{token[:6]}...{token[-4:]}"


SCOPE_COMPOSE = "https://www.googleapis.com/auth/gmail.compose"
SCOPE_SEND = "https://www.googleapis.com/auth/gmail.send"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_REDIRECT = "http://127.0.0.1:8765/"


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code: str | None = None
    error: str | None = None

    def log_message(self, format: str, *args: object) -> None:
        return  # silence request logs (no codes in server logs)

    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        if "error" in query:
            _OAuthCallbackHandler.error = query["error"][0]
        elif "code" in query:
            _OAuthCallbackHandler.auth_code = query["code"][0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if _OAuthCallbackHandler.auth_code:
            body = "<h1>Authorization received</h1><p>You can close this tab and return to the terminal.</p>"
        else:
            body = "<h1>Authorization failed</h1><p>Check the terminal for details.</p>"
        self.wfile.write(body.encode())


def _exchange_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected token response")
        return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Gmail OAuth refresh token (local dev only).")
    parser.add_argument(
        "--include-send",
        action="store_true",
        help="Also request gmail.send scope (only if you plan to test GMAIL_SEND_ENABLED=true).",
    )
    parser.add_argument(
        "--redirect-uri",
        default=os.environ.get("GOOGLE_REDIRECT_URI", DEFAULT_REDIRECT),
        help=f"OAuth redirect URI (default: {DEFAULT_REDIRECT}). Must match Google Cloud client.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    args = parser.parse_args()

    _load_dotenv()

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print(
            "ERROR: Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your local .env first.\n"
            "See docs/gmail_oauth_setup.md for Google Cloud Console steps.",
            file=sys.stderr,
        )
        return 1

    scopes = [SCOPE_COMPOSE]
    if args.include_send:
        scopes.append(SCOPE_SEND)

    redirect_uri = args.redirect_uri.strip() or DEFAULT_REDIRECT
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
    }
    authorization_url = f"{AUTH_URL}?{urlencode(params)}"

    print("\n=== OnePilot Gmail OAuth setup (developer only) ===\n")
    print("1. Ensure Gmail API is enabled and OAuth consent screen is configured.")
    print("2. OAuth client type: Desktop app (recommended) with redirect URI:")
    print(f"   {redirect_uri}")
    print("3. Open this URL in your browser (same Google account as your demo inbox):\n")
    print(authorization_url)
    print()

    if not args.no_browser:
        try:
            webbrowser.open(authorization_url)
        except Exception:
            pass

    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None

    port = urlparse(redirect_uri).port or 8765
    server = HTTPServer(("127.0.0.1", port), _OAuthCallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    print(f"Waiting for callback on 127.0.0.1:{port} ... (or paste the authorization code below)\n")

    thread.join(timeout=120.0)
    code = _OAuthCallbackHandler.auth_code
    if _OAuthCallbackHandler.error:
        print(f"ERROR: OAuth returned error={_OAuthCallbackHandler.error}", file=sys.stderr)
        return 1

    if not code:
        print("Paste the authorization code (or full redirect URL) and press Enter:")
        raw = input().strip()
        if "code=" in raw:
            code = parse_qs(urlparse(raw).query).get("code", [None])[0]
        else:
            code = raw

    if not code:
        print("ERROR: No authorization code provided.", file=sys.stderr)
        return 1

    try:
        token_data = _exchange_code(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
    except httpx.HTTPError as exc:
        print(f"ERROR: Token exchange failed ({exc}).", file=sys.stderr)
        print("Check redirect URI matches your Google Cloud OAuth client.", file=sys.stderr)
        return 1

    refresh = str(token_data.get("refresh_token") or "").strip()
    if not refresh:
        print(
            "WARNING: No refresh_token in response. Revoke app access at "
            "https://myaccount.google.com/permissions and run again with prompt=consent.",
            file=sys.stderr,
        )
        return 1

    print("\n=== SUCCESS — add to your local .env only (never commit) ===\n")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print("GOOGLE_CLIENT_SECRET=<keep existing value in .env>")
    print(f"GOOGLE_REFRESH_TOKEN masked preview: {_mask_token(refresh)}")
    print("GOOGLE_REDIRECT_URI=" + redirect_uri)
    print("GMAIL_PROVIDER_MODE=auto")
    print("GMAIL_SEND_ENABLED=false")
    print()
    reveal = input("Print full GOOGLE_REFRESH_TOKEN to this terminal once? [y/N]: ").strip().lower()
    if reveal == "y":
        print("\n⚠️  Copy the line below into your local .env, then clear scrollback. Do not commit.\n")
        print(f"GOOGLE_REFRESH_TOKEN={refresh}\n")
    else:
        print("\nSkipped full token print. Re-run and answer 'y' when ready to copy into .env.\n")
    print("After updating .env:")
    print("  docker compose down && docker compose up -d --build")
    print("  curl http://localhost:8000/health  # gmail_mode should be live")
    print("  curl http://localhost:8000/providers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
