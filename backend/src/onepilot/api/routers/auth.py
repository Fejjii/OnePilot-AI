from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from onepilot.api.deps import DBSession
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


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, session: DBSession) -> TokenResponse:
    _user, _org, token, expires_at = auth_service.register(
        session=session,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        organization_name=body.organization_name,
    )
    return TokenResponse(access_token=token, expires_at=expires_at.isoformat())


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: DBSession) -> TokenResponse:
    _user, token, expires_at = auth_service.authenticate(
        session=session,
        email=body.email,
        password=body.password,
    )
    return TokenResponse(access_token=token, expires_at=expires_at.isoformat())
