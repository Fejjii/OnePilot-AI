# NovaEdge Solutions — Objection Handling

This document is the **single source of truth** for how NovaEdge reps respond to common
objections. If a prospect raises something not covered here, escalate to a senior AE before
quoting a custom answer.

## Pricing Objections

### "It's too expensive."
**Response:** "Compared to what?" Then quantify against the customer's current pain. A $14,900
Standard Implementation pays back in ~3 months for a team spending 40 hours / week on email triage
at a $35/hour blended cost.

**Discount matrix (without VP approval):**
- Up to 10% on retainer for an annual prepay.
- Up to 5% one-time discount on Implementation if signed within 7 days of proposal.
- No discount on Pilot. Pilot is a fixed-fee proof of value.

### "Can you just bill on outcomes?"
**Response:** Not for the first 90 days. We need a baseline implementation period to calibrate.
After the initial retainer term we can discuss outcome-based pricing on **renewals only**.

### "Why don't you charge per seat?"
**Response:** Our value is conversation volume, not headcount. Per-seat pricing punishes the
customers who use us most. We will not seat-license.

## Build vs Buy Objections

### "We have engineers, we can build this ourselves."
**Response:** Many of our customers tried. The hard part is not the prompt — it is:
- Multi-tenant isolation and audit logging.
- Eval harness and weekly regression testing.
- Vector index ops and re-embedding pipelines.
- Provider failover when OpenAI has an outage.
- Compliance documentation for procurement.

We have already paid for those mistakes. Quote the **time-to-first-value comparison**: NovaEdge
ships a Pilot in 4 weeks. In-house projects typically take 4-6 months to reach the same point.

### "We already use a generic AI tool — Copilot, Gemini, ChatGPT."
**Response:** Great. Those are great for individuals. We solve the **team-level** problem:
shared knowledge, audit, approval workflows, multi-channel triage, integrations with HubSpot
and Gmail, and an evaluation harness. We complement those tools rather than replacing them.

## Trust and Risk Objections

### "What about hallucinations?"
**Response:** Our RAG agent uses retrieval-grounded answers with citations. When evidence is
weak, **it does not guess** — it escalates. See `customer_faq.md` and `ai_usage_policy.md` for
the exact policy. We also run weekly evals and produce a monthly accuracy report.

### "Where does our data go?"
**Response:** All data is stored in the customer's tenant in OnePilot AI. We do not train any
third-party model on customer data. Default region is `ca-central-1`; EU customers get
`eu-central-1`. See `data_privacy_policy.md`.

### "Are you SOC 2 / ISO 27001 certified?"
**Response:** SOC 2 Type II is **in progress**, targeted Q4 2026. We are happy to share our
current security policy, DPIA, and pen-test results. We are not ISO 27001 certified and will
not pretend to be. If certification is a hard procurement gate, suggest a 60-day delayed
start that aligns with our audit timeline.

## Competition Objections

### "We're also evaluating <competitor>."
**Response:** Acknowledge it. Ask which criteria matter most. Then ask: "What would have to be
true for NovaEdge to be the obvious choice?" If they cannot answer, you have not earned the
right to win the deal yet.

### "<Competitor> is cheaper."
**Response:** Likely true. Quote the **fully-loaded** cost: implementation + monthly fees +
the customer's engineering time. NovaEdge wins on time-to-value, integrations, and audit
features. If they want the absolute cheapest tool, refer them out gracefully.

## Timing Objections

### "Let's revisit next quarter."
**Response:** "Specifically — what changes by next quarter?" If nothing concrete, this is a
polite no. Mark Closed-Lost / Nurture and set a reminder. Do not chase indefinitely.

### "Our priorities just shifted."
**Response:** Confirm whether priorities shifted **away from this problem** or away from
**this solution**. The first is a real signal; the second is winnable.

## Escalation
Anything beyond the matrix above needs sign-off from:
- **Discounts > 10%** → VP of Revenue.
- **Custom SOW deviations** → Head of Delivery.
- **Compliance commitments** → Head of Security.

Document the request and the approval inline in the deal record in HubSpot.
