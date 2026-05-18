from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from onepilot.core.config import get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.errors import AuthenticationError


class Principal(BaseModel):
    user_id: str
    organization_id: str
    role: Role
    plan_code: PlanCode


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw_bytes = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))


def create_access_token(
    user_id: str,
    organization_id: str,
    role: str,
    plan_code: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    settings = get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "plan": plan_code,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, expire


def decode_access_token(token: str) -> Principal:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise AuthenticationError("Invalid or expired token") from e

    user_id = payload.get("sub")
    org_id = payload.get("org")
    role = payload.get("role")
    plan = payload.get("plan")

    if not all([user_id, org_id, role, plan]):
        raise AuthenticationError("Token payload incomplete")

    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role(role),
        plan_code=PlanCode(plan),
    )
