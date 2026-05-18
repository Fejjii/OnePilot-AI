"""Tests for deterministic demo data generation."""

from __future__ import annotations

from onepilot.demo_data.generators import (
    DEFAULT_ORG_ID,
    generate_appointments,
    generate_approval_examples,
    generate_audit_logs,
    generate_conversations,
    generate_customers,
    generate_demo_dataset,
    generate_email_examples,
    generate_leads,
    generate_support_tickets,
    generate_usage_events,
)


class TestGeneratorsAreDeterministic:
    def test_leads_are_deterministic_with_same_seed(self) -> None:
        a = generate_leads(count=20, seed=42)
        b = generate_leads(count=20, seed=42)
        assert a == b

    def test_different_seed_changes_output(self) -> None:
        a = generate_leads(count=20, seed=42)
        b = generate_leads(count=20, seed=7)
        assert a != b

    def test_full_dataset_is_deterministic(self) -> None:
        ds1 = generate_demo_dataset(scale=0.1, seed=42)
        ds2 = generate_demo_dataset(scale=0.1, seed=42)
        assert ds1.total_records == ds2.total_records
        assert ds1.leads == ds2.leads
        assert ds1.customers == ds2.customers


class TestGeneratorsProduceExpectedShape:
    def test_lead_has_core_fields(self) -> None:
        leads = generate_leads(count=3)
        assert len(leads) == 3
        first = leads[0]
        for key in (
            "id",
            "organization_id",
            "full_name",
            "email",
            "phone",
            "company",
            "company_size",
            "stage",
            "qualified",
            "created_at",
        ):
            assert key in first
        assert first["organization_id"] == DEFAULT_ORG_ID

    def test_customer_has_plan_and_status(self) -> None:
        customers = generate_customers(count=5)
        assert len(customers) == 5
        for c in customers:
            assert c["plan_code"] in {"free", "pro", "team", "business"}
            assert c["status"] in {"active", "trial", "churned", "past_due"}

    def test_support_tickets_reference_customers(self) -> None:
        customers = generate_customers(count=8)
        tickets = generate_support_tickets(count=20, customers=customers)
        customer_ids = {c["id"] for c in customers}
        assert all(t["customer_id"] in customer_ids for t in tickets)

    def test_conversations_have_escalation_when_not_resolved(self) -> None:
        conversations = generate_conversations(count=40)
        for conv in conversations:
            if conv["ai_resolved"]:
                assert conv["escalation_reason"] is None
            else:
                assert conv["escalation_reason"]

    def test_appointments_have_future_or_past_window(self) -> None:
        appointments = generate_appointments(count=15)
        for appt in appointments:
            assert appt["duration_minutes"] in {30, 45, 60}
            assert appt["source"] in {"booking_bot", "manual"}

    def test_emails_have_intent(self) -> None:
        emails = generate_email_examples(count=10)
        assert all("intent" in e for e in emails)
        assert all(e["direction"] in {"inbound", "outbound"} for e in emails)

    def test_usage_events_have_tokens(self) -> None:
        events = generate_usage_events(count=25)
        # Token counts must be non-negative.
        assert all(e["input_tokens"] >= 0 and e["output_tokens"] >= 0 for e in events)

    def test_approval_examples_have_resolved_states(self) -> None:
        approvals = generate_approval_examples(count=15)
        assert all(
            a["status"] in {"pending", "approved", "rejected", "needs_more_info"}
            for a in approvals
        )

    def test_audit_logs_have_resource_type(self) -> None:
        logs = generate_audit_logs(count=10)
        assert all(log["resource_type"] for log in logs)
        assert all(log["organization_id"] == DEFAULT_ORG_ID for log in logs)


class TestDemoDatasetAggregate:
    def test_dataset_obeys_scale(self) -> None:
        ds = generate_demo_dataset(scale=0.1)
        # ~ 10% of the defaults; leads default is 200 → expect 20.
        assert 15 <= len(ds.leads) <= 25
        assert ds.total_records > 0
        assert ds.organization_id == DEFAULT_ORG_ID
