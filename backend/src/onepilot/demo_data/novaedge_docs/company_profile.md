# NovaEdge Solutions — Company Profile

## Who We Are
NovaEdge Solutions is a B2B AI automation consultancy founded in 2023 and headquartered in Toronto, Canada.
We are a small, remote-first team of 18 engineers, consultants, and customer success specialists.
Our mission is to help small and mid-sized businesses (typically 10 to 200 employees) put AI
to work on the operational chaos that drains their teams: customer support, lead qualification,
email workflows, internal knowledge search, and appointment booking.

Our tagline is **"Your AI workforce, finally without the chaos."**

## Who We Serve
NovaEdge focuses on three primary customer segments:

- **Professional services firms** (agencies, consultancies, law and accounting practices) that need
  to handle a high volume of inbound emails and qualified leads.
- **B2B SaaS startups** between seed and Series B that want to automate tier-1 support and reduce
  ticket backlog without hiring more agents.
- **Local service businesses** (clinics, real-estate teams, home services) that need automated
  appointment booking, reminders, and follow-up.

We deliberately do not serve enterprise customers above ~1,000 employees. Our methodology and
pricing are optimized for fast, opinionated rollouts at SMB scale.

## What We Do
We deliver four practical, repeatable AI automation packages:

1. **AI Inbox Triage** — automatic email classification, summarization, and reply drafting.
2. **AI Support Agent** — retrieval-augmented (RAG) support assistant grounded in the customer's
   internal knowledge base.
3. **Lead Qualification & Follow-up** — automated lead scoring, qualification chats, and
   sequenced follow-up across email and CRM.
4. **Appointment Booking Assistant** — calendar-aware scheduling for demo calls, intro calls,
   and consultations.

Each package can be deployed standalone or combined under a managed automation retainer.

## How We Engage
We have four engagement tiers:

- **Discovery Call** — free 60-minute scoping session.
- **Pilot Engagement** — fixed-scope 4-week pilot at $4,900 USD, focused on one workflow.
- **Standard Implementation** — 8 weeks, $14,900 USD, includes integrations and handoff.
- **Enterprise Implementation** — 12+ weeks, custom pricing.

After implementation, most customers move into a **Managed Automation Retainer**
(see `pricing_plans.md`).

## Platforms We Integrate With
We support the following integrations out of the box:

- **CRM:** HubSpot (primary), Pipedrive, and Salesforce (read-only sync).
- **Email:** Gmail / Google Workspace, Microsoft 365 / Outlook.
- **Calendar:** Google Calendar, Microsoft Outlook Calendar.
- **Helpdesk:** Zendesk, Intercom, Freshdesk.
- **Collaboration:** Slack, Microsoft Teams.

Custom integrations are available under Enterprise engagements.

## Models and Stack
NovaEdge is model-agnostic, but our default stack is:

- **GPT-4o-mini** for routine triage, classification, and short-form tasks.
- **GPT-4o** and **Claude 3.5 Sonnet** for complex reasoning, long-form drafting, and policy-sensitive responses.
- **OpenAI text-embedding-3-small** for vector embeddings.
- **Qdrant** for retrieval-augmented knowledge bases in production.
- **OnePilot AI** as our internal control plane (audit, quotas, tenant isolation).

## Compliance and Trust
- NovaEdge is **GDPR-aware** and **PIPEDA-aligned**.
- SOC 2 Type II audit is **in progress**, target completion 2026 Q4.
- We do not train third-party models on customer content.
- All customer data is stored regionally where required (EU customers default to `eu-central-1`).
- Every AI action is logged in the OnePilot audit log and scoped by `organization_id`.

## Contact
- Website: **novaedge.io**
- Sales: **sales@novaedge.io**
- Support: **support@novaedge.io**
- Phone: **+1 (416) 555-0190**

For escalation rules, see `escalation_policy.md`. For our refund terms, see `refund_policy.md`.
