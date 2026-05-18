from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    company: str | None = None
    source: str | None = None
    urgency: str = "medium"
    intent: str | None = None
    pain_point: str | None = None
    summary: str | None = None
    recommended_next_action: str | None = None
    status: str = "new"


class LeadUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    company: str | None = None
    source: str | None = None
    urgency: str | None = None
    intent: str | None = None
    pain_point: str | None = None
    summary: str | None = None
    recommended_next_action: str | None = None
    status: str | None = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    company: str | None
    email: str | None
    status: str
    source: str | None
    urgency: str
    intent: str | None
    pain_point: str | None
    summary: str | None
    recommended_next_action: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
