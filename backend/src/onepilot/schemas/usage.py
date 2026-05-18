from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from onepilot.core.constants import PlanCode, UsageFeature


class UsageEventCreate(BaseModel):
    feature: UsageFeature
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    provider: str | None = None
    fallback_used: bool = False
    tool_calls: int = 0
    latency_ms: int = 0


class UsageQuotaResponse(BaseModel):
    feature: UsageFeature
    used: int
    limit: int
    remaining: int
    period_start: datetime
    period_end: datetime


class UsageSummaryResponse(BaseModel):
    organization_id: str
    plan_code: PlanCode
    quotas: list[UsageQuotaResponse]
    total_estimated_cost: float
