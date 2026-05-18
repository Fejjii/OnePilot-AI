"""Tests for tenant isolation in repositories."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from onepilot.core.constants import PlanCode
from onepilot.core.ids import new_id
from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import (
    Organization,
    OrganizationMember,
    Subscription,
    UsageQuota,
    User,
)
from onepilot.repositories.organizations import OrganizationMemberRepository
from onepilot.repositories.plans import SubscriptionRepository
from onepilot.repositories.usage import UsageQuotaRepository
from onepilot.security.auth import hash_password


def _create_org(session: Session, name: str) -> Organization:
    org = Organization(id=new_id("org"), name=name, slug=f"{name.lower()}-{new_id()[:6]}")
    session.add(org)
    session.flush()
    return org


def _create_user(session: Session, email: str) -> User:
    user = User(
        id=new_id("usr"),
        email=email,
        hashed_password=hash_password("testpass123"),
        full_name="Test User",
    )
    session.add(user)
    session.flush()
    return user


def _create_member(session: Session, org: Organization, user: User, role: str = "member") -> OrganizationMember:
    member = OrganizationMember(
        id=new_id("mem"),
        organization_id=org.id,
        user_id=user.id,
        role=role,
    )
    session.add(member)
    session.flush()
    return member


class TestBaseRepositoryIsolation:
    def test_user_repo_cannot_cross_org(self, db_session: Session):
        org_a = _create_org(db_session, "OrgA")
        org_b = _create_org(db_session, "OrgB")

        sub = Subscription(
            id=new_id("sub"),
            organization_id=org_a.id,
            plan_code=PlanCode.FREE,
            status="active",
        )
        db_session.add(sub)
        db_session.flush()

        repo = BaseRepository(db_session, Subscription)
        found = repo.get(sub.id, organization_id=org_a.id)
        assert found is not None
        assert found.id == sub.id

        not_found = repo.get(sub.id, organization_id=org_b.id)
        assert not_found is None


class TestSubscriptionIsolation:
    def test_subscription_scoped_to_org(self, db_session: Session):
        org_a = _create_org(db_session, "SubOrgA")
        org_b = _create_org(db_session, "SubOrgB")

        sub = Subscription(
            id=new_id("sub"),
            organization_id=org_a.id,
            plan_code=PlanCode.FREE,
            status="active",
        )
        db_session.add(sub)
        db_session.flush()

        sub_repo = SubscriptionRepository(db_session)
        assert sub_repo.get_active(org_a.id) is not None
        assert sub_repo.get_active(org_b.id) is None


class TestQuotaIsolation:
    def test_quota_scoped_to_org(self, db_session: Session):
        org_a = _create_org(db_session, "QuotaOrgA")
        org_b = _create_org(db_session, "QuotaOrgB")

        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        quota = UsageQuota(
            id=new_id("uq"),
            organization_id=org_a.id,
            feature="chat_messages",
            used=5,
            period_start=period_start,
            period_end=period_start.replace(month=period_start.month + 1) if period_start.month < 12 else period_start.replace(year=period_start.year + 1, month=1),
        )
        db_session.add(quota)
        db_session.flush()

        quota_repo = UsageQuotaRepository(db_session)
        assert quota_repo.get_for_period(org_a.id, "chat_messages", period_start) is not None
        assert quota_repo.get_for_period(org_b.id, "chat_messages", period_start) is None


class TestMemberIsolation:
    def test_member_scoped_to_org(self, db_session: Session):
        org_a = _create_org(db_session, "MemOrgA")
        org_b = _create_org(db_session, "MemOrgB")

        user_a = _create_user(db_session, "usera_iso@example.com")
        user_b = _create_user(db_session, "userb_iso@example.com")

        _create_member(db_session, org_a, user_a, "owner")
        _create_member(db_session, org_b, user_b, "owner")

        member_repo = OrganizationMemberRepository(db_session)
        org_a_members = member_repo.list_by_org(org_a.id)
        org_b_members = member_repo.list_by_org(org_b.id)

        assert len(org_a_members) == 1
        assert org_a_members[0].user_id == user_a.id

        assert len(org_b_members) == 1
        assert org_b_members[0].user_id == user_b.id
