# Demo Data

This package owns the fictional **NovaEdge Solutions** demo data used by tests and the
guided demo flow.

## Knowledge Base Documents (`novaedge_docs/`)
Nineteen Markdown documents that describe NovaEdge end-to-end:

1. `company_profile.md`
2. `services_overview.md`
3. `pricing_plans.md`
4. `sales_playbook.md`
5. `objection_handling.md`
6. `integration_guide_hubspot_gmail_calendar.md`
7. `customer_faq.md`
8. `support_troubleshooting.md`
9. `escalation_policy.md`
10. `refund_policy.md`
11. `onboarding_guide.md`
12. `customer_success_sop.md`
13. `data_privacy_policy.md`
14. `ai_usage_policy.md`
15. `security_policy.md`
16. `email_templates.md`
17. `discovery_call_script.md`
18. `demo_call_checklist.md`
19. `sample_meeting_notes.md`

## Deterministic Generators (`generators.py`)
Each generator accepts a `seed` argument and returns a list of plain dictionaries
representing one entity type. The default seed is `42`.

- `generate_leads(count=200)`
- `generate_customers(count=75)`
- `generate_support_tickets(count=200, customers=...)`
- `generate_conversations(count=100)`
- `generate_email_examples(count=50)`
- `generate_appointments(count=30)`
- `generate_usage_events(count=300)`
- `generate_approval_examples(count=20)`
- `generate_audit_logs(count=150)`

`generate_demo_dataset(scale=1.0, seed=42)` returns a `DemoDataset` aggregating all of
the above. Use a smaller `scale` (e.g. `0.1`) in tests for speed.

## Seeder (`seed.py`)
`seed_knowledge_base(...)` ingests the 19 Markdown documents into the principal's
organization via `services.document_service.upload_document`. It is **idempotent**:
re-running the seeder skips documents that are already present (matched by filename).

`seed_operational_data(...)` seeds **12 curated leads**, **8 approvals** (including
pending items), **40 usage events**, and **25 audit logs** when the org has no leads
yet. Also idempotent.

The same flow is exposed via the API at `POST /demo/seed` (admin-only).

**Demo login:** `admin@onepilot.ai` / `Demo1234!`
