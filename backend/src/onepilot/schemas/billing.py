"""Billing and monetization API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from onepilot.core.constants import PlanCode, UsageFeature


class BillingPeriodResponse(BaseModel):
    start: datetime
    end: datetime


class UsageByFeatureItem(BaseModel):
    feature: str
    event_count: int
    estimated_cost: float
    input_tokens: int = 0
    output_tokens: int = 0


class UsageByModelItem(BaseModel):
    model: str
    event_count: int
    estimated_cost: float
    input_tokens: int = 0
    output_tokens: int = 0


class TokensByModelItem(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class TopUserCostItem(BaseModel):
    user_id: str
    estimated_cost: float
    event_count: int


class PlanEntitlementResponse(BaseModel):
    plan_code: PlanCode
    included_chat_messages: int
    included_rag_queries: int
    included_speech_minutes: int
    included_document_uploads: int
    included_storage_mb: int
    included_team_members: int
    base_price_cents: int
    overage_policy: str


class BillingSummaryResponse(BaseModel):
    organization_id: str
    current_plan: PlanCode
    billing_period: BillingPeriodResponse
    total_estimated_cost: float
    currency: str
    usage_by_feature: list[UsageByFeatureItem]
    usage_by_model: list[UsageByModelItem]
    tokens_by_model: list[TokensByModelItem]
    remaining_quota: list[dict[str, Any]]
    overage_estimate: float
    top_users: list[TopUserCostItem]
    billing_provider_mode: str
    mock_mode: bool


class InvoiceLineItem(BaseModel):
    description: str
    quantity: float | int = 1
    unit_amount_cents: int = 0
    amount_cents: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class InvoicePreviewResponse(BaseModel):
    organization_id: str
    plan_code: PlanCode
    billing_period: BillingPeriodResponse
    base_plan_price_cents: int
    estimated_usage_cost: float
    estimated_overage_cost: float
    total_estimated_due_cents: int
    currency: str
    line_items: list[InvoiceLineItem]
    mock_stripe: bool
    provider_status: str


class BillingUsageResponse(BaseModel):
    organization_id: str
    billing_period: BillingPeriodResponse
    events: list[dict[str, Any]]
    total: int
    total_estimated_cost: float


class BillingPlansResponse(BaseModel):
    current_plan: PlanCode
    entitlements: PlanEntitlementResponse
    available_plans: list[dict[str, Any]]
