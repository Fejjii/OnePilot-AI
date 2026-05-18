"""Deterministic generators for fictional NovaEdge demo data.

All generators accept a `seed` argument so the output is reproducible.
The default seed (`42`) produces the canonical dataset used for tests and the demo.

These generators produce plain dictionaries rather than ORM objects so they can be
consumed by tests, scripts, or seeded into the database via :mod:`demo_data.seed`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final

from faker import Faker

DEFAULT_SEED: Final[int] = 42
DEFAULT_ORG_ID: Final[str] = "org_demo_onepilot"
DEFAULT_USER_ID: Final[str] = "usr_demo_admin"

_INDUSTRIES: Final[tuple[str, ...]] = (
    "B2B SaaS",
    "Professional Services",
    "Healthcare",
    "Real Estate",
    "E-commerce",
    "Education",
    "FinTech",
    "Marketing Agency",
    "Legal",
    "Manufacturing",
)
_LEAD_SOURCES: Final[tuple[str, ...]] = (
    "website",
    "referral",
    "linkedin",
    "outbound_email",
    "conference",
    "partner",
    "demo_request",
)
_LEAD_STAGES: Final[tuple[str, ...]] = (
    "mql",
    "sql",
    "discovery",
    "scoping",
    "negotiation",
    "closed_won",
    "closed_lost",
)
_PLAN_CODES: Final[tuple[str, ...]] = ("free", "pro", "team", "business")
_TICKET_CHANNELS: Final[tuple[str, ...]] = ("email", "chat", "slack", "phone")
_TICKET_PRIORITIES: Final[tuple[str, ...]] = ("P1", "P2", "P3", "P4")
_TICKET_STATUSES: Final[tuple[str, ...]] = ("open", "in_progress", "resolved", "escalated")
_EMAIL_INTENTS: Final[tuple[str, ...]] = (
    "support",
    "sales",
    "billing",
    "scheduling",
    "complaint",
    "renewal",
)
_USAGE_FEATURES: Final[tuple[str, ...]] = (
    "chat_messages",
    "rag_queries",
    "document_uploads",
    "email_drafts",
    "lead_workflows",
    "tool_calls",
)
_USAGE_MODELS: Final[tuple[str, ...]] = (
    "gpt-4o-mini",
    "gpt-4o",
    "claude-3-5-sonnet",
    "text-embedding-3-small",
)
_APPROVAL_ACTIONS: Final[tuple[str, ...]] = (
    "send_email_reply",
    "create_calendar_event",
    "issue_refund",
    "update_crm_deal",
    "share_external_link",
)
_APPROVAL_STATUSES: Final[tuple[str, ...]] = (
    "pending",
    "approved",
    "rejected",
    "needs_more_info",
)
_AUDIT_ACTIONS: Final[tuple[str, ...]] = (
    "document.uploaded",
    "document.deleted",
    "knowledge.searched",
    "knowledge.answered",
    "approval.requested",
    "approval.decided",
    "integration.connected",
    "user.invited",
)
_AUDIT_RESOURCE_TYPES: Final[tuple[str, ...]] = (
    "document",
    "knowledge_query",
    "approval",
    "integration",
    "user",
)


def _build_faker(seed: int, offset: int) -> Faker:
    fake = Faker(["en_US", "en_CA"])
    fake.seed_instance(seed + offset)
    return fake


def _build_rng(seed: int, offset: int) -> random.Random:
    return random.Random(seed + offset)


def _iso_window(rng: random.Random, *, days_back: int) -> datetime:
    """Return a deterministic timestamp within the last `days_back` days."""
    base = datetime(2026, 5, 1, tzinfo=UTC)
    delta = timedelta(
        seconds=rng.randint(0, days_back * 24 * 3600),
    )
    return base - delta


def generate_leads(
    count: int = 200,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
) -> list[dict]:
    fake = _build_faker(seed, 1)
    rng = _build_rng(seed, 1)
    leads: list[dict] = []
    for i in range(count):
        company = fake.company()
        full_name = fake.name()
        email = fake.unique.company_email()
        stage = rng.choice(_LEAD_STAGES)
        qualified = stage not in ("mql", "closed_lost")
        leads.append(
            {
                "id": f"lead_{i + 1:05d}",
                "organization_id": organization_id,
                "full_name": full_name,
                "email": email,
                "phone": fake.phone_number(),
                "company": company,
                "company_size": rng.randint(5, 350),
                "industry": rng.choice(_INDUSTRIES),
                "role": fake.job(),
                "source": rng.choice(_LEAD_SOURCES),
                "score": rng.randint(0, 100),
                "stage": stage,
                "qualified": qualified,
                "created_at": _iso_window(rng, days_back=90),
                "notes": fake.sentence(nb_words=14),
            }
        )
    return leads


def generate_customers(
    count: int = 75,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
) -> list[dict]:
    fake = _build_faker(seed, 2)
    rng = _build_rng(seed, 2)
    customers: list[dict] = []
    for i in range(count):
        plan_code = rng.choice(_PLAN_CODES)
        mrr = {"free": 0, "pro": 29, "team": 79, "business": 199}[plan_code]
        status = rng.choices(
            ["active", "trial", "churned", "past_due"],
            weights=[78, 8, 10, 4],
        )[0]
        customers.append(
            {
                "id": f"cust_{i + 1:05d}",
                "organization_id": organization_id,
                "company_name": fake.company(),
                "contact_name": fake.name(),
                "contact_email": fake.unique.company_email(),
                "industry": rng.choice(_INDUSTRIES),
                "country": rng.choice(["US", "CA", "GB", "DE", "FR", "AU"]),
                "plan_code": plan_code,
                "mrr_usd": mrr,
                "status": status,
                "started_at": _iso_window(rng, days_back=365),
                "csm": rng.choice(["Priya Iyer", "Owen MacLean", "Erin Sato", "Sam Diallo"]),
            }
        )
    return customers


def generate_support_tickets(
    count: int = 200,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
    customers: list[dict] | None = None,
) -> list[dict]:
    fake = _build_faker(seed, 3)
    rng = _build_rng(seed, 3)
    customer_ids = (
        [c["id"] for c in customers]
        if customers
        else [f"cust_{i + 1:05d}" for i in range(75)]
    )
    tickets: list[dict] = []
    for i in range(count):
        priority = rng.choices(_TICKET_PRIORITIES, weights=[5, 15, 50, 30])[0]
        status = rng.choices(_TICKET_STATUSES, weights=[20, 25, 45, 10])[0]
        ai_handled = status == "resolved" and rng.random() < 0.6
        tickets.append(
            {
                "id": f"tkt_{i + 1:05d}",
                "organization_id": organization_id,
                "customer_id": rng.choice(customer_ids),
                "subject": fake.sentence(nb_words=6).rstrip("."),
                "body": fake.paragraph(nb_sentences=4),
                "channel": rng.choice(_TICKET_CHANNELS),
                "priority": priority,
                "status": status,
                "ai_handled": ai_handled,
                "escalated": status == "escalated",
                "created_at": _iso_window(rng, days_back=60),
            }
        )
    return tickets


def generate_conversations(
    count: int = 100,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
) -> list[dict]:
    fake = _build_faker(seed, 4)
    rng = _build_rng(seed, 4)
    conversations: list[dict] = []
    for i in range(count):
        message_count = rng.randint(2, 18)
        ai_resolved = rng.random() < 0.55
        conversations.append(
            {
                "id": f"conv_{i + 1:05d}",
                "organization_id": organization_id,
                "channel": rng.choice(("chat", "email", "slack")),
                "started_at": _iso_window(rng, days_back=30),
                "ended_at": _iso_window(rng, days_back=29),
                "message_count": message_count,
                "ai_resolved": ai_resolved,
                "escalation_reason": (
                    None
                    if ai_resolved
                    else rng.choice(
                        [
                            "weak_evidence",
                            "policy_forbids_autonomous",
                            "customer_requested_human",
                            "tool_failure",
                        ]
                    )
                ),
                "topic": rng.choice(
                    [
                        "pricing",
                        "onboarding",
                        "billing",
                        "integration_help",
                        "feature_request",
                        "refund_request",
                        "renewal",
                    ]
                ),
                "summary": fake.sentence(nb_words=12),
            }
        )
    return conversations


def generate_email_examples(
    count: int = 50,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
) -> list[dict]:
    fake = _build_faker(seed, 5)
    rng = _build_rng(seed, 5)
    emails: list[dict] = []
    for i in range(count):
        ai_drafted = rng.random() < 0.7
        intent = rng.choice(_EMAIL_INTENTS)
        emails.append(
            {
                "id": f"email_{i + 1:05d}",
                "organization_id": organization_id,
                "direction": rng.choice(("inbound", "outbound")),
                "from_email": fake.email(),
                "to_email": fake.email(),
                "subject": fake.sentence(nb_words=5).rstrip("."),
                "body_snippet": fake.paragraph(nb_sentences=2),
                "intent": intent,
                "ai_drafted": ai_drafted,
                "status": rng.choice(("draft", "sent", "needs_review", "scheduled")),
                "created_at": _iso_window(rng, days_back=21),
            }
        )
    return emails


def generate_appointments(
    count: int = 30,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
) -> list[dict]:
    fake = _build_faker(seed, 6)
    rng = _build_rng(seed, 6)
    appointments: list[dict] = []
    base = datetime(2026, 5, 12, 9, 0, tzinfo=UTC)
    for i in range(count):
        scheduled_at = base + timedelta(
            days=rng.randint(-7, 30),
            minutes=rng.choice([0, 15, 30, 45]) + 60 * rng.randint(0, 8),
        )
        appointments.append(
            {
                "id": f"appt_{i + 1:05d}",
                "organization_id": organization_id,
                "title": rng.choice(
                    [
                        "Discovery Call",
                        "Pilot Kickoff",
                        "QBR",
                        "Renewal Review",
                        "Technical Deep Dive",
                    ]
                ),
                "attendees": [fake.email(), fake.email()],
                "scheduled_at": scheduled_at,
                "duration_minutes": rng.choice([30, 45, 60]),
                "source": rng.choices(
                    ["booking_bot", "manual"], weights=[70, 30]
                )[0],
                "status": rng.choices(
                    ["scheduled", "completed", "cancelled", "no_show"],
                    weights=[55, 30, 10, 5],
                )[0],
                "confirmed": rng.random() < 0.85,
            }
        )
    return appointments


def generate_usage_events(
    count: int = 300,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
    user_id: str = DEFAULT_USER_ID,
) -> list[dict]:
    rng = _build_rng(seed, 7)
    events: list[dict] = []
    for i in range(count):
        feature = rng.choice(_USAGE_FEATURES)
        model = rng.choice(_USAGE_MODELS) if feature != "document_uploads" else None
        input_tokens = rng.randint(50, 1800) if model else 0
        output_tokens = rng.randint(20, 900) if model else 0
        fallback_used = rng.random() < 0.18
        events.append(
            {
                "id": f"uev_{i + 1:05d}",
                "organization_id": organization_id,
                "user_id": user_id,
                "feature": feature,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": round(
                    (input_tokens + output_tokens) * 0.0000045, 6
                ),
                "fallback_used": fallback_used,
                "latency_ms": rng.randint(120, 4200),
                "tool_calls": rng.choices([0, 0, 0, 1, 2, 3], weights=[60, 10, 5, 10, 10, 5])[0],
                "created_at": _iso_window(rng, days_back=30),
            }
        )
    return events


def generate_approval_examples(
    count: int = 20,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
) -> list[dict]:
    fake = _build_faker(seed, 8)
    rng = _build_rng(seed, 8)
    approvals: list[dict] = []
    for i in range(count):
        status = rng.choices(_APPROVAL_STATUSES, weights=[35, 45, 12, 8])[0]
        requested_at = _iso_window(rng, days_back=14)
        decided_at = (
            None if status == "pending" else requested_at + timedelta(hours=rng.randint(1, 24))
        )
        approvals.append(
            {
                "id": f"app_{i + 1:05d}",
                "organization_id": organization_id,
                "action_type": rng.choice(_APPROVAL_ACTIONS),
                "status": status,
                "summary": fake.sentence(nb_words=10),
                "requester": fake.name(),
                "approver": fake.name() if status != "pending" else None,
                "requested_at": requested_at,
                "decided_at": decided_at,
            }
        )
    return approvals


def generate_audit_logs(
    count: int = 150,
    *,
    seed: int = DEFAULT_SEED,
    organization_id: str = DEFAULT_ORG_ID,
    user_id: str = DEFAULT_USER_ID,
) -> list[dict]:
    fake = _build_faker(seed, 9)
    rng = _build_rng(seed, 9)
    logs: list[dict] = []
    for i in range(count):
        action = rng.choice(_AUDIT_ACTIONS)
        resource_type, _, _ = action.partition(".")
        if resource_type not in _AUDIT_RESOURCE_TYPES:
            resource_type = "system"
        logs.append(
            {
                "id": f"aud_{i + 1:05d}",
                "organization_id": organization_id,
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": f"{resource_type[:3]}_{rng.randint(1, 9999):05d}",
                "detail": {"summary": fake.sentence(nb_words=8)},
                "ip_address": fake.ipv4_public(),
                "created_at": _iso_window(rng, days_back=30),
            }
        )
    return logs


@dataclass
class DemoDataset:
    """Aggregate container for a deterministic demo dataset."""

    organization_id: str
    seed: int
    leads: list[dict] = field(default_factory=list)
    customers: list[dict] = field(default_factory=list)
    support_tickets: list[dict] = field(default_factory=list)
    conversations: list[dict] = field(default_factory=list)
    email_examples: list[dict] = field(default_factory=list)
    appointments: list[dict] = field(default_factory=list)
    usage_events: list[dict] = field(default_factory=list)
    approval_examples: list[dict] = field(default_factory=list)
    audit_logs: list[dict] = field(default_factory=list)

    @property
    def total_records(self) -> int:
        return sum(
            len(group)
            for group in (
                self.leads,
                self.customers,
                self.support_tickets,
                self.conversations,
                self.email_examples,
                self.appointments,
                self.usage_events,
                self.approval_examples,
                self.audit_logs,
            )
        )


def generate_demo_dataset(
    *,
    organization_id: str = DEFAULT_ORG_ID,
    user_id: str = DEFAULT_USER_ID,
    seed: int = DEFAULT_SEED,
    scale: float = 1.0,
) -> DemoDataset:
    """Generate a full, deterministic demo dataset for NovaEdge.

    `scale` linearly resizes every collection. Use `scale=0.1` in tests to keep
    them fast while preserving determinism.
    """
    if scale <= 0:
        raise ValueError("scale must be positive")

    def s(n: int) -> int:
        return max(1, int(round(n * scale)))

    customers = generate_customers(s(75), seed=seed, organization_id=organization_id)
    return DemoDataset(
        organization_id=organization_id,
        seed=seed,
        leads=generate_leads(s(200), seed=seed, organization_id=organization_id),
        customers=customers,
        support_tickets=generate_support_tickets(
            s(200), seed=seed, organization_id=organization_id, customers=customers
        ),
        conversations=generate_conversations(s(100), seed=seed, organization_id=organization_id),
        email_examples=generate_email_examples(
            s(50), seed=seed, organization_id=organization_id
        ),
        appointments=generate_appointments(s(30), seed=seed, organization_id=organization_id),
        usage_events=generate_usage_events(
            s(300), seed=seed, organization_id=organization_id, user_id=user_id
        ),
        approval_examples=generate_approval_examples(
            s(20), seed=seed, organization_id=organization_id
        ),
        audit_logs=generate_audit_logs(
            s(150), seed=seed, organization_id=organization_id, user_id=user_id
        ),
    )


__all__ = [
    "DEFAULT_ORG_ID",
    "DEFAULT_SEED",
    "DEFAULT_USER_ID",
    "DemoDataset",
    "generate_appointments",
    "generate_approval_examples",
    "generate_audit_logs",
    "generate_conversations",
    "generate_customers",
    "generate_demo_dataset",
    "generate_email_examples",
    "generate_leads",
    "generate_support_tickets",
    "generate_usage_events",
]
