# Private live-Google setup (operator)

Sanitized runbook for a **private** recruiter/demo host with a dedicated Google
account. This is **not** the public demo and must never share that host or its
environment.

Do **not** commit credentials, refresh tokens, client secrets, cookies, or raw
env values. This file lists **variable names only**.

Related local helpers (names only): [gmail_oauth_setup.md](../gmail_oauth_setup.md),
[google_workspace_oauth_setup.md](../google_workspace_oauth_setup.md).

---

## What this track is

| Track | Anonymous `/demo/start` | Gmail / Calendar | Access |
|-------|-------------------------|------------------|--------|
| Public demo | Enabled | Mock / send-disabled / create-disabled | Anyone with the public URL |
| **Private live-Google** | **Disabled** | **Live Gmail + live Calendar** | Authenticated users in one allowlisted org |
| Local `auto` | Off by default | Live if OAuth is present, else mock | Developer machine |

The public production host stays on `GMAIL_PROVIDER_MODE=mock` and
`GOOGLE_CALENDAR_PROVIDER_MODE=mock`. Do not change public Railway/Vercel env.

The legacy pointer `deployment/live-google-demo` is not the implementation
branch. Product code lives on `main` (this document ships via a `main` PR).

---

## 1. Dedicated Google demo account

1. Create or reuse a **dedicated** Google account for this private demo only.
   Do not connect a personal or customer mailbox.
2. Keep the account under operator control. Recruiters should not receive the
   Google password.
3. Use this account only on the **private** backend host.

---

## 2. Google Cloud project and APIs

In [Google Cloud Console](https://console.cloud.google.com/):

1. Create or select a project used only for this private demo.
2. **APIs & Services → Library** — enable:
   - **Gmail API**
   - **Google Calendar API**
3. Confirm both APIs show as enabled before generating a refresh token.

---

## 3. OAuth consent

1. **APIs & Services → OAuth consent screen**.
2. User type: **External** (or Internal if the account is Workspace-only).
3. App name, support email, and developer contact — operator-owned values only.
4. Add scopes (minimum private-demo set):
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/calendar.events`
5. Optional, only if you will later set `GMAIL_SEND_ENABLED=true`:
   - `https://www.googleapis.com/auth/gmail.send`
6. While the app is in **Testing**, add the dedicated Google demo account as a
   test user.
7. Publishing the consent screen to production is not required for a private
   test-user demo.

---

## 4. OAuth client and redirect URI

**Recommended: Desktop app** (refresh-token helper on an operator machine).

1. **Credentials → Create credentials → OAuth client ID**.
2. Application type: **Desktop app**.
3. Redirect URI used by the helper scripts:
   - `http://127.0.0.1:8765/`
4. Desktop clients typically allow loopback. If the Console asks for an
   authorized redirect URI, add the loopback URI above.
5. Copy the client ID and client secret into the **private host secret store
   only** — never into git.

**Web application** is only needed if you intentionally use a web redirect
flow. Then set the same URI in `GOOGLE_REDIRECT_URI`. The running OnePilot
API does **not** expose a public Google OAuth callback for end users. Tokens
are generated offline and stored as server env.

Generate the refresh token on a trusted operator machine (from `backend/`):

```bash
uv run python scripts/generate_google_workspace_refresh_token.py
```

Default scopes: Gmail compose + Calendar readonly + Calendar events.

- The script does not write tokens to disk.
- It shows a masked preview. Paste the refresh token into the host secret
  store, then clear the terminal scrollback.
- The Gmail-only helper `scripts/generate_gmail_refresh_token.py` does **not**
  include Calendar scopes. Prefer the workspace helper for this track.

Revoke access later at [Google Account permissions](https://myaccount.google.com/permissions).

---

## 5. Required environment variable names

Set these on the **private** backend host only. Values stay in Railway (or
equivalent) secrets — never in the repo, PR, or Cloud reports.

### Track and safety

| Variable | Private-track value | Notes |
|----------|---------------------|--------|
| `APP_ENV` | `production` | Existing production startup checks apply |
| `DEV_AUTH_ENABLED` | `false` | Required; startup fails if true with this track |
| `PUBLIC_DEMO_ENABLED` | `false` | **Required.** Anonymous `/demo/start` must stay off |
| `PRIVATE_LIVE_GOOGLE_ENABLED` | `true` | Selects the private live-Google track |
| `PRIVATE_LIVE_GOOGLE_ORG_ID` | dedicated org id | Only this org may use live Gmail/Calendar |
| `GMAIL_PROVIDER_MODE` | `live` | `auto` is also accepted if OAuth is present; `mock` is rejected |
| `GOOGLE_CALENDAR_PROVIDER_MODE` | `live` | Same as Gmail |
| `GMAIL_SEND_ENABLED` | `false` | Keep false unless you explicitly test send |
| `GOOGLE_CALENDAR_CREATE_ENABLED` | `true` | Writes still require human approval |

### Google OAuth (names only)

| Variable | Required |
|----------|----------|
| `GOOGLE_CLIENT_ID` | Yes |
| `GOOGLE_CLIENT_SECRET` | Yes |
| `GOOGLE_REFRESH_TOKEN` | Yes |
| `GOOGLE_REDIRECT_URI` | No (default loopback for the helper) |

### Calendar extras (optional)

| Variable | Typical private-demo value |
|----------|----------------------------|
| `GOOGLE_CALENDAR_ID` | `primary` |
| `GOOGLE_CALENDAR_IDS` | empty unless aggregating calendars |
| `GOOGLE_CALENDAR_DEFAULT_TIMEZONE` | operator timezone, e.g. `Europe/Berlin` |

### Host / auth (existing names)

| Variable | Notes |
|----------|--------|
| `DATABASE_URL` | Private Postgres — do not reuse the public-demo database |
| `JWT_SECRET` | New strong secret, ≥ 32 characters. Do not copy the public host secret |
| `CORS_ORIGINS` | Private frontend origin only, no wildcards |
| `REDIS_URL` | Strongly recommended |
| `OPENAI_API_KEY` | Optional; do not change the public host model |
| `OPENAI_MODEL` | Leave the **public** host on `gpt-5-nano`. Private host may keep its own model name |

Startup **fails closed** when:

- `PRIVATE_LIVE_GOOGLE_ENABLED=true` and OAuth fields are missing
- `GMAIL_PROVIDER_MODE=live` or `GOOGLE_CALENDAR_PROVIDER_MODE=live` without OAuth
- both `PUBLIC_DEMO_ENABLED` and `PRIVATE_LIVE_GOOGLE_ENABLED` are true
- `PRIVATE_LIVE_GOOGLE_ORG_ID` is empty while the private track is enabled
- `DEV_AUTH_ENABLED=true` while the private track is enabled

---

## 6. Where to configure (Railway / Vercel)

| Surface | Location | What to set |
|---------|----------|-------------|
| Private API | **New** Railway (or equivalent) service/project — **not** the public production service | Backend env table above |
| Private frontend | **New** Vercel project — **not** `one-pilot-ai.vercel.app` | `NEXT_PUBLIC_API_URL` pointing at the private API |
| Private CORS | Private API env | `CORS_ORIGINS` = the private Vercel URL |
| Public demo | Existing Railway + Vercel | **Do not change** |

Do not fast-forward `deployment/public-demo` or `deployment/live-google-demo`
as part of this setup. After the product PR is on `main`, the operator
chooses a later, explicit deploy of a **separate** private host.

---

## 7. Safe provider-mode values

| Host | `GMAIL_PROVIDER_MODE` | `GOOGLE_CALENDAR_PROVIDER_MODE` | `GMAIL_SEND_ENABLED` | `PUBLIC_DEMO_ENABLED` | `PRIVATE_LIVE_GOOGLE_ENABLED` |
|------|------------------------|----------------------------------|----------------------|-----------------------|-------------------------------|
| Public demo | `mock` | `mock` | `false` | `true` | `false` |
| Private live-Google | `live` | `live` | `false` | `false` | `true` |
| Local without OAuth | `auto` or `mock` | `auto` or `mock` | `false` | `false` | `false` |

`auto` without credentials stays mock (local/dev convenience).
`live` without credentials refuses to start.

---

## 8. Auth model on the private host

The current JWT + RBAC model is sufficient. Do **not** enable
`PUBLIC_DEMO_ENABLED`.

1. Seed or create one owner user in `PRIVATE_LIVE_GOOGLE_ORG_ID`.
2. Share login credentials privately with intended reviewers only.
3. `/demo/start` returns 403 on this host.
4. Other organizations on the same host receive mock Gmail/Calendar and cannot
   read or write the dedicated Google account.
5. Gmail send/draft provider execution and Calendar create/update still require
   Owner/Admin approval. Calendar availability/list/slots are read-only and
   still require an authenticated principal in the allowlisted org.

---

## 9. Validation checklist (operator)

After env is set on the **private** host only:

1. `GET /health` — `status=ok`, `demo_track=private_live_google`,
   `public_demo_enabled=false`, `private_live_google_enabled=true`,
   `gmail_mode=live`, `calendar_mode=live`, `gmail_send_enabled=false`.
2. `GET /providers` — Gmail and Google Calendar `mode=live`,
   `requires_approval` / `requires_approval_for_create` true, no tokens in the
   payload.
3. `POST /demo/start` — HTTP 403.
4. Login with the dedicated owner (not Try the demo).
5. Calendar availability / upcoming meetings return live busy/free data (no
   private event titles in API responses).
6. “Draft and send” or schedule-meeting prompts create an **ApprovalRequest**.
   Nothing hits Gmail send or Calendar insert until Owner/Admin approves.
7. A second registered org cannot see the first org’s approvals or live Google
   data.
8. Public demo URL is unchanged: Gmail mock, Calendar mock, speech disabled,
   `gpt-5-nano` on the public host.

Never paste health JSON that might include connection strings into chat or git.

---

## 10. Rollback

If the private host misbehaves:

1. Set `PRIVATE_LIVE_GOOGLE_ENABLED=false`.
2. Set `GMAIL_PROVIDER_MODE=mock` and `GOOGLE_CALENDAR_PROVIDER_MODE=mock`.
3. Remove `GOOGLE_REFRESH_TOKEN` (and client secret) from the private host.
4. Restart the private API. Startup will no longer select live Google.
5. Leave the **public** Railway/Vercel env untouched.
6. Optionally revoke the OAuth grant at Google Account permissions.
7. Do not move `deployment/public-demo` or `deployment/live-google-demo`
   unless a later task explicitly authorizes that branch.
