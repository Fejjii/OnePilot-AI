# NovaEdge Solutions — Sales Playbook

This playbook tells the NovaEdge sales team how to move a prospect from first contact to
signed Pilot or Standard Implementation. It is intentionally opinionated — follow it unless
you have a specific, documented reason not to.

## Ideal Customer Profile (ICP)
A "perfect" NovaEdge customer matches **at least four** of these signals:

- 10-200 employees.
- Existing CRM (HubSpot, Pipedrive, Salesforce) and Gmail/M365.
- At least one team currently drowning in email or support tickets.
- A named operations or revenue leader who can champion the project.
- Budget authority for $5K - $20K project spend.
- Annual revenue between $1M and $50M.

Disqualify if:
- Fewer than 5 employees and no recurring revenue.
- Heavy regulatory environment without a clear AI policy (financial services with no AI committee, healthcare without HIPAA Business Associate path).
- Looking for "an AI strategy consultant" rather than an implementation partner.

## Sales Stages
1. **MQL** — inbound form, demo request, referral.
2. **SQL** — discovery call booked.
3. **Discovery** — discovery call completed; pain confirmed.
4. **Scoping** — written proposal sent.
5. **Negotiation** — pricing/terms discussion.
6. **Closed-Won** — signed SOW or order form.
7. **Closed-Lost** — explicit no, or 30 days of silence.

Move stages only when the **next-step criteria** are met. Do not advance for activity alone.

### Stage Exit Criteria
- **MQL → SQL**: prospect has a calendar slot booked.
- **SQL → Discovery**: discovery call attended; problem statement confirmed.
- **Discovery → Scoping**: budget range confirmed; champion identified; timeline acknowledged.
- **Scoping → Negotiation**: proposal sent; champion has reviewed; objections surfaced.
- **Negotiation → Closed-Won**: SOW signed.

## Discovery Mantra
Use the **MEDDIC-lite** rubric in discovery (we drop "Identify pain" because everyone has pain).

- **M**etrics — what KPI will this move? Be specific (e.g., "cut FRT from 4h to 30m").
- **E**conomic buyer — who signs?
- **D**ecision criteria — what makes us win? Price, integrations, references?
- **D**ecision process — what does their procurement look like?
- **C**hampion — who advocates internally?

Anything missing must be filled in before sending a proposal.

## Proposals
- Use the standard SOW template (see internal Notion).
- Default to Pilot unless the prospect explicitly needs a multi-workflow rollout.
- Always include the scope, exclusions, timeline, deliverables, and pricing in writing.
- Quote prices from `pricing_plans.md`. Discount rules in `objection_handling.md`.

## Demo Etiquette
Run demos using the **NovaEdge demo workspace** (org `org_demo_novaedge`) — never live
customer data. Confirm the demo checklist from `demo_call_checklist.md` is complete before
the call.

## Follow-up
After every prospect touch, send a follow-up email within **24 hours**. Use the templates in
`email_templates.md` (subject lines: "Recap and next steps", "Quick scoping question",
"Proposal v1"). Each follow-up must:

- Restate the agreed problem.
- Confirm the agreed next step and its owner.
- Include a calendar link only if a meeting is the next step.

## Handoff to Delivery
At **Closed-Won**, transfer the account to Customer Success using the handoff template in
`customer_success_sop.md`. Include:

- Final SOW.
- Discovery notes.
- Integration list and access plan.
- Risk flags.
- Champion contact.

Do not skip the handoff call. Customers who skip handoff have a **2.3x higher** churn rate in
the first 90 days.

## Forbidden Behaviors
- No "AI will replace your team" framing. Ever. We sell augmentation.
- No promises about regulatory certifications we do not hold (see `security_policy.md`).
- No deal-specific discounts beyond the matrix in `objection_handling.md` without VP approval.
- No bypassing the audit log, even for demos.
