# NovaEdge Solutions — Escalation Policy

This policy defines how NovaEdge classifies, routes, and resolves customer issues. It applies
to both human-handled and AI-handled tickets.

## Severity Levels
| Severity | Definition                                                        | Initial Response SLA                  | Workaround SLA |
|----------|-------------------------------------------------------------------|---------------------------------------|----------------|
| **P1**   | Service down for all users in a workspace, or data integrity at risk. | 15 minutes (Scale/Enterprise), 1h (Growth), 4h (Essentials). | 4 hours        |
| **P2**   | Major feature degraded (RAG empty, integration broken).            | 1h (Scale/Enterprise), 4h (Growth), 1 business day (Essentials). | 1 business day |
| **P3**   | Minor issue, partial degradation, single user affected.            | 1 business day                        | 5 business days |
| **P4**   | Question, feature request, configuration help.                     | 2 business days                       | n/a            |

Enterprise customers may negotiate 24/7 coverage; default is North America business hours.

## What the AI Agent Must Escalate
The AI support agent is **not allowed to resolve**:

- Refund or billing-credit requests.
- Complaints about staff or product quality.
- Legal notices, regulatory inquiries, GDPR / PIPEDA data-subject requests.
- Anything tagged P1 or P2.
- Anything addressed to executives (`founder@`, `ceo@`, `legal@`).
- Anything where the customer has explicitly asked to speak to a human.

In all of those cases, the AI must:

1. Acknowledge the message politely.
2. Open a ticket and assign it to the right queue (`billing`, `legal`, `cs-lead`, `oncall`).
3. Stop replying further until a human takes over.

See `ai_usage_policy.md` for the full set of guardrails.

## Routing
| Issue type             | Primary owner          | Backup                |
|------------------------|------------------------|-----------------------|
| Billing                | Finance team           | Head of CS            |
| Legal / privacy        | `legal@novaedge.io`    | CEO                   |
| Security incident      | Security on-call       | CTO                   |
| Product incident       | Engineering on-call    | Head of Engineering   |
| Integration outage     | Integrations team      | Engineering on-call   |
| Account questions      | Customer Success       | AE for the account    |
| Renewal escalations    | Customer Success       | Head of Revenue       |

## Communication During Incidents
- For P1: open a dedicated incident channel (`#inc-<workspace>-<date>`), invite the customer
  champion, and provide updates **every 30 minutes** until resolved.
- For P2: provide an update every **2 hours** during business hours.
- For P3/P4: respond within the SLA above; no rolling updates required unless customer asks.

## Postmortems
Every P1 and every customer-impacting P2 triggers a postmortem within 5 business days.
Postmortems are shared with the customer in summary form. Internal postmortems include:

- Timeline.
- Root cause.
- What we did well.
- What we did poorly.
- Action items with owners and due dates.

## Disagreements
If a customer disagrees with our triage, escalate to the Head of Customer Success. We do not
argue severity in the ticket — we re-triage and document the decision.

## Out-of-Hours
- **Essentials** customers: no after-hours coverage. P1s are picked up at start of business.
- **Growth** customers: P1 best-effort after-hours, no committed SLA.
- **Scale** customers: P1 covered 24/5, P2 covered business hours.
- **Enterprise** customers: as negotiated; default 24/7 P1, 24/5 P2.

## Customer Escalation Path
Customers can escalate beyond their CSM as follows:

1. CSM
2. Head of Customer Success — `cs-lead@novaedge.io`
3. CEO — `founder@novaedge.io` (use sparingly)

We never punish a customer for escalating. Escalation is a feature, not a flag.
