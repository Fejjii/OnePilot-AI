# Usage-Based Billing & Monetization

OnePilot AI records per-call usage events and estimates token costs for a SaaS monetization layer. **No real payments are collected** — billing runs against a simulated Stripe integration.

## What Is Implemented

- **Central cost calculator** (`backend/src/onepilot/services/cost_calculator.py`) driven by `backend/src/onepilot/core/pricing_config.py`
- **Usage event enrichment** on record: estimated cost, provider, model, fallback flag, cost breakdown in event metadata
- **Billing API** (organization-scoped, JWT required):
  - `GET /billing/summary` — plan, period totals, usage by feature/model, quotas, top users
  - `GET /billing/usage` — period usage events with costs
  - `GET /billing/invoice-preview` — line items and estimated due
  - `GET /billing/plans` — entitlements and available tiers
- **Plan entitlements** for Free, Pro, Team, Business (included limits + base price)
- **Mock Stripe provider** — checkout, portal, invoice preview (in-memory)
- **Frontend** — Usage & Admin page shows estimated cost, invoice preview, model/feature cost breakdown, mock billing banner

## What Is Mocked

| Piece | Behavior |
|-------|----------|
| Stripe | `MockStripeProvider` unless `STRIPE_SECRET_KEY` is set (real `StripeProvider` methods still raise `NotImplementedError`) |
| Payments | No charges, no card storage, no webhooks |
| Overage | Policy placeholder; quotas still **block** at limit via `QuotaExceededError` |
| Prices | Static table — **verify against OpenAI/provider pricing before production** |

## How Costs Are Estimated

1. On `usage_service.record()`, if `estimated_cost` is omitted, `calculate_usage_cost()` runs.
2. Token models use per-1M input/output rates from `MODEL_TOKEN_PRICES`.
3. Speech uses `SPEECH_PRICE_PER_MINUTE` (e.g. whisper-1).
4. RAG queries / document uploads may add small flat feature costs when no token cost applies.
5. Tool calls add a per-call flat estimate.
6. **Fallback providers cost $0** (`fallback_used` or provider name contains `fallback` / `mock`).

Breakdown is stored in `event_metadata.cost_breakdown` with `price_source` and `currency`.

## Connecting Stripe Later

1. Implement `StripeProvider` methods against Stripe API (customers, subscriptions, checkout, portal).
2. Map `organization_id` → Stripe `customer_id` in Postgres.
3. Add webhook route for `invoice.paid`, `customer.subscription.updated`, etc.
4. Sync `Subscription.plan_code` from Stripe subscription items.
5. Keep **estimated** usage costs in `usage_events`; reconcile with Stripe metered billing or internal ledger as needed.
6. Set `STRIPE_SECRET_KEY` in production; diagnostics will show live mode when implemented.

## Privacy & Security

- Do not log API keys or payment methods.
- Billing endpoints use the same JWT + `organization_id` isolation as the rest of the API.
- Invoice preview and summaries are estimates only — not legal invoices.
- Admin usage event lists remain role-gated (`owner` / `admin`).

## Limitations

- No payment blocking beyond existing quota checks.
- No tax, proration, or multi-currency.
- Calendar-month aggregation only (no custom billing cycles).
- `total_estimated_cost` on `/usage/summary` aggregates DB events for the current month; admin event table may show a paginated subset.

See also `docs/limitations_roadmap.md`.
