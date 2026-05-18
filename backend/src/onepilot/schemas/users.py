from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from onepilot.core.constants import PlanCode, Role
from onepilot.schemas.organizations import OrganizationResponse


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MeResponse(BaseModel):
    user: UserResponse
    organization: OrganizationResponse
    role: Role
    plan: PlanCode
