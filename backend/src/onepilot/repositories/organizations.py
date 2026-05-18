from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from onepilot.repositories.base import BaseRepository
from onepilot.repositories.models import Organization, OrganizationMember


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Organization)

    def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        return self._session.execute(stmt).scalar_one_or_none()


class OrganizationMemberRepository(BaseRepository[OrganizationMember]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, OrganizationMember)

    def get_membership(self, organization_id: str, user_id: str) -> OrganizationMember | None:
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_by_org(self, organization_id: str) -> list[OrganizationMember]:
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_by_user(self, user_id: str) -> list[OrganizationMember]:
        stmt = select(OrganizationMember).where(OrganizationMember.user_id == user_id)
        return list(self._session.execute(stmt).scalars().all())
