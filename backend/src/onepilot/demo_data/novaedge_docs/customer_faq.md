# NovaEdge Solutions — Customer FAQ

This is the public-facing FAQ. It is the canonical answer set for questions the AI support
agent and customer-facing reps are allowed to answer directly. If a question is not in here,
the AI agent should not answer it — it must escalate.

## General

### What is NovaEdge?
NovaEdge Solutions is a B2B AI automation consultancy. We help small and mid-sized businesses
automate customer support, lead qualification, email triage, internal knowledge search, and
appointment booking. See `company_profile.md`.

### Where are you located?
We are remote-first with a registered office in Toronto, Canada. Most of our team is in
North America and Europe.

### Do you work with companies outside North America?
Yes. We have customers in the US, Canada, the UK, France, Germany, the Netherlands, and
Australia. For EU customers, data is stored in `eu-central-1` by default.

## Product

### What does the AI agent actually do?
It depends on the package. The most common deployment is the AI Support Agent: a chat/email
bot that answers tier-1 customer questions using your knowledge base, with citations. See
`services_overview.md`.

### Can the AI take actions, or just answer questions?
Both, with controls. We support **read-only** mode, **draft-only** mode, **approval-required**
actions, and **fully autonomous** actions. The level of autonomy is configurable per workflow.
Destructive or high-value actions always require approval. See `ai_usage_policy.md`.

### What if the AI gets something wrong?
The agent is configured to **not answer** when retrieval evidence is weak (confidence below
the configured threshold — default 0.30). It will instead say something like "I don't have a
confident answer — let me get a human" and create a ticket. We also publish a monthly
accuracy report.

### Can we add our own knowledge base?
Yes. Most customers upload between 30 and 300 documents during onboarding. We support PDF,
DOCX, Markdown, plain text, and CSV. We do not currently parse images or scanned PDFs.

### Which LLMs do you use?
By default, **GPT-4o-mini** for routine traffic and **GPT-4o** or **Claude 3.5 Sonnet** for
complex tasks. You can request a specific model in your contract. See `ai_usage_policy.md`.

## Security and Privacy

### Do you train models on our data?
No. Customer data is never used to train third-party models. See `data_privacy_policy.md`.

### Where is our data stored?
By default in `ca-central-1`. EU customers default to `eu-central-1`. US-data-residency
customers can be hosted in `us-east-1`. See `security_policy.md`.

### Are you SOC 2 / ISO 27001 / HIPAA compliant?
SOC 2 Type II is in progress (target: Q4 2026). We are not ISO 27001 certified. HIPAA is
available under a Business Associate Agreement only for Enterprise customers. See
`security_policy.md`.

### Can we get a DPA?
Yes. Our standard DPA is available on request from `legal@novaedge.io`.

## Billing

### How am I billed?
Monthly, in advance, in USD. You can also choose annual prepay for a 10% discount. We accept
ACH, wire transfer, and major credit cards. See `pricing_plans.md`.

### What if I go over my plan limit?
You will receive a soft warning at 80% of plan usage and a hard warning at 100%. Overages are
billed at the end of the month at the per-conversation rate published in `pricing_plans.md`.
No service interruption.

### Can I downgrade?
Yes, at the next renewal date. Mid-cycle downgrades are not allowed. See `refund_policy.md`.

### How do I cancel?
Email `support@novaedge.io` from your account-admin address. Cancellations take effect at the
end of the current billing period. Refunds are governed by `refund_policy.md`.

## Support

### How do I reach you?
- Email: `support@novaedge.io`
- Slack: shared channel for Growth, Scale, and Enterprise customers.
- Phone: +1 (416) 555-0190 (business hours, North America).
- See `escalation_policy.md` for the SLA matrix.

### What are your business hours?
Monday-Friday, 09:00-18:00 Eastern Time. Scale customers also receive an after-hours
on-call number for incidents. Enterprise customers can request 24/7 coverage.

### What counts as an incident?
- **P1:** Service down for all users.
- **P2:** Major feature degraded (e.g., RAG returns no results).
- **P3:** Minor issue that does not block business operations.
- **P4:** Question or feature request.

See `support_troubleshooting.md` and `escalation_policy.md`.
