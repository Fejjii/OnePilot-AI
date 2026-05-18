# NovaEdge Solutions — Customer Onboarding Guide

Onboarding runs from **day 0** (contract signed) to **day 30** (post-launch tuning closeout).
This document is the canonical script. Do not improvise — if something is missing here, flag
it to the Head of Delivery so we can update the playbook.

## Day 0 — Kickoff Pack
Within 24 hours of signed SOW, send the customer:

- Welcome email (template in `email_templates.md`, subject "Welcome to NovaEdge").
- The kickoff agenda (60 minutes).
- A short security overview (`security_policy.md`, `data_privacy_policy.md`).
- The integration prerequisites doc (`integration_guide_hubspot_gmail_calendar.md`).
- The shared Slack invite (Growth, Scale, Enterprise only).

## Day 1 — Kickoff Call
**Agenda (60 minutes):**

1. Introductions and roles (5 min).
2. Re-confirm scope and success criteria (10 min).
3. Walk through the timeline (10 min).
4. Identify integration prerequisites and credentials owners (15 min).
5. Review the data-privacy posture (10 min).
6. Confirm next steps and the weekly cadence (10 min).

**Outputs to record:**

- Customer champion (named).
- Procurement / security contact (named).
- Integration owners (HubSpot, Gmail, Calendar — named).
- Risks and assumptions (written).

## Days 2-5 — Discovery and Access
- Schedule **workflow deep-dives** with the operators (support team, sales team, ops team).
- Collect at least **30 example tickets / emails / leads** for each workflow we are
  automating.
- Get the customer to grant access to the integrations (see
  `integration_guide_hubspot_gmail_calendar.md`).
- Confirm escalation paths (`escalation_policy.md`).

## Days 6-14 — Build
- Ingest the customer's knowledge base into their tenant.
- Build the first version of each prompt/workflow using NovaEdge's prompt library.
- Run **offline evals** against the collected examples. Target: **>= 85% accuracy** for
  classification workflows, **>= 70% confident answers** for RAG workflows.
- Configure approval routes (`ai_usage_policy.md`).

## Days 15-21 — Internal Pilot
- Run the workflow in **draft-only** mode against real production traffic.
- The customer reviews drafts daily for 3-5 business days.
- Capture every override the customer makes — those are the highest-value examples for
  prompt tuning.
- Iterate prompts at least twice during this week.

## Days 22-28 — Go-Live
- Move the workflow to **approval-required** or **autonomous** mode, per the SOW.
- Switch reply mode in Gmail / chat to live.
- Notify the customer team and provide a one-page user guide.
- Monitor dashboards daily for the first 5 business days.

## Day 29-30 — Closeout
- Run the 30-day review meeting.
- Present:
  - Performance vs. success criteria.
  - Gap analysis: questions we could not answer, drafts the customer rewrote heavily.
  - Recommendations for the next quarter (additional workflows, new docs to ingest, etc.).
- Confirm the handoff to the ongoing retainer team (see `customer_success_sop.md`).

## Common Onboarding Risks
- **Champion leaves the company mid-onboarding.** Mitigation: identify a backup on day 1.
- **Integration prerequisites missing.** Mitigation: send the prerequisites doc before
  contract signing.
- **Knowledge base is bad.** Mitigation: do not paper over it. Tell the customer that the
  agent will only be as good as its knowledge base, and help them prioritize document
  hygiene.
- **Customer expects autonomous mode on day 1.** Mitigation: explain the draft → approval →
  autonomous progression and the reason for it (`ai_usage_policy.md`).

## Onboarding Roles
- **Account Executive (AE):** owner through Closed-Won, available during onboarding.
- **Implementation Engineer:** primary builder; owns the technical delivery.
- **Customer Success Manager (CSM):** owner from day 14 onwards.
- **Engineering on-call:** available for outages or major bugs only.

## Onboarding Quality Gate
Before declaring an account "onboarded," the CSM must confirm:

- [ ] At least one workflow is live and producing measurable value.
- [ ] The customer can articulate which actions are autonomous, approval-required, or
      draft-only.
- [ ] The integration health page is green.
- [ ] The customer's champion has had a 1:1 with the CSM.

If any of those is false, onboarding is **not done**, regardless of the calendar.
