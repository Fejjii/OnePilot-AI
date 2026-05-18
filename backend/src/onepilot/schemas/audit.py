from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str
    detail: dict | None
    ip_address: str | None
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int


class UsageEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str | None
    feature: str
    model: str | None
    provider: str | None
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    fallback_used: bool
    tool_calls: int
    latency_ms: int
    created_at: datetime


class UsageEventListResponse(BaseModel):
    items: list[UsageEventResponse]
    total: int
