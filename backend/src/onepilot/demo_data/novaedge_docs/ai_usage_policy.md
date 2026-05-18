# NovaEdge Solutions — AI Usage Policy

This is the internal and customer-facing policy that defines what our AI agents are allowed
to do, what they must escalate, and how confidence is managed.

## Core Principles
1. **Augment, don't replace.** AI accelerates humans; it does not replace them where judgment
   or accountability is required.
2. **Grounded answers only.** AI responses to factual customer questions must be grounded in
   retrieved evidence. No free-floating "I think" answers.
3. **Confidence over coverage.** When confidence is low, the AI escalates. We prefer "I don't
   know" to a confident wrong answer.
4. **Auditable.** Every AI action that touches a customer system is logged with the input
   hash, output hash, model, latency, confidence, and any human override.

## Autonomy Levels
Each workflow runs in exactly one autonomy mode at a time:

- **Read-only.** AI can read but not write. Safe default during onboarding.
- **Draft-only.** AI produces drafts; a human sends.
- **Approval-required.** AI proposes an action; a human approves with one click.
- **Autonomous.** AI executes without approval.

A workflow can graduate from one mode to the next only with **written sign-off** from the
customer's named champion. The graduation is recorded in the audit log.

## Where Autonomy Is Forbidden
The following actions are **never autonomous**, regardless of customer request:

- Sending refund or credit communications.
- Replying to legal notices, GDPR / PIPEDA requests, or regulatory inquiries.
- Replying to executives at the customer or at the customer's customer (`founder@`, `ceo@`,
  `legal@`, etc.).
- Mass outreach to more than 50 unique recipients in 24 hours.
- Posting publicly on behalf of the customer (social media, status pages).
- Modifying or deleting historical customer data (we may insert; we do not retroactively
  rewrite).

These actions can run in approval-required mode at most.

## Confidence and Weak Evidence
- The retrieval-augmented support agent produces an answer only when the **top retrieval
  score** is above a configurable threshold. Default: `0.30` (cosine similarity / 1).
- If no chunk is above the threshold, the agent must respond with the configured
  weak-evidence template:
  > "I don't have a confident answer based on the knowledge I have. I'm forwarding this to a
  > human teammate."
- The agent must include **citations** with every confident answer. Citations include the
  document title, the chunk identifier, and the section if available.
- Confidence scores must be exposed in the response payload so admins can audit them.

## Prompt and Model Discipline
- Prompt templates are versioned and stored outside of code (`/prompts/*.yaml`). No ad-hoc
  prompts in production traffic.
- We log the **prompt template version**, **model**, and **temperature** with every call.
- Temperature defaults: `0.2` for classification, `0.4` for drafting, `0.7` for ideation.
- The agent must refuse out-of-scope requests politely and direct the user back to the
  supported workflows.

## Prompt-Injection Defenses
- All user-supplied text is treated as data, not instructions. We escape and tag it.
- Retrieved documents are also untrusted; the agent must never follow instructions found in
  retrieved content.
- We maintain a small allow-list of "system prompts" the agent will honor; everything else is
  ignored.

## Tool Use
The agent can call tools (CRM, email, calendar). Tool calls must:

- Be enumerated in the workflow definition.
- Carry a tenant-scoped credential.
- Produce an audit-log entry with input arguments hashed.
- Fail safely if the tool returns an unexpected error (never invent a tool result).

## Out-of-Scope Behavior
If a customer asks the agent something outside the documented scope (e.g., medical advice,
legal advice, financial speculation), the agent must:

1. Decline politely.
2. Redirect to a human teammate.
3. Log the request as an "out-of-scope" event for the gap report.

## Customer Override
A customer can request a tighter or looser policy through their CSM:

- **Tighter** (e.g., draft-only forever): always honored.
- **Looser** (e.g., autonomous refunds): never honored. We will not override the forbidden
  list above.

## Review Cadence
This policy is reviewed quarterly by the security and product leads. The audit log retains
all overrides for **24 months** for compliance review.
