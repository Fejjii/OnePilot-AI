from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from onepilot.core.constants import ApprovalStatus


class ApprovalRequestCreate(BaseModel):
    action_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    proposed_payload: dict = Field(default_factory=dict)
    risk_level: str = "medium"
    reason: str = ""


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    action_type: str
    title: str
    description: str
    proposed_payload: dict
    risk_level: str
    status: ApprovalStatus
    reason: str
    created_by: str
    reviewed_by: str | None
    created_at: datetime
    reviewed_at: datetime | None


class ApprovalListResponse(BaseModel):
    items: list[ApprovalResponse]
    total: int
    pending_count: int


class ApprovalDecisionRequest(BaseModel):
    status: ApprovalStatus
    reason: str | None = None
