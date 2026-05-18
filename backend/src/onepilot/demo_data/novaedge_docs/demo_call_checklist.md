# NovaEdge Solutions — Demo Call Checklist

This checklist applies to **demo calls only** — the dedicated session that follows
discovery. If you have not yet done discovery, do not run a demo; use the discovery script
in `discovery_call_script.md` instead.

## Goals of a Demo Call
1. Show, in 30 minutes, that NovaEdge solves the specific problem the prospect described.
2. Surface objections that did not appear in discovery.
3. Earn the right to send a proposal.

## 24 Hours Before
- [ ] Re-read discovery notes.
- [ ] Open the NovaEdge **demo workspace** (`org_demo_novaedge`) and confirm it loads.
- [ ] Refresh the demo workspace data by running `POST /demo/seed` (idempotent).
- [ ] Confirm at least 19 documents are ingested and visible in `/documents`.
- [ ] Prepare a one-page agenda; share it with the prospect.

## 30 Minutes Before
- [ ] Test screen-share.
- [ ] Test microphone.
- [ ] Close every non-demo browser tab. No customer data on screen. Ever.
- [ ] Open the relevant demo workflow tab(s).
- [ ] Set Slack to do-not-disturb.

## On the Call

### 0:00 — Reframe (3 min)
> "Last time we agreed the problem was {problem}. The success metric was {metric}. Today I'll
> show how NovaEdge gets you there. I'll pause every few minutes for your reactions — please
> interrupt freely."

### 0:03 — Show, don't tell (15 min)
- Walk through **one** workflow end to end.
- Use **the prospect's words** in the demo prompt. If they said "ticket triage", use
  "ticket triage", not "inbox triage".
- Show the audit log. This is a NovaEdge differentiator — do not skip it.
- Show the citation list on a RAG answer.
- Show what happens when evidence is weak (the agent escalates, doesn't guess).

### 0:18 — Differentiators (5 min)
- Multi-tenant isolation.
- Per-workflow autonomy controls (`ai_usage_policy.md`).
- Approval flows.
- Quota and usage tracking.

### 0:23 — Reactions (5 min)
- "What worked?"
- "What did I skip that you wanted to see?"
- "What concern is still open?"

### 0:28 — Next Step (2 min)
- Confirm the next step (proposal date, pilot start, technical deep-dive).
- Confirm who owns it.

## Forbidden Demos
- **Live customer data.** Never. Even a quick "let me show you something cool".
- **Production credentials on a personal laptop.** Use the sanctioned demo workstation.
- **Half-built workflows.** If a workflow is not production-ready, do not demo it.

## Things to Have Ready in the Demo Workspace
- 19 ingested NovaEdge knowledge documents (this very deck).
- At least 30 example tickets, 100 example leads, 20 example email drafts.
- At least one example of a **weak-evidence escalation** to show the guardrail.
- At least one example of an **approval-required action** in flight.

## Post-Call (within 24 hours)
- [ ] Send the recap email (template in `email_templates.md`, "Discovery Recap and Next
      Steps").
- [ ] Update the HubSpot deal record.
- [ ] If the prospect requested specific follow-ups, owner + due date in HubSpot.
- [ ] Mark the next step in your calendar.

## Demo Anti-Patterns
- **Feature tour.** Resist the urge to "show everything". Show one thing well.
- **Speaker-mode.** If you're talking more than 70% of the time, you're losing.
- **Slide-deck dependency.** Live product > slides. Always.
- **Skipping the audit log.** It is the #1 differentiator and the easiest to forget.
