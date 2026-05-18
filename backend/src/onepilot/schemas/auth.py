from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from onepilot.core.constants import PlanCode, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    organization_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class Principal(BaseModel):
    """Resolved identity attached to every authenticated request."""

    user_id: str
    organization_id: str
    role: Role
    plan_code: PlanCode
