# NovaEdge Solutions — Security Policy

## Posture
NovaEdge is a remote-first, cloud-native company. We design our systems on the assumption
that the perimeter is "the audit log", not the network. Every action is authenticated,
authorized, and logged.

## Compliance Status
- **SOC 2 Type II**: in progress. Target completion **2026 Q4**. We can share the in-progress
  control documentation under NDA.
- **ISO 27001**: not certified. We do not currently plan to pursue it.
- **HIPAA**: Business Associate Agreement available **only** for Enterprise customers, and
  only after a tailored implementation review.
- **GDPR / PIPEDA**: aligned. Standard DPA available on request.
- **PCI DSS**: not applicable. We do not store cardholder data; Stripe holds all card data.

We will not claim certifications we do not hold. See `objection_handling.md` for how reps
should answer compliance questions.

## Access Control
- **Authentication**: all NovaEdge employees use SSO with mandatory MFA.
- **Authorization**: role-based access (RBAC). Engineering roles do not grant access to
  customer data by default.
- **Customer data access**: limited to a small support engineering rotation. Each access
  produces an audit-log entry with reason.
- **Quarterly access reviews**: every role's permissions are reviewed and pruned.

## Tenant Isolation
- Every row in our primary database carries an `organization_id`.
- All repositories and services accept and enforce an `organization_id` parameter.
- Cross-tenant access raises an internal `PermissionDeniedError` and produces an alert.
- Vector indexes are partitioned by tenant; chunks carry `organization_id` in payload.

## Cryptography
- **In transit**: TLS 1.2+ for all customer-facing endpoints. HSTS enabled.
- **At rest**: AES-256 via the cloud provider's managed encryption (AWS KMS / Google KMS).
- **Secrets**: all customer-supplied secrets (API tokens, service-account JSON) are
  encrypted with a per-tenant key.
- **Password hashing**: bcrypt (cost factor 12).

## Application Security
- Static analysis (ruff + mypy) on every commit.
- Dependency scanning weekly.
- All third-party packages must be either widely-used or vetted by an engineer.
- We follow OWASP ASVS Level 2 controls for web application security.

## Incident Response
- 24/7 on-call rotation for Scale and Enterprise customers.
- A confirmed security incident triggers our incident process:
  1. Page the security on-call.
  2. Open an incident channel.
  3. Contain (revoke credentials, isolate workloads).
  4. Investigate (read audit log; identify scope).
  5. Notify affected customers within 72 hours.
  6. Remediate.
  7. Postmortem within 5 business days.

## Customer-Side Controls
We strongly recommend customers:

- Use SSO for their OnePilot workspace.
- Use API tokens scoped to specific machine workloads, not personal admin accounts.
- Restrict integrations to the **least-scope** OAuth permissions necessary.
- Rotate integration credentials at least annually.

## Vulnerability Disclosure
We accept responsible disclosure reports at `security@novaedge.io`.

- We acknowledge reports within 2 business days.
- We aim to triage within 5 business days.
- We do not pay bug bounties at this time.
- We will publicly credit researchers after a fix is shipped, with their consent.

## Penetration Testing
- Third-party penetration test annually.
- Internal red-team exercises quarterly.
- Customers on Scale or Enterprise can request a redacted penetration-test summary.

## Sub-processors and Region
- See `data_privacy_policy.md` for the sub-processor list and data-region defaults.

## Logging and Monitoring
- Every API call produces a structured log line with `request_id`, `organization_id`,
  `user_id`, route, status, latency.
- AI tool calls produce an audit-log entry with input hash and output hash.
- Anomaly detection alerts on:
  - Unusual cross-tenant access patterns.
  - Sudden spikes in token usage per tenant.
  - Repeated failed authentication.
- Logs are retained for **24 months**.

## What We Do Not Do
- We do not weaken security to close a deal.
- We do not commit to a security control in writing without the Head of Security's approval.
- We do not promise a compliance certification we have not yet achieved.

For privacy specifics, see `data_privacy_policy.md`. For AI-specific guardrails, see
`ai_usage_policy.md`.
