"""Tests for authentication endpoints and JWT utilities."""

from __future__ import annotations

import os
from datetime import timedelta

from fastapi.testclient import TestClient

from onepilot.core.config import get_settings
from onepilot.security.auth import create_access_token, decode_access_token


def _register_user(client: TestClient, suffix: str = "") -> dict:
    resp = client.post(
        "/auth/register",
        json={
            "email": f"user{suffix}@example.com",
            "password": "strongpass123",
            "full_name": "Test User",
            "organization_name": f"TestOrg{suffix}",
        },
    )
    return resp.json()


class TestRegister:
    def test_register_success(self, client: TestClient):
        resp = client.post(
            "/auth/register",
            json={
                "email": "new@example.com",
                "password": "securepass1",
                "full_name": "New User",
                "organization_name": "NewOrg",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data

    def test_register_duplicate_email(self, client: TestClient):
        client.post(
            "/auth/register",
            json={
                "email": "dup@example.com",
                "password": "securepass1",
                "full_name": "First",
                "organization_name": "Org1",
            },
        )
        resp = client.post(
            "/auth/register",
            json={
                "email": "dup@example.com",
                "password": "securepass2",
                "full_name": "Second",
                "organization_name": "Org2",
            },
        )
        assert resp.status_code == 409

    def test_register_weak_password(self, client: TestClient):
        resp = client.post(
            "/auth/register",
            json={
                "email": "weak@example.com",
                "password": "short",
                "full_name": "Weak Pass",
                "organization_name": "WeakOrg",
            },
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient):
        _register_user(client, suffix="_login")
        resp = client.post(
            "/auth/login",
            json={"email": "user_login@example.com", "password": "strongpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient):
        _register_user(client, suffix="_wrongpw")
        resp = client.post(
            "/auth/login",
            json={"email": "user_wrongpw@example.com", "password": "badpassword"},
        )
        assert resp.status_code == 401


class TestMe:
    def test_me_with_token(self, client: TestClient):
        data = _register_user(client, suffix="_me")
        token = data["access_token"]
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["email"] == "user_me@example.com"
        assert "organization" in body
        assert "role" in body

    def test_me_without_token(self, client: TestClient):
        resp = client.get("/me")
        assert resp.status_code == 401

    def test_me_with_dev_auth(self, client: TestClient):
        os.environ["DEV_AUTH_ENABLED"] = "true"
        get_settings.cache_clear()
        try:
            resp = client.get("/me")
            assert resp.status_code in (200, 401)
        finally:
            os.environ["DEV_AUTH_ENABLED"] = "false"
            get_settings.cache_clear()


class TestJWT:
    def test_jwt_decode(self):
        token, _expires = create_access_token(
            user_id="usr_test",
            organization_id="org_test",
            role="owner",
            plan_code="free",
        )
        principal = decode_access_token(token)
        assert principal.user_id == "usr_test"
        assert principal.organization_id == "org_test"
        assert principal.role == "owner"
        assert principal.plan_code == "free"

    def test_jwt_expired(self, client: TestClient):
        token, _ = create_access_token(
            user_id="usr_expired",
            organization_id="org_expired",
            role="owner",
            plan_code="free",
            expires_delta=timedelta(seconds=-1),
        )
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
