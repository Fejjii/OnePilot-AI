# NovaEdge Solutions — Services Overview

This document describes the four packaged services NovaEdge delivers and how they fit together.
For pricing tiers, see `pricing_plans.md`. For sales positioning, see `sales_playbook.md`.

## 1. AI Inbox Triage
**Goal:** stop your team from manually sorting hundreds of emails per day.

**What we automate:**
- Classification of incoming email by intent: sales, support, billing, internal, spam.
- Priority scoring (P1 / P2 / P3) based on customer tier and urgency cues.
- One-paragraph summarization of long threads.
- Suggested reply drafting using approved tone and templates from `email_templates.md`.
- Automatic routing to the right inbox, Slack channel, or HubSpot owner.

**Typical KPIs after 30 days:**
- 60-75% reduction in time-to-first-response.
- 40-55% drop in time spent reading email.
- < 2% misclassification rate after tuning.

**Where humans stay in the loop:**
- Replies to refund requests, complaints, and enterprise contracts always require human approval
  (see `escalation_policy.md`).

## 2. AI Support Agent (RAG)
**Goal:** answer up to 70% of tier-1 support questions without an agent on shift.

**How it works:**
1. We ingest your knowledge base (help center articles, internal SOPs, product docs).
2. Documents are chunked, embedded, and stored in a Qdrant vector index scoped to your tenant.
3. Incoming questions are answered by an LLM **grounded in retrieved passages**, with citations.
4. If retrieval evidence is weak or below confidence threshold, the bot **does not guess** — it
   politely escalates to a human and creates a ticket.

**What you get:**
- A chat widget, an email auto-responder, or a Slack/Teams bot.
- Per-answer citation list (document title + section).
- Confidence scores and weak-evidence logging for ongoing tuning.
- A monthly **gap report** identifying questions the bot could not confidently answer.

## 3. Lead Qualification & Follow-up
**Goal:** stop dropping warm leads because nobody had time to follow up.

**Capabilities:**
- Inbound qualification chats that ask 3-5 qualifying questions (BANT or custom rubric).
- Automatic lead scoring and CRM enrichment (HubSpot, Pipedrive).
- Sequenced follow-up emails when prospects go cold.
- AI-drafted personalized outreach using public signals (company size, role, recent news).
- Hand-off to a human owner once a lead crosses the qualified threshold.

**Guardrails:**
- We never auto-send cold outreach without explicit configuration approval.
- All AI-generated emails are reviewed for compliance with CAN-SPAM and CASL.

## 4. Appointment Booking Assistant
**Goal:** book qualified meetings into your calendar without ping-pong.

**Capabilities:**
- Calendar-aware scheduling for Google Calendar and Outlook.
- Multi-attendee coordination.
- Time-zone-correct proposals.
- Automatic rescheduling and reminders.
- Conflict resolution when invitees overlap.

**Where it does not act unattended:**
- Bookings with VIP customers or values above a configurable threshold require human confirmation.

## Cross-Cutting Capabilities
All packages share a common foundation:

- **Multi-tenant isolation** — every customer is a separate tenant; data is never co-mingled.
- **Audit logs** — every AI action is logged with input hash, output hash, model, and confidence.
- **Quota and usage tracking** — token, request, and tool-call usage is tracked per workspace.
- **Human approval workflows** — destructive or high-value actions can require explicit approval.
- **Provider abstraction** — we can swap LLM, embedding, and vector providers without redoing
  integrations.

## Engagement Path
A typical NovaEdge engagement runs:

1. **Discovery Call** (free, 60 min). See `discovery_call_script.md`.
2. **Pilot** (4 weeks). One workflow, fixed scope, $4,900 USD.
3. **Standard Implementation** (8 weeks). Two or three workflows, $14,900 USD.
4. **Managed Automation Retainer** (ongoing). See `pricing_plans.md`.

Customers can graduate to **Enterprise** if scope expands or compliance requirements grow
(custom pricing, dedicated CSM).
