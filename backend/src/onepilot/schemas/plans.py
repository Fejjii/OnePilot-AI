from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from onepilot.core.constants import PlanCode, SubscriptionStatus


class PlanLimits(BaseModel):
    chat_messages: int
    rag_queries: int
    document_uploads: int
    storage_mb: int
    email_drafts: int
    lead_workflows: int
    tool_calls: int
    users: int


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: PlanCode
    name: str
    monthly_price_cents: int
    limits: PlanLimits


class SubscriptionResponse(BaseModel):
    id: str
    organization_id: str
    plan_code: PlanCode
    status: SubscriptionStatus
    started_at: datetime
    renews_at: datetime | None


class CurrentPlanResponse(BaseModel):
    plan: PlanResponse
    subscription: SubscriptionResponse
