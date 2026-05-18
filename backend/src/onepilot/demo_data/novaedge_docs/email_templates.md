# NovaEdge Solutions — Email Templates

These are the approved email templates the team and the AI agents use. They are deliberately
short and direct. Do not invent new templates without review.

Placeholders in curly braces `{like_this}` are replaced at send time.

---

## 1. Welcome to NovaEdge
**Subject:** Welcome to NovaEdge, {first_name}

Hi {first_name},

Welcome to NovaEdge. I'm {csm_name}, your Customer Success Manager. Over the next 30 days
we'll have you live on {workflow_name}.

Three quick things for the kickoff call on **{kickoff_datetime}**:

1. Confirm the integration owners for HubSpot, Gmail, and Calendar.
2. Identify your champion and one backup.
3. Bring 30 sample {workflow_artifact} (emails / tickets / leads).

Talk soon,
{csm_name}

---

## 2. Discovery Recap and Next Steps
**Subject:** Recap and next steps — NovaEdge

Hi {first_name},

Thanks for the conversation today. Quick recap of what I heard:

- **Problem:** {problem_summary}
- **Goal:** {goal_summary}
- **Constraints:** {constraints}

Next step: I'll send a proposal by **{proposal_date}**. If anything above is off, please flag
it now so I can fix the scope.

Best,
{ae_name}

---

## 3. Proposal v1
**Subject:** Proposal — {workflow_name} Pilot for {customer_company}

Hi {first_name},

Attached is the proposal for a 4-week Pilot of {workflow_name}.

- **Scope:** {scope}
- **Timeline:** {timeline}
- **Investment:** $4,900 USD, fully refundable in the first 7 days.
- **Success criteria:** {success_criteria}

I'm available for any clarifying questions on Wednesday at **{availability}**.

Best,
{ae_name}

---

## 4. Renewal Heads-Up (60 days)
**Subject:** Heads-up on your NovaEdge renewal — {customer_company}

Hi {first_name},

Your retainer renews on **{renewal_date}**. Two reasons I'm reaching out:

1. I'd like to schedule a 30-minute review to confirm you're getting value.
2. If you'd like to expand or change scope, we have time to plan it before renewal.

Does **{proposed_time}** work?

— {csm_name}

---

## 5. Support — Confident RAG Answer
**Subject:** RE: {customer_subject}

Hi {first_name},

{rag_answer_body}

Source(s):
- {citation_1}
- {citation_2}

If this didn't fully answer your question, just reply and a human will jump in.

— NovaEdge Support

---

## 6. Support — Weak Evidence Escalation
**Subject:** RE: {customer_subject}

Hi {first_name},

Thanks for reaching out. I don't have a confident answer based on the knowledge I have, so
I've forwarded this to a human teammate. They will reply within **{sla}**.

— NovaEdge Support

---

## 7. Refund Acknowledgement
**Subject:** Your NovaEdge refund request

Hi {first_name},

We received your refund request for **{engagement_name}**. A human teammate will review it
under the terms of `refund_policy.md` and reply within **3 business days**.

You will not be charged the next invoice until the request is resolved.

— NovaEdge Billing

---

## 8. Outage Acknowledgement
**Subject:** Incident in your NovaEdge workspace

Hi {first_name},

We are aware of {incident_summary} affecting {workspace_id}.

- **Severity:** {severity}
- **Engineer on-call:** {engineer_name}
- **Next update:** within {update_window}

We will follow up in this thread with the next update. The incident channel is
`#inc-{workspace_short}-{date}`.

— NovaEdge Engineering

---

## 9. Lead Follow-up (sequence step 1)
**Subject:** Following up on {topic}

Hi {first_name},

Following up on our conversation about {topic}. The proposal we discussed is below for
quick reference: {one_line_pitch}.

If now isn't the right time, I'm happy to circle back next quarter — just let me know.

— {ae_name}

---

## 10. Out-of-Scope Decline (AI)
**Subject:** RE: {customer_subject}

Hi {first_name},

This question is outside what our AI assistant is configured to answer. I've forwarded it to
a human teammate. They'll be in touch within **{sla}**.

— NovaEdge Support

---

## Tone Guidelines (apply to all templates)
- Plain English, no jargon.
- Short sentences.
- Specific dates and amounts, never "shortly" or "soon".
- One clear next step at the end of every email.
- No exclamation points.
- No emojis.
- Sign-offs: "Best," for sales, "—" for support.
