"""Initial schema: organizations, users, members, plans, subscriptions, usage_quotas

Revision ID: 0001
Revises: None
Create Date: 2026-05-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PLAN_SEEDS = [
    {
        "code": "free",
        "name": "Free",
        "monthly_price_cents": 0,
        "limits": '{"chat_messages": 50, "rag_queries": 20, "document_uploads": 5, "storage_mb": 100, "email_drafts": 10, "lead_workflows": 5, "tool_calls": 30, "users": 1}',
    },
    {
        "code": "pro",
        "name": "Pro",
        "monthly_price_cents": 2900,
        "limits": '{"chat_messages": 500, "rag_queries": 200, "document_uploads": 50, "storage_mb": 1000, "email_drafts": 100, "lead_workflows": 50, "tool_calls": 300, "users": 1}',
    },
    {
        "code": "team",
        "name": "Team",
        "monthly_price_cents": 7900,
        "limits": '{"chat_messages": 2000, "rag_queries": 1000, "document_uploads": 200, "storage_mb": 5000, "email_drafts": 500, "lead_workflows": 200, "tool_calls": 1000, "users": 10}',
    },
    {
        "code": "business",
        "name": "Business",
        "monthly_price_cents": 19900,
        "limits": '{"chat_messages": 10000, "rag_queries": 5000, "document_uploads": 1000, "storage_mb": 25000, "email_drafts": 2000, "lead_workflows": 1000, "tool_calls": 5000, "users": 50}',
    },
]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "organization_members",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("organization_id", sa.String(64), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
    op.create_index("ix_org_members_org_id", "organization_members", ["organization_id"])
    op.create_index("ix_org_members_user_id", "organization_members", ["user_id"])

    op.create_table(
        "plans",
        sa.Column("code", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("monthly_price_cents", sa.Integer(), default=0),
        sa.Column("limits", sa.JSON(), nullable=False),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("organization_id", sa.String(64), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("plan_code", sa.String(20), sa.ForeignKey("plans.code"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("renews_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_org_id", "subscriptions", ["organization_id"])

    op.create_table(
        "usage_quotas",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("organization_id", sa.String(64), nullable=False),
        sa.Column("feature", sa.String(50), nullable=False),
        sa.Column("used", sa.Integer(), default=0),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "feature", "period_start", name="uq_org_feature_period"),
    )
    op.create_index("ix_usage_quotas_org_id", "usage_quotas", ["organization_id"])

    plans_table = sa.table(
        "plans",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("monthly_price_cents", sa.Integer),
        sa.column("limits", sa.JSON),
    )
    for seed in PLAN_SEEDS:
        insert_sql = sa.text("""INSERT INTO plans (code, name, monthly_price_cents, limits) VALUES (:code, :name, :monthly_price_cents, CAST(:limits AS JSON)) ON CONFLICT (code) DO NOTHING""")
        op.execute(insert_sql.bindparams(**seed))


def downgrade() -> None:
    op.drop_table("usage_quotas")
    op.drop_table("subscriptions")
    op.drop_table("plans")
    op.drop_table("organization_members")
    op.drop_table("users")
    op.drop_table("organizations")
