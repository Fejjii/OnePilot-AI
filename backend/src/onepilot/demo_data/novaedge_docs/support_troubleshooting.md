# NovaEdge Solutions — Support Troubleshooting Guide

This guide is for the NovaEdge support team and senior customer admins. It covers the most
common runtime issues and the right first-line responses.

## Triage Checklist
For every customer report, capture:

1. Customer workspace ID (`org_*`).
2. Affected workflow (Inbox Triage, Support Agent, Lead Qualifier, Appointment Booker).
3. First time the problem was observed.
4. Whether the issue is partial (one mailbox / one channel) or full (whole workspace).
5. Recent changes: new integrations, prompt updates, model swaps.

Without these five fields, do **not** open an internal ticket. Ask the customer first.

## Symptom: RAG Agent Returns "I don't have a confident answer"
### Likely causes
- Knowledge base is incomplete or stale.
- Confidence threshold is set too high.
- Embeddings index is empty for the customer's tenant.

### Checks
- Confirm `documents` table contains at least one ingested document for the workspace.
- Run a manual semantic search via the OnePilot console (`/knowledge/search`) with a known
  test query. If results are empty, re-index.
- Lower the confidence threshold from `0.30` to `0.20` and observe.

### Fixes
- Trigger a full re-embed: `POST /demo/seed?reindex=true` is the demo equivalent; in
  production, use the customer's knowledge-base sync job.
- If the knowledge base is genuinely missing content, file an internal "knowledge gap" ticket
  and notify the customer's owner — do not let the bot guess.

## Symptom: Email Drafts Are Empty or Truncated
### Likely causes
- LLM provider rate limit hit (HTTP 429 from OpenAI).
- Prompt template was edited and includes an unresolved placeholder.
- Customer's email body contains too much HTML / attachments.

### Checks
- Look at the `usage_events` table for recent `fallback_used = true` entries.
- Inspect the latest prompt template version.
- Re-run the failing email through the **single-message replay** tool.

### Fixes
- Switch the workflow to `fallback_model` temporarily.
- Re-publish the prompt template after fixing placeholders.
- For long HTML bodies, enable the `strip_html_in_summarize` workflow flag.

## Symptom: Calendar Invites in the Wrong Time Zone
### Likely causes
- Impersonated Google user has no default time zone.
- Booking workflow uses UTC instead of the prospect's locale.

### Fixes
- Set the user's default time zone in their Google account.
- In the workflow config, change `default_timezone` from `UTC` to `{{prospect.timezone}}`.

## Symptom: HubSpot Sync Stops
### Likely causes
- HubSpot private app token expired or was rotated.
- HubSpot API rate limit hit.
- A new required scope was added on our side.

### Checks
- Test the token via HubSpot's API explorer.
- Look at the OnePilot integration health page — every connector exposes a status row.

### Fixes
- Rotate the token. Update it in the **Integrations → HubSpot** settings.
- Adjust the polling interval from 1 minute to 5 minutes if rate-limited.

## Symptom: Authentication Errors / 401s in API
### Likely causes
- Customer's API token expired.
- Customer is targeting a different workspace than they think (multi-org user).
- Clock skew on a self-hosted Enterprise deployment.

### Fixes
- Have the customer re-issue an API token from **Settings → API**.
- Confirm the `X-Organization-Id` header matches the user's primary workspace.
- For Enterprise self-hosted, confirm NTP is functioning.

## Symptom: Slow Responses (> 5s p95)
### Likely causes
- Cold start on the embedding model.
- Cross-region latency on a misconfigured tenant.
- Large retrieval (`top_k > 50`).

### Fixes
- Cap `top_k` to 10 unless the customer has a justified reason.
- Confirm the tenant region matches the customer's primary region.
- Check OpenAI status; switch to fallback provider if degraded.

## When To Escalate to Engineering
- Any P1 (full service down for a workspace).
- Any data-loss suspicion.
- Any audit-log discrepancy.
- Anything you cannot reproduce after 30 minutes of investigation.

See `escalation_policy.md` for SLAs and on-call rotation.
