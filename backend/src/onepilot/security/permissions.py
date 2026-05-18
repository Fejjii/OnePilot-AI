from __future__ import annotations

from onepilot.core.constants import Role
from onepilot.core.errors import PermissionDeniedError
from onepilot.security.auth import Principal

ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.MEMBER: 1,
    Role.ADMIN: 2,
    Role.OWNER: 3,
}


class RoleChecker:
    """FastAPI-compatible dependency that checks the principal's role against allowed roles."""

    def __init__(self, *allowed_roles: Role) -> None:
        self._allowed = set(allowed_roles)

    def __call__(self, principal: Principal) -> Principal:
        if Role(principal.role) not in self._allowed:
            raise PermissionDeniedError(
                f"Role '{principal.role}' is not permitted for this action"
            )
        return principal


require_owner = RoleChecker(Role.OWNER)
require_admin = RoleChecker(Role.OWNER, Role.ADMIN)
require_member = RoleChecker(Role.OWNER, Role.ADMIN, Role.MEMBER)
require_viewer = RoleChecker(Role.OWNER, Role.ADMIN, Role.MEMBER, Role.VIEWER)


def ensure_same_org(principal: Principal, resource_org_id: str) -> None:
    if principal.organization_id != resource_org_id:
        raise PermissionDeniedError("Cross-tenant access denied")


def has_at_least_role(principal: Principal, minimum_role: Role) -> bool:
    return ROLE_HIERARCHY.get(Role(principal.role), -1) >= ROLE_HIERARCHY.get(minimum_role, 99)
