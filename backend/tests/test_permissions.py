"""Tests for permission helpers and RoleChecker."""

from __future__ import annotations

import pytest

from onepilot.core.constants import PlanCode, Role
from onepilot.core.errors import PermissionDeniedError
from onepilot.security.auth import Principal
from onepilot.security.permissions import (
    ensure_same_org,
    has_at_least_role,
    require_admin,
    require_member,
    require_owner,
    require_viewer,
)


def _make_principal(role: Role) -> Principal:
    return Principal(
        user_id="usr_test",
        organization_id="org_test",
        role=role,
        plan_code=PlanCode.FREE,
    )


class TestRoleChecker:
    def test_role_checker_owner_passes(self):
        principal = _make_principal(Role.OWNER)
        result = require_owner(principal)
        assert result == principal

    def test_role_checker_member_fails_admin(self):
        principal = _make_principal(Role.MEMBER)
        with pytest.raises(PermissionDeniedError):
            require_admin(principal)

    def test_role_checker_viewer_fails_member(self):
        principal = _make_principal(Role.VIEWER)
        with pytest.raises(PermissionDeniedError):
            require_member(principal)

    def test_admin_passes_require_admin(self):
        principal = _make_principal(Role.ADMIN)
        result = require_admin(principal)
        assert result == principal

    def test_viewer_passes_require_viewer(self):
        principal = _make_principal(Role.VIEWER)
        result = require_viewer(principal)
        assert result == principal


class TestEnsureSameOrg:
    def test_ensure_same_org_passes(self):
        principal = _make_principal(Role.OWNER)
        ensure_same_org(principal, "org_test")

    def test_ensure_same_org_raises(self):
        principal = _make_principal(Role.OWNER)
        with pytest.raises(PermissionDeniedError):
            ensure_same_org(principal, "org_other")


class TestRoleHierarchy:
    @pytest.mark.parametrize(
        "role,minimum,expected",
        [
            (Role.OWNER, Role.OWNER, True),
            (Role.OWNER, Role.ADMIN, True),
            (Role.OWNER, Role.MEMBER, True),
            (Role.OWNER, Role.VIEWER, True),
            (Role.ADMIN, Role.OWNER, False),
            (Role.ADMIN, Role.ADMIN, True),
            (Role.ADMIN, Role.MEMBER, True),
            (Role.ADMIN, Role.VIEWER, True),
            (Role.MEMBER, Role.OWNER, False),
            (Role.MEMBER, Role.ADMIN, False),
            (Role.MEMBER, Role.MEMBER, True),
            (Role.MEMBER, Role.VIEWER, True),
            (Role.VIEWER, Role.OWNER, False),
            (Role.VIEWER, Role.ADMIN, False),
            (Role.VIEWER, Role.MEMBER, False),
            (Role.VIEWER, Role.VIEWER, True),
        ],
    )
    def test_role_hierarchy(self, role: Role, minimum: Role, expected: bool):
        principal = _make_principal(role)
        assert has_at_least_role(principal, minimum) is expected
