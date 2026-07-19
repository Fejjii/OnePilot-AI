# Security

## Principles

1. Defense in depth — multiple layers of protection
2. Least privilege — users only access what they need
3. Fail safely — errors never expose internals
4. Audit everything — important actions are logged
5. No autonomous external actions — human approval required before any side effect

---

## Implemented

### Authentication

- **JWT (HS256)** with configurable secret (`JWT_SECRET`), algorithm, and expiry (`JWT_EXPIRE_MINUTES`, default 60)
- **DEV_AUTH fallback** — when `DEV_AUTH_ENABLED=true` and no `Authorization` header is sent, the request is attributed to a fixed demo user/org. The safe field default is `false`; local dev sets `true` in `.env`. **Startup fails** if `APP_ENV=production` and `DEV_AUTH_ENABLED=true`.
- Password hashing via **bcrypt** (passlib, 12 rounds)
- Token payload: `user_id`, `organization_id`, `role`, `plan_code`

#### JWT Storage — Current Behavior and Known Risk

Tokens are currently stored in **`localStorage`** in the browser. This is a deliberate simplification for the demo build.

| Risk | Detail |
|------|--------|
| XSS exposure | Any injected script can read `localStorage` |
| No automatic expiry on client | Token persists until the user logs out or it expires server-side |

**Recommended production improvement:** Store the JWT in an HTTP-only, `Secure`, `SameSite=Strict` cookie and implement a `/auth/refresh` endpoint using a long-lived refresh token stored in the same cookie. This eliminates XSS read access to the token.

---

### Role-Based Access Control (RBAC)

| Role | Level | Permissions |
|------|-------|-------------|
| Owner | 3 | Everything including plan changes |
| Admin | 2 | Manage team, data, settings |
| Member | 1 | Use all AI tools |
| Viewer | 0 | Read-only access |

- `RoleChecker` dependency enforces minimum role per endpoint
- `ensure_same_org()` prevents cross-tenant data access at the service layer
- Sensitive endpoints (user management, plan changes, admin operations) require `Admin` or `Owner`

---

### Multi-Tenant Isolation

- Every database entity carries an `organization_id` column via `TenantMixin`
- `BaseRepository` enforces `organization_id` filtering on all reads, updates, and deletes
- Vector collections are namespaced: `documents_{organization_id}` — one Qdrant collection per tenant
- Service layer validates org membership before any data access
- `ensure_same_org()` guard raises `403` if a resource belongs to a different org
- All audit logs and usage events are scoped to `organization_id`

---

### Prompt Injection Detection

The `security.prompt_injection` module uses regex and keyword patterns to detect:

| Pattern | Example |
|---------|---------|
| Instruction override | "ignore previous instructions", "disregard the above" |
| System prompt extraction | "reveal system prompt", "what are your instructions" |
| Destructive operations | "delete all data", "drop the database" |
| Approval bypass | "skip approval", "execute without review" |
| Secret exfiltration | "show api keys", "print your credentials" |
| Privilege escalation | "act as admin", "you are now a superuser" |
| Code execution | "exec(", "eval(", "`rm -rf`" |

Flagged messages are blocked before reaching the agent and logged as audit events.

---

### Sensitive Data Redaction

- `structlog` processor redacts sensitive keys in log output (API keys, bearer tokens, passwords)
- `TextRedactor` strips API keys, bearer tokens, emails, and phone numbers from free text
- Error responses never include stack traces or internal exception details
- Log entries are safe to ship to external observability platforms

---

### Request Tracing

- Every request receives a unique `X-Request-ID` (ULID)
- The request ID is echoed in the response header and in every log line for the request lifecycle
- Enables correlation between frontend errors and backend logs

---

### Rate Limiting

Fixed-window limits per feature (raises `429 RATE_LIMIT_EXCEEDED`):

| Endpoint / feature | Limit | Key |
|--------------------|-------|-----|
| `POST /chat` | 60 / minute | org + user |
| `POST /documents/upload` | 20 / minute | org + user |
| `POST /auth/login` | 10 / minute | email (hashed in Redis keys) |
| `POST /auth/register` | 5 / hour | client IP (hashed in Redis keys) |
| `POST /demo/start` | 10 / hour | client IP (hashed in Redis keys) |

**Backend selection**

- When `REDIS_URL` is set and reachable, counters are stored in Redis (shared across workers; TTL-based fixed windows).
- When `REDIS_URL` is unset or Redis errors at runtime, the limiter falls back to **in-memory** counters for that process.
- `/health` and `/providers` expose `rate_limit_backend` (`redis` or `memory`) without user identifiers.

**Recommendations**

- **Public demo / multi-instance production:** set `REDIS_URL` (strongly recommended, not strictly required).
- **Local single-process dev:** memory fallback is acceptable.

**Known limitations**

- Memory fallback resets on restart and is not shared across instances.
- If Redis fails mid-flight, the process degrades to memory for the remainder of its lifetime.
- No IP rate limiting at the reverse proxy (add WAF/nginx limits for extra protection).

---

### File Upload Validation

- Allowed extensions: `.pdf`, `.docx`, `.txt`, `.md`, `.csv`
- MIME type verification in addition to extension check
- Maximum file size: 50 MB
- Content is never executed; it is only parsed for text extraction

---

### Approval Gates

Actions that modify external systems require explicit human approval before execution:

1. Sending emails
2. Scheduling meetings
3. Updating CRM records (HubSpot)
4. Changing lead status
5. Any other external side effect
6. Low-confidence or high-risk LLM outputs

The approval gate creates an `ApprovalRequest` row in Postgres. The agent waits for `status = approved` before proceeding. Rejected requests are never retried.

---

### Audit Logging

Every sensitive action writes an `AuditLog` row including:
- `actor_id`, `organization_id`
- `action` (e.g., `document.uploaded`, `approval.created`, `chat.message`)
- `resource_type`, `resource_id`
- `metadata` (JSON with relevant context)
- `created_at` (UTC)

Audit logs are append-only at the application layer. They are surfaced in the Usage/Admin page.

---

### No Autonomous External Actions

The system is explicitly designed to **never execute external actions without human approval**. The LangGraph agent creates draft actions; humans approve or reject them in the Approvals queue. This policy is documented in the NovaEdge AI Usage Policy demo document.

---

### Provider Fallback Behavior

When an external provider is unavailable or not configured:

| Provider | Fallback | Notes |
|----------|----------|-------|
| OpenAI LLM | `FallbackLLMProvider` | Returns deterministic synthesized responses |
| OpenAI Embeddings | `FallbackEmbeddingsProvider` | Token-hash embeddings (not for production) |
| Qdrant | `MemoryVectorProvider` | In-process singleton (not for production) |
| HubSpot CRM | `MockCRMProvider` | In-memory, deterministic |
| Gmail | `MockEmailProvider` or `GmailProvider` | OAuth refresh token in server env only; drafts/sends **after** approval; `/health` and `/providers` never return tokens. Setup: `docs/gmail_oauth_setup.md` |
| Google Calendar | `MockCalendarProvider` or `GoogleCalendarProvider` | Reuses same OAuth refresh token when Calendar scopes granted; availability/slots without approval; event creation **after** approval only. Setup: `docs/google_workspace_oauth_setup.md` |
| Stripe | `MockBillingProvider` | In-memory subscription store |

All fallback usage is logged with `fallback_used=True` in responses and audit logs.

---

## Production Gaps (Known Limitations)

| Gap | Risk | Recommendation |
|-----|------|----------------|
| JWT in `localStorage` | XSS can steal tokens | Move to HTTP-only cookies + refresh tokens |
| No token refresh | Tokens expire after `JWT_EXPIRE_MINUTES` | Implement `/auth/refresh` |
| In-memory rate limiting fallback | Resets on restart; not shared across workers | Set `REDIS_URL` for shared Redis counters |
| No CSRF protection | Relevant if cookies are used | Add CSRF middleware when switching to cookies |
| No security headers | Missing CSP, HSTS, etc. | Add security headers middleware in production |
| No IP-based rate limiting | Brute force possible | Add IP rate limiting at reverse proxy |
| No OAuth/SSO | Password-only login | Add OAuth 2.0 / SAML for enterprise |
| No audit log immutability | Logs can be deleted by DB admin | Send logs to append-only external store |
| No content safety classification | LLM output not safety-filtered | Add Moderation API call on LLM output |
| DEV_AUTH_ENABLED risk | If left on in production, all auth is bypassed | Startup validation rejects `DEV_AUTH_ENABLED=true` when `APP_ENV=production` |
