from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr

from onepilot.api.deps import DBSession
from onepilot.security.rate_limit import (
    FEATURE_AUTH_LOGIN,
    FEATURE_AUTH_REGISTER,
    enforce_rate_limit_for_client,
)
from onepilot.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, request: Request, session: DBSession) -> TokenResponse:
    enforce_rate_limit_for_client(
        f"register:{_client_ip(request)}",
        FEATURE_AUTH_REGISTER,
    )
    _user, _org, token, expires_at = auth_service.register(
        session=session,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        organization_name=body.organization_name,
    )
    return TokenResponse(access_token=token, expires_at=expires_at.isoformat())


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, session: DBSession) -> TokenResponse:
    enforce_rate_limit_for_client(
        f"login:{body.email.lower()}",
        FEATURE_AUTH_LOGIN,
    )
    _user, token, expires_at = auth_service.authenticate(
        session=session,
        email=body.email,
        password=body.password,
    )
    return TokenResponse(access_token=token, expires_at=expires_at.isoformat())
