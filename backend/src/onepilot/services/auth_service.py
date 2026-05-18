from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from onepilot.core.constants import PlanCode, Role
from onepilot.core.errors import AuthenticationError, ConflictError, ValidationError
from onepilot.core.ids import new_id
from onepilot.repositories.models import Organization, OrganizationMember, Subscription, User
from onepilot.repositories.organizations import OrganizationMemberRepository, OrganizationRepository
from onepilot.repositories.plans import SubscriptionRepository
from onepilot.repositories.users import UserRepository
from onepilot.security.auth import (
    Principal,
    create_access_token,
    hash_password,
    verify_password,
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")
MIN_PASSWORD_LENGTH = 8


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.lower()).strip("-")
    return slug or "org"


def register(
    session: Session,
    email: str,
    password: str,
    full_name: str,
    organization_name: str,
) -> tuple[User, Organization, str, datetime]:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    user_repo = UserRepository(session)
    if user_repo.get_by_email(email):
        raise ConflictError("A user with this email already exists")

    org_repo = OrganizationRepository(session)
    slug = _slugify(organization_name)
    existing = org_repo.get_by_slug(slug)
    if existing:
        slug = f"{slug}-{new_id()[:8]}"

    org = Organization(id=new_id("org"), name=organization_name, slug=slug)
    org_repo.create(org)

    user = User(
        id=new_id("usr"),
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    user_repo.create(user)

    member_repo = OrganizationMemberRepository(session)
    member = OrganizationMember(
        id=new_id("mem"),
        organization_id=org.id,
        user_id=user.id,
        role=Role.OWNER,
    )
    member_repo.create(member)

    sub_repo = SubscriptionRepository(session)
    sub = Subscription(
        id=new_id("sub"),
        organization_id=org.id,
        plan_code=PlanCode.FREE,
        status="active",
    )
    sub_repo.create(sub)

    session.commit()

    token, expires_at = create_access_token(
        user_id=user.id,
        organization_id=org.id,
        role=Role.OWNER,
        plan_code=PlanCode.FREE,
    )
    return user, org, token, expires_at


def authenticate(session: Session, email: str, password: str) -> tuple[User, str, datetime]:
    user_repo = UserRepository(session)
    user = user_repo.get_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    member_repo = OrganizationMemberRepository(session)
    memberships = member_repo.list_by_user(user.id)
    if not memberships:
        raise AuthenticationError("User has no organization membership")

    membership = memberships[0]
    sub_repo = SubscriptionRepository(session)
    sub = sub_repo.get_active(membership.organization_id)
    plan_code = sub.plan_code if sub else PlanCode.FREE

    token, expires_at = create_access_token(
        user_id=user.id,
        organization_id=membership.organization_id,
        role=membership.role,
        plan_code=plan_code,
    )
    return user, token, expires_at


def get_principal_details(
    session: Session, principal: Principal
) -> dict:
    user_repo = UserRepository(session)
    user = user_repo.get(principal.user_id)
    if not user:
        raise AuthenticationError("User not found")

    org_repo = OrganizationRepository(session)
    org = org_repo.get(principal.organization_id)

    return {
        "user": user,
        "organization": org,
        "role": principal.role,
        "plan_code": principal.plan_code,
    }
