# Google Workspace OAuth Setup (Gmail + Calendar)

OnePilot reuses a **single Google OAuth refresh token** for Gmail and Google Calendar when the token includes the required scopes.

## 1. Enable APIs

In [Google Cloud Console](https://console.cloud.google.com/):

1. Enable **Gmail API**
2. Enable **Google Calendar API**

## 2. OAuth consent screen

- User type: **External** (demo) or **Internal** (Workspace org)
- Add test users for the demo Google account
- Scopes (minimum recommended demo set):
  - `https://www.googleapis.com/auth/gmail.compose`
  - `https://www.googleapis.com/auth/calendar.readonly`
  - `https://www.googleapis.com/auth/calendar.events`
- Optional (only if testing send): `https://www.googleapis.com/auth/gmail.send`

## 3. OAuth client

Create an OAuth client (**Desktop app** recommended):

- Redirect URI: `http://127.0.0.1:8765/`
- Copy **Client ID** and **Client secret** into local `.env` only (never commit)

## 4. Generate refresh token

From `backend/`:

```bash
uv run python scripts/generate_google_workspace_refresh_token.py
```

Default scopes: Gmail compose + Calendar readonly + Calendar events.

Optional flags:

```bash
uv run python scripts/generate_google_workspace_refresh_token.py --include-send
uv run python scripts/generate_google_workspace_refresh_token.py --scopes gmail.compose,calendar.readonly,calendar.events
```

The legacy Gmail-only helper remains at `scripts/generate_gmail_refresh_token.py` but does **not** include Calendar scopes.

## 5. Local `.env` variables

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8765/

GMAIL_PROVIDER_MODE=auto
GMAIL_SEND_ENABLED=false

GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_PROVIDER_MODE=auto
GOOGLE_CALENDAR_CREATE_ENABLED=true
GOOGLE_CALENDAR_DEFAULT_TIMEZONE=Europe/Berlin
```

## 6. Regenerating when adding Calendar scopes

If your existing refresh token was created with **Gmail-only** scopes, Calendar API calls will fail with `mode=unhealthy` and `calendar_status_reason=missing_calendar_scope`.

**After adding Calendar to your project, regenerate the token:**

1. Revoke the app at https://myaccount.google.com/permissions
2. From `backend/`, run:
   ```bash
   uv run python scripts/generate_google_workspace_refresh_token.py
   ```
   Default scopes include Gmail compose + `calendar.readonly` + `calendar.events`.
3. Replace `GOOGLE_REFRESH_TOKEN` in local `.env` (never commit)
4. Verify:
   ```bash
   uv run python scripts/check_google_calendar_status.py
   ```
   Expect `mode: live` and `scope_check: ok`.

## 7. Safety model

| Action | Approval required |
|--------|-------------------|
| Check availability | No |
| Suggest slots | No |
| Create calendar event | **Yes** |

Without OAuth credentials, Calendar runs in **mock mode** for safe demos.

## 8. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/providers
```

Expect `calendar_mode: live` when OAuth is configured, otherwise `mock`.

Diagnostics never expose tokens, refresh tokens, or private event payloads.
