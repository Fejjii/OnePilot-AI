from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from onepilot.core.config import Settings, get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.errors import AuthenticationError
from onepilot.core.logging import get_logger, request_id_ctx
from onepilot.repositories.session import get_session
from onepilot.security.auth import Principal, decode_access_token

logger = get_logger(__name__)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSession = Annotated[Session, Depends(get_session)]


def get_request_id(request: Request) -> str:
    return request_id_ctx.get() or request.headers.get("X-Request-ID", "unknown")


def get_current_principal(
    settings: SettingsDep,
    authorization: str | None = Header(None),
) -> Principal:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        return decode_access_token(token)

    if settings.DEV_AUTH_ENABLED:
        logger.warning("dev_auth_fallback", user_id=settings.DEV_USER_ID, org_id=settings.DEV_ORG_ID)
        return Principal(
            user_id=settings.DEV_USER_ID,
            organization_id=settings.DEV_ORG_ID,
            role=Role.OWNER,
            plan_code=PlanCode.BUSINESS,
        )

    raise AuthenticationError("Missing or invalid Authorization header")


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
