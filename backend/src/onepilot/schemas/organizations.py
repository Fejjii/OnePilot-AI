from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from onepilot.core.constants import Role


class OrganizationCreate(BaseModel):
    name: str


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class AddMemberRequest(BaseModel):
    email: str
    role: Role = Role.MEMBER


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str
    role: Role
    created_at: datetime
