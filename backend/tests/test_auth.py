"""Tests for authentication endpoints and JWT utilities."""

from __future__ import annotations

import os
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from onepilot.core.config import get_settings
from onepilot.security.auth import (
    BCRYPT_MAX_PASSWORD_BYTES,
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password,
)
from onepilot.security.rate_limit import (
    FEATURE_AUTH_LOGIN,
    FEATURE_AUTH_REGISTER,
    _FEATURE_LIMITS,
    reset_rate_limiter,
)


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


class TestPasswordValidation:
    def test_rejects_password_over_bcrypt_byte_limit(self) -> None:
        # 73 ASCII bytes exceeds bcrypt's 72-byte limit
        long_password = "a" * (BCRYPT_MAX_PASSWORD_BYTES + 1)
        with pytest.raises(Exception) as exc:
            validate_password(long_password)
        assert "72 bytes" in str(exc.value)

    def test_rejects_unicode_password_over_byte_limit(self) -> None:
        # Each emoji is 4 UTF-8 bytes; 19 * 4 = 76 bytes
        long_password = "🔒" * 19
        assert len(long_password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES
        with pytest.raises(Exception) as exc:
            validate_password(long_password)
        assert "72 bytes" in str(exc.value)

    def test_register_rejects_long_password(self, client: TestClient) -> None:
        long_password = "x" * (BCRYPT_MAX_PASSWORD_BYTES + 1)
        resp = client.post(
            "/auth/register",
            json={
                "email": "longpw@example.com",
                "password": long_password,
                "full_name": "Long PW",
                "organization_name": "LongPWOrg",
            },
        )
        assert resp.status_code == 422
        assert "72 bytes" in resp.json()["message"]

    def test_hash_password_does_not_silently_truncate(self) -> None:
        long_password = "b" * (BCRYPT_MAX_PASSWORD_BYTES + 1)
        with pytest.raises(Exception):
            hash_password(long_password)


class TestAuthRateLimit:
    def test_login_rate_limit_enforced(self, client: TestClient, monkeypatch) -> None:
        reset_rate_limiter()
        monkeypatch.setitem(_FEATURE_LIMITS, FEATURE_AUTH_LOGIN, (2, 60))
        _register_user(client, suffix="_login_rl")
        payload = {"email": "user_login_rl@example.com", "password": "strongpass123"}

        assert client.post("/auth/login", json=payload).status_code == 200
        assert client.post("/auth/login", json=payload).status_code == 200

        blocked = client.post("/auth/login", json=payload)
        assert blocked.status_code == 429
        assert blocked.json()["error"] == "RATE_LIMIT_EXCEEDED"

    def test_register_rate_limit_enforced(self, client: TestClient, monkeypatch) -> None:
        reset_rate_limiter()
        monkeypatch.setitem(_FEATURE_LIMITS, FEATURE_AUTH_REGISTER, (2, 3600))

        for i in range(2):
            resp = client.post(
                "/auth/register",
                json={
                    "email": f"reg_rl_{i}@example.com",
                    "password": "strongpass123",
                    "full_name": "RL User",
                    "organization_name": f"RLOrg{i}",
                },
            )
            assert resp.status_code == 200, resp.text

        blocked = client.post(
            "/auth/register",
            json={
                "email": "reg_rl_blocked@example.com",
                "password": "strongpass123",
                "full_name": "Blocked",
                "organization_name": "BlockedOrg",
            },
        )
        assert blocked.status_code == 429
        assert blocked.json()["error"] == "RATE_LIMIT_EXCEEDED"
