# Safety & Privacy

How OnePilot AI keeps humans in control and keeps tenant data isolated — including on the public demo.

## Human-in-the-loop (HITL)

External side effects never run autonomously. When the agent proposes a gated action (for example Gmail draft/send, calendar event creation, CRM update):

1. An **ApprovalRequest** is created with the proposed payload and risk level.
2. The action appears in the **Approvals** queue and as a pending banner in AI Workspace.
3. An **Owner/Admin** approves or rejects. Rejected actions are not auto-retried.
4. The decision and execution metadata are written to the **audit log**.

Email **draft text** can be generated in-app without approval. **Gmail provider actions** and **calendar event creation** require approval. Gmail **send** is additionally gated by `GMAIL_SEND_ENABLED` (default `false`).

## Public demo safeguards

| Control | Behavior |
|---------|----------|
| Entry | **Try the demo** → short-lived JWT; no credentials displayed |
| Gmail | `GMAIL_PROVIDER_MODE=mock` — simulated only |
| Calendar | `GOOGLE_CALENDAR_PROVIDER_MODE=mock` — simulated only |
| Send | `GMAIL_SEND_ENABLED=false` |
| Auth bypass | `DEV_AUTH_ENABLED=false` in production |
| Demo rate limit | `POST /demo/start` limited per IP |
| Agent memory | Disabled on the shared-demo tenant (`shared_demo_tenant`) |
| Demo start | Clears user/agent memories for the demo principal |

Reviewers share one seeded demo organization. Isolation between private tenants remains repository-enforced; shared-demo memory controls prevent cross-reviewer memory leakage on that shared org.

## Multi-tenant isolation

- Every tenant-scoped row carries `organization_id`.
- Repositories filter by organization on read/update/delete.
- Vector collections are namespaced per organization (`documents_{organization_id}`).
- Cross-org access returns `403` via `ensure_same_org()`.

## Memory privacy

| Scope | Behavior |
|-------|----------|
| User / organization memory | CRUD API + UI; tenant-scoped |
| Agent memory | Recalled before generation; may persist explicit durable facts |
| Secrets | Persist path rejects secret-like content |
| Shared public demo | Agent memory **disabled**; memories cleared on `/demo/start` |

## Other guardrails

- JWT + RBAC (Owner / Admin / Member / Viewer)
- Prompt-injection detection before agent execution
- Sensitive-data redaction in logs
- Rate limiting (Redis when available; in-memory fallback)
- No API keys in the frontend bundle — model names only via `/runtime/config`
- Calendar responses expose busy/free style availability, not private event titles

## Known privacy trade-offs (honest)

- JWT is stored in browser **`localStorage`** (XSS risk). Production hardening should move to HTTP-only cookies + refresh tokens.
- Public demo reviewers share one org dataset (NovaEdge seed). Do not put personal or customer PII into the shared demo.
- Uploaded original files are processed then discarded; chunks live in Postgres. There is no object-storage retention layer yet.

## Related docs

- [security.md](security.md) — full security model
- [capabilities.md](capabilities.md) — what is live vs mocked
- [demo_script.md](demo_script.md) — how to demonstrate these controls
