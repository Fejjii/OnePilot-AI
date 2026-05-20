# Gmail OAuth setup (local live demo)

Link **one** Gmail account to OnePilot for approval-gated **draft creation**. Sending stays off unless you explicitly enable it.

## Required environment variables (local `.env` only)

| Variable | Required | Notes |
|----------|----------|--------|
| `GOOGLE_CLIENT_ID` | Yes | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | Yes | Long-lived refresh token for your demo inbox |
| `GMAIL_PROVIDER_MODE` | No | Default `auto` (live when OAuth set, else mock) |
| `GMAIL_SEND_ENABLED` | No | Default `false` — **keep false** for recommended demo |
| `GOOGLE_REDIRECT_URI` | No | Default `http://127.0.0.1:8765/` for the helper script |

Never commit `.env`. `.env.example` contains placeholders only.

---

## Google Cloud Console

### 1. Project and Gmail API

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project (e.g. `onepilot-demo`).
3. **APIs & Services → Library** → enable **Gmail API**.

### 2. OAuth consent screen

1. **APIs & Services → OAuth consent screen**.
2. User type: **External** (or Internal if Workspace-only).
3. Add app name, support email, developer contact.
4. **Scopes** → add:
   - `https://www.googleapis.com/auth/gmail.compose` (required)
   - `https://www.googleapis.com/auth/gmail.send` (only if you will test send with `GMAIL_SEND_ENABLED=true`)
5. **Test users**: add your Gmail address while app is in **Testing**.

### 3. OAuth client (recommended: Desktop app)

**Preferred for local refresh token generation:**

1. **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Desktop app**.
3. Name: `OnePilot Local Dev`.
4. Note the **Client ID** and **Client secret**.

**Redirect URI for the helper script:**

- Add authorized redirect URI: `http://127.0.0.1:8765/`  
  (Desktop clients often allow loopback; if the Console does not show redirect URIs, the Desktop type uses loopback by default.)

**Alternative: Web application** (only if you use a web redirect flow):

- Authorized redirect URI: `http://127.0.0.1:8765/` or your documented callback.
- Use the same URI in `GOOGLE_REDIRECT_URI`.

### 4. Copy credentials to local `.env`

In the **project root** `.env` (used by Docker Compose):

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REFRESH_TOKEN=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8765/
GMAIL_PROVIDER_MODE=auto
GMAIL_SEND_ENABLED=false
```

---

## Generate refresh token (developer machine)

From `backend/`:

```bash
uv run python scripts/generate_gmail_refresh_token.py
```

- Opens the Google authorization URL (or print and open manually with `--no-browser`).
- Uses scope `gmail.compose` only by default.
- For send testing: `uv run python scripts/generate_gmail_refresh_token.py --include-send`  
  (only if you will set `GMAIL_SEND_ENABLED=true` later).

The script:

- Does **not** write tokens to disk.
- Shows a **masked** refresh token preview.
- Optionally prints the full refresh token once if you confirm at the prompt (copy into `.env`, then clear terminal history).

---

## Start stack and verify

```bash
docker compose down
docker compose up -d --build
docker compose run --rm migrate
docker compose run --rm seed
```

### Health

```bash
curl http://localhost:8000/health
```

Expect (when OAuth is complete):

- `providers.gmail_configured`: `true`
- `providers.gmail_mode`: `live`
- `providers.gmail_send_enabled`: `false`

### Providers

```bash
curl http://localhost:8000/providers
```

Find **Gmail**:

- `configured`: `true`
- `mode`: `live`
- `details.capability_create_draft`: `true`
- `details.capability_send_email`: `false`
- `details.requires_approval`: `true`

No tokens appear in these responses.

---

## App demo flow (draft after approval)

### 1. Draft only (no Gmail)

**AI Workspace:**

> Draft an email to a high priority lead about NovaEdge automation services.

Expected: email text in chat; **no** approval; **no** Gmail API call.

### 2. Draft + send intent (approval, no send)

> Draft and send an email to a high priority lead about NovaEdge automation services.

Expected: approval created; **no** Gmail until you approve.

### 3. Approve

1. Open **Approvals** → select the request → **Approve**.
2. Expected: Gmail **draft** in your linked inbox; execution status shows `draft_id`; audit event `gmail.draft_created`.
3. With `GMAIL_SEND_ENABLED=false`, message is **not** sent.

---

## Optional: test real send (explicit only)

1. Regenerate token with `--include-send` or add `gmail.send` scope in Console.
2. Set `GMAIL_SEND_ENABLED=true` in local `.env` only.
3. Rebuild/restart backend.
4. Use a **test recipient you control**; still requires approval.
5. After testing, set `GMAIL_SEND_ENABLED=false` again.

---

## Security notes

- Refresh tokens and client secrets live **only** in server env (Docker `.env`, not frontend).
- All Gmail I/O runs **after** human approval.
- Revoke access anytime: [Google Account permissions](https://myaccount.google.com/permissions).

See also `docs/security.md` and `docs/manual_test_checklist.md`.
