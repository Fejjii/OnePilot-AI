# NovaEdge Solutions — Sample Meeting Notes

This document contains anonymized sample meeting notes from NovaEdge customer engagements.
They are used for prompt training, demo scenarios, and onboarding new reps. All names and
company details are fictional.

---

## Discovery Call — BrightCloud Consulting (2026-04-08)

**Attendees:**
- Customer: Mia Park (COO), Daniel Wu (Head of Customer Operations)
- NovaEdge: Erin Sato (AE)

**Company overview:**
- 42-person consultancy in Vancouver. Recurring SaaS implementation services.
- Annual revenue ~$6.8M.
- 4 customer-operations agents handle ~250 emails/day.

**Pain:**
- 60% of emails are repeat-pattern questions (status, scope, onboarding logistics).
- Average first-response time is **4.5 hours**. Goal: 30 minutes.
- Daniel personally reviews every refund request — 8-12 per month.

**Success criteria (90-day):**
- FRT < 30 minutes.
- Tier-1 deflection > 50%.
- Refunds still 100% human-reviewed (do not automate).

**Constraints:**
- HubSpot Pro plan, Gmail Workspace.
- Procurement requires DPA review (2 weeks).
- Budget: $5K-$20K for project, $2K-$5K/month retainer.

**Decision criteria:**
1. Integration with HubSpot.
2. Audit log.
3. Time-to-value < 60 days.

**Next step:** Erin sends proposal by 2026-04-12 for a Pilot.
**Champion:** Daniel Wu.

---

## QBR — Halcyon Health Network (2026-03-15)

**Attendees:**
- Customer: Anika Verma (VP Operations), Jamal Rivers (IT Director)
- NovaEdge: Priya Iyer (CSM), Owen MacLean (Implementation Lead)

**Last quarter:**
- Conversations handled by AI: 7,420 (target was 6,000). **Green.**
- Autonomous resolution rate: 58% (target 55%). **Green.**
- Escalation rate: 27% (target < 30%). **Green.**
- Customer-reported NPS impact: +6 points QoQ.

**Open items:**
- Two prompt-template iterations completed; one outstanding for refund pattern (defer to next
  quarter; refunds still 100% manual).
- New knowledge documents added: 12.
- Gap report: 14 questions the bot did not confidently answer; KB update in flight.

**Next quarter focus:**
- Stand up the Lead Qualifier workflow in draft-only.
- Increase Scale plan limits if conversation volume continues to grow.
- Begin SOC 2 procurement questionnaire review (we are still in-progress; flagged for
  Anika's procurement).

**Health rating:** Green. Renewal scheduled 2026-09-30.

---

## Incident Postmortem — VelocityRetail (2026-02-19)

**Incident:** P2 — HubSpot sync stopped for 4 hours.

**Timeline:**
- 09:14 — HubSpot rotated their rate-limit window. NovaEdge poller fell behind.
- 09:42 — Customer reported "deals not updating".
- 09:53 — NovaEdge engineering on-call confirmed the issue.
- 10:30 — Polling interval increased from 1 min to 5 min; rate-limit budget tuned.
- 13:00 — Sync caught up.
- 13:30 — Customer confirmed resolution.

**Root cause:** Our HubSpot client was hitting the per-app rate limit. We had no exponential
backoff on burst calls.

**Customer impact:** 187 deal updates delayed by up to 4 hours. No data lost.

**Action items:**
- Add exponential backoff and jitter to all HubSpot calls (Owner: Owen, due 2026-03-01).
- Add an integration-health page with last-success timestamps (Owner: Erin, due 2026-03-05).
- Update `support_troubleshooting.md` with this scenario (Owner: Priya, done 2026-02-21).

**Customer service credit issued:** 3% of February retainer ($114).

---

## Renewal Call — Stellar Pediatrics Clinic (2026-04-02)

**Attendees:**
- Customer: Dr. Maya Chen (Owner), Tomas Reyes (Office Manager)
- NovaEdge: Priya Iyer (CSM)

**Context:**
- 1-year customer on Essentials plan.
- Workflow: Appointment Booking Assistant.

**Performance:**
- 1,640 appointments booked / rescheduled in the year.
- 92% scheduled without human touch.
- 8% required staff confirmation (mostly multi-attendee).

**Customer feedback:**
- "It feels like we added a part-time admin without hiring anyone."
- Wants to add an after-hours intake form workflow next.

**Outcome:**
- Renewed Essentials for another 12 months.
- Quoted Pilot for new workflow ($4,900) — they agreed verbally; SOW to be sent within 48h.
- Champion: Tomas. Backup: Dr. Chen.

---

## Discovery Call — NorthGate Realty Group (2026-04-22)

**Attendees:**
- Customer: Riku Tanaka (Managing Broker)
- NovaEdge: Erin Sato (AE)

**Outcome:** Disqualified.

**Reason:** 3-person team, no CRM, lead volume < 5/week. Outside ICP (`sales_playbook.md`).

**Next step:** Sent a polite decline and referred them to a templated automation tool that
better fits their scale. No follow-up scheduled.

---

## Save Plan Review — IronStack DevTools (2026-03-25)

**Status:** Red account.

**Issue:**
- Champion (Head of Support) left the company 2026-02-04.
- Replacement is skeptical of the project.
- Conversation volume dropped 40% month-over-month — likely because the new lead routed
  tickets back to humans.

**Plan:**
1. Schedule a 1:1 with the new champion within 7 days.
2. Re-walk the success criteria using last quarter's data.
3. Offer to lower the autonomy mode to draft-only for 30 days to rebuild trust.

**Owner:** Priya. Re-review in 30 days.
