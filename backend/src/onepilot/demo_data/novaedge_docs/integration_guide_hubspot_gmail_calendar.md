# Integration Guide — HubSpot, Gmail, Google Calendar

This guide describes how to connect a NovaEdge workspace to a customer's HubSpot account,
Gmail/Google Workspace, and Google Calendar. It is written for technical-leaning customers
and for the NovaEdge implementation team.

## Prerequisites
Before starting the integration, confirm:

- The customer is on a paid HubSpot plan (Starter or above) that allows custom integrations.
- The customer has a Google Workspace domain (not a personal `@gmail.com` account) for
  Gmail and Calendar.
- An admin in the customer's organization is available for the OAuth consent flow.
- The customer's NovaEdge workspace has at least the **Pro** plan (lower plans cannot use the
  HubSpot integration).

If any of these are missing, raise it in the discovery call. Do not attempt to integrate
against personal accounts in production.

## HubSpot Integration

### Step 1 — Create a Private App
1. In HubSpot, go to **Settings → Integrations → Private Apps**.
2. Click **Create a private app**.
3. Name it `NovaEdge AI Integration`.
4. Under **Scopes**, enable:
   - `crm.objects.contacts.read`, `crm.objects.contacts.write`
   - `crm.objects.companies.read`, `crm.objects.companies.write`
   - `crm.objects.deals.read`, `crm.objects.deals.write`
   - `crm.objects.owners.read`
   - `tickets`
   - `timeline`
5. Copy the **Access Token**.

### Step 2 — Connect in OnePilot
1. In the NovaEdge customer workspace, navigate to **Integrations → HubSpot**.
2. Paste the access token.
3. Click **Verify connection**. You should see the customer's portal ID and owner list.

### Step 3 — Map Fields
NovaEdge defaults to standard HubSpot contact and deal properties. If the customer uses
custom properties (e.g., a custom `lifecycle_stage_v2`), map them in the **Field Mapping**
screen. We support up to 30 custom property mappings on Pro and 100 on Team / Business.

### Step 4 — Verify Audit Trail
After connection, every CRM write produces an entry in the OnePilot audit log with
`resource_type = "hubspot_contact"` (or `deal` / `ticket`) and `actor = ai_agent` or
`actor = user`. Confirm at least one entry appears.

## Gmail Integration

### Step 1 — Domain-Wide Delegation (recommended)
For Google Workspace, the safest approach is **domain-wide delegation** of a service account:

1. In the customer's Google Cloud Console, create a service account.
2. Grant it the scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/gmail.send` (only if auto-send is enabled — usually
     it is not).
3. Have a Google Workspace super-admin authorize the client ID in the Admin Console under
   **Security → API controls → Domain-wide delegation**.

### Step 2 — Configure in OnePilot
1. Navigate to **Integrations → Gmail**.
2. Upload the service-account JSON.
3. Specify which mailboxes NovaEdge may impersonate. Typically: `support@`, `sales@`, and
   `hello@`.
4. Save and run the **connection test**.

### Step 3 — Define Reply Modes
For each mailbox, choose one of:

- **Draft only** — NovaEdge writes drafts, a human must send.
- **Reply with approval** — NovaEdge sends after one-click approval in OnePilot.
- **Auto-send** — fully automated. Disabled by default. Requires escalation policy review.

Auto-send is **never enabled** for refund requests, complaints, legal notices, or executive
email — even if the customer asks. See `escalation_policy.md`.

## Google Calendar Integration

### Step 1 — Reuse the Gmail Service Account
If you already configured Gmail with a service account, reuse it. Add the scope
`https://www.googleapis.com/auth/calendar.events` and reauthorize in the Admin Console.

### Step 2 — Connect Calendars
1. Navigate to **Integrations → Google Calendar**.
2. Add each calendar the booking assistant should read or write. Common patterns:
   - Read-only on the CEO calendar.
   - Read-write on a shared `Sales Demos` calendar.
3. Specify default meeting duration, buffer time, and time-of-day windows.

### Step 3 — Verify Time-Zone Handling
Run a smoke test: ask the AI to book a 30-minute slot for the customer's primary contact.
Confirm the invite appears in the correct calendar with the correct time zone for both
parties.

## Common Failures
- **"Insufficient permission"** in HubSpot — usually a missing scope on the private app.
  Recreate the app with the scopes above.
- **`invalid_grant`** in Gmail — the service account JSON is wrong or the domain-wide
  delegation was not authorized.
- **Calendar invites in UTC** — the impersonated user does not have a default time zone.
  Set it under the user's Google account preferences.

For any other integration issues, see `support_troubleshooting.md`.
