# NovaEdge Solutions — Customer Success SOP

This SOP describes how the Customer Success team operates once a customer has gone live.
Onboarding handoff happens on day 14-30 (see `onboarding_guide.md`). After that, the CSM
owns the relationship.

## Account Tiers and Cadence
| Plan        | Touchpoint cadence            | QBR / EBR cadence | Slack channel |
|-------------|-------------------------------|-------------------|---------------|
| Essentials  | Monthly email check-in        | None              | No            |
| Growth      | Bi-weekly call (30 min)       | Quarterly         | Yes (shared)  |
| Scale       | Weekly call (30 min)          | Monthly           | Yes (shared)  |
| Enterprise  | Weekly call + executive review| Monthly           | Yes (private) |

CSMs are expected to **never** miss a scheduled touchpoint without 48-hour notice and a
written reschedule.

## What a Weekly / Bi-weekly Touchpoint Covers
1. **Health metrics** (5 min): conversation volume, autonomous-resolution rate, escalation
   rate, drift signals.
2. **Open items** (10 min): tickets, prompt iterations, gap report progress.
3. **Customer feedback** (5 min): friction points, requested features, concerns.
4. **Next steps** (5 min): assigned owners and due dates.
5. **Internal capture** (5 min): write the recap into HubSpot before EOD.

## Quarterly Business Reviews (QBRs)
For Growth and above, run a **45-minute** QBR with the customer's economic buyer present.

**Required artifacts:**
- Performance dashboard (conversations, resolution rate, accuracy, latency).
- ROI calculation (time saved, ticket deflection, hours reclaimed).
- Gap report.
- Roadmap recommendations for the next quarter.
- Renewal posture (Healthy / At-Risk / Critical).

## Health Scoring
A simple traffic-light system:

- **Green** — all KPIs above target; champion engaged; no open P1/P2; renewal likely.
- **Yellow** — at least one KPI below target, or a champion change, or one open P2; needs a
  written intervention plan within 5 business days.
- **Red** — sustained KPI miss, or a P1 within last 30 days, or no champion engagement;
  requires Head of CS engagement and a 30-day save plan.

Health is updated **monthly** by the CSM. The Head of CS reviews all Yellow / Red accounts
each Monday.

## Save-Plan Template
For any Red account:

1. Root cause (one paragraph).
2. Three concrete actions with dates and owners.
3. Communication plan with the customer.
4. Renewal forecast and confidence level.

## Renewals
- Renewals begin **90 days** before contract end for Scale / Enterprise.
- Renewals begin **60 days** before for Growth.
- Essentials renewals are automatic; the CSM only intervenes if health is Yellow / Red.
- A renewal call is mandatory for Growth and above.

## Expansion
Expansion conversations are a CS responsibility, not Sales. CSMs propose expansion when:

- The customer is consistently > 80% of plan usage.
- A new use case has been validated in a 30-day mini-pilot.
- The customer has explicitly asked.

Sales is looped in only if the expansion is large enough to require a new SOW.

## When To Loop In Other Teams
- **Engineering:** for bugs, outages, or anything in `support_troubleshooting.md` you cannot
  resolve.
- **Sales:** for renewals at risk, expansion, contract renegotiation.
- **Security:** for any privacy or compliance request.
- **Legal:** for DPA updates, regulatory inquiries.

Use the templates in `email_templates.md` for the standard customer-facing communications.

## Forbidden Behaviors
- Do not promise a feature before checking the roadmap with Product.
- Do not give a refund or credit outside the matrix in `refund_policy.md` without approval.
- Do not bypass the audit log to "fix something quickly."
- Do not let a Red account go more than two weeks without an executive update.
