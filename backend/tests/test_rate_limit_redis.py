"""Tests for Redis-backed rate limiting with in-memory fallback."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from onepilot.security.rate_limit import (
    FEATURE_AUTH_LOGIN,
    FEATURE_AUTH_REGISTER,
    FEATURE_CHAT,
    CompositeRateLimiter,
    MemoryRateLimiter,
    RedisRateLimiter,
    _FEATURE_LIMITS,
    _build_rate_limiter,
    enforce_rate_limit,
    rate_limit_runtime_status,
    reset_rate_limiter,
)


class FakeRedisScript:
    def __init__(self, redis: FakeRedis) -> None:
        self._redis = redis

    def __call__(self, *, keys: list[str], args: list[str | int]) -> int:
        key = keys[0]
        ttl = int(args[0])
        count = self._redis.incr(key)
        if count == 1:
            self._redis.expire(key, ttl)
        return count


class FakeRedis:
    """Minimal Redis stand-in for unit tests (no real server required)."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._expires_at: dict[str, float] = {}
        self._now = time.monotonic()

    def advance(self, seconds: float) -> None:
        self._now += seconds
        expired = [k for k, exp in self._expires_at.items() if exp <= self._now]
        for key in expired:
            self._counts.pop(key, None)
            self._expires_at.pop(key, None)

    def _purge(self, key: str) -> None:
        exp = self._expires_at.get(key)
        if exp is not None and exp <= self._now:
            self._counts.pop(key, None)
            self._expires_at.pop(key, None)

    def incr(self, key: str) -> int:
        self._purge(key)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def expire(self, key: str, ttl: int) -> bool:
        self._expires_at[key] = self._now + ttl
        return True

    def delete(self, key: str) -> int:
        existed = key in self._counts
        self._counts.pop(key, None)
        self._expires_at.pop(key, None)
        return int(existed)

    def ping(self) -> bool:
        return True

    def register_script(self, _script: str) -> FakeRedisScript:
        return FakeRedisScript(self)


@pytest.fixture(autouse=True)
def _clear_limiter() -> None:
    reset_rate_limiter()
    yield
    reset_rate_limiter()


class TestMemoryRateLimiter:
    def test_allows_then_blocks_without_redis(self) -> None:
        limiter = MemoryRateLimiter(default_capacity=3, default_window=3600)
        org, user, feat = "org1", "usr1", "custom_feature"

        for _ in range(3):
            assert limiter.check(org, user, feat) is True
        assert limiter.check(org, user, feat) is False

    def test_runtime_status_defaults_to_memory(self) -> None:
        status = rate_limit_runtime_status()
        assert status["rate_limit_backend"] == "memory"
        assert status["rate_limit_redis_configured"] is False
        assert status["rate_limit_shared"] is False


class TestRedisRateLimiter:
    def test_limits_shared_across_instances(self) -> None:
        fake = FakeRedis()
        limiter_a = RedisRateLimiter(fake)
        limiter_b = RedisRateLimiter(fake)
        _FEATURE_LIMITS["test_shared"] = (2, 60)

        for _ in range(2):
            assert limiter_a.check("org1", "usr1", "test_shared") is True

        assert limiter_b.check("org1", "usr1", "test_shared") is False

    def test_ttl_expiry_allows_requests_again(self) -> None:
        fake = FakeRedis()
        limiter = RedisRateLimiter(fake)
        _FEATURE_LIMITS["test_ttl_feature"] = (1, 2)

        assert limiter.check("org1", "usr1", "test_ttl_feature") is True
        assert limiter.check("org1", "usr1", "test_ttl_feature") is False

        fake.advance(3)
        assert limiter.check("org1", "usr1", "test_ttl_feature") is True

    def test_redis_keys_are_hashed(self) -> None:
        fake = FakeRedis()
        limiter = RedisRateLimiter(fake)
        limiter.check("_public", "login:user@example.com", FEATURE_AUTH_LOGIN)

        for key in fake._counts:
            assert "user@example.com" not in key
            assert key.startswith("onepilot:rl:v1:")

    def test_lua_script_matches_incr_expire_semantics(self) -> None:
        fake = FakeRedis()
        script = FakeRedisScript(fake)
        count = script(keys=["k1"], args=[60])
        assert count == 1
        count = script(keys=["k1"], args=[60])
        assert count == 2


class TestCompositeRateLimiter:
    def test_falls_back_to_memory_when_redis_errors(self) -> None:
        broken = MagicMock()
        broken.register_script.return_value = MagicMock(
            side_effect=ConnectionError("redis down")
        )
        memory = MemoryRateLimiter(default_capacity=2, default_window=3600)
        composite = CompositeRateLimiter(
            redis_backend=RedisRateLimiter(broken),
            memory_backend=memory,
        )

        assert composite.check("org1", "usr1", "custom_feature") is True
        assert composite.backend_mode == "memory"
        assert composite.check("org1", "usr1", "custom_feature") is True
        assert composite.check("org1", "usr1", "custom_feature") is False

    def test_build_rate_limiter_uses_memory_without_redis_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REDIS_URL", "")
        from onepilot.core.config import get_settings

        get_settings.cache_clear()
        limiter = _build_rate_limiter()
        assert limiter.backend_mode == "memory"

    def test_build_rate_limiter_uses_redis_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = FakeRedis()

        def _fake_from_url(*_args: Any, **_kwargs: Any) -> FakeRedis:
            return fake

        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setattr(
            "onepilot.security.rate_limit._create_redis_client",
            lambda _url: fake,
        )
        from onepilot.core.config import get_settings

        get_settings.cache_clear()
        limiter = _build_rate_limiter()
        assert limiter.backend_mode == "redis"


class TestRateLimitIntegration429:
    def _register(self, client: TestClient, suffix: str) -> str:
        resp = client.post(
            "/auth/register",
            json={
                "email": f"rlredis{suffix}@example.com",
                "password": "strongpass123",
                "full_name": "RL User",
                "organization_name": f"RLOrg{suffix}",
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    def test_login_rate_limit_returns_429(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setitem(_FEATURE_LIMITS, FEATURE_AUTH_LOGIN, (2, 60))
        reset_rate_limiter()
        from onepilot.security import rate_limit as rl_module

        rl_module._rate_limiter = MemoryRateLimiter()

        client.post(
            "/auth/register",
            json={
                "email": "login429@example.com",
                "password": "strongpass123",
                "full_name": "User",
                "organization_name": "Org",
            },
        )
        payload = {"email": "login429@example.com", "password": "strongpass123"}
        assert client.post("/auth/login", json=payload).status_code == 200
        assert client.post("/auth/login", json=payload).status_code == 200
        blocked = client.post("/auth/login", json=payload)
        assert blocked.status_code == 429
        assert blocked.json()["error"] == "RATE_LIMIT_EXCEEDED"

    def test_register_rate_limit_returns_429(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setitem(_FEATURE_LIMITS, FEATURE_AUTH_REGISTER, (2, 3600))
        reset_rate_limiter()
        from onepilot.security import rate_limit as rl_module

        rl_module._rate_limiter = MemoryRateLimiter()

        for i in range(2):
            assert client.post(
                "/auth/register",
                json={
                    "email": f"reg429_{i}@example.com",
                    "password": "strongpass123",
                    "full_name": "User",
                    "organization_name": f"Org{i}",
                },
            ).status_code == 200

        blocked = client.post(
            "/auth/register",
            json={
                "email": "reg429_blocked@example.com",
                "password": "strongpass123",
                "full_name": "Blocked",
                "organization_name": "BlockedOrg",
            },
        )
        assert blocked.status_code == 429

    def test_enforce_rate_limit_raises(self) -> None:
        from onepilot.security import rate_limit as rl_module

        rl_module._rate_limiter = MemoryRateLimiter(default_capacity=1, default_window=3600)
        enforce_rate_limit(organization_id="org1", user_id="usr1", feature="custom_feature")
        with pytest.raises(Exception) as exc:
            enforce_rate_limit(organization_id="org1", user_id="usr1", feature="custom_feature")
        from onepilot.core.errors import RateLimitExceededError

        assert isinstance(exc.value, RateLimitExceededError)
        assert exc.value.status_code == 429


class TestHealthRateLimitDiagnostics:
    def test_health_includes_rate_limit_backend(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REDIS_URL", "")
        from onepilot.core.config import get_settings

        get_settings.cache_clear()
        reset_rate_limiter()

        resp = client.get("/health")
        assert resp.status_code == 200
        providers = resp.json()["providers"]
        assert providers["rate_limit_backend"] == "memory"
        assert providers["rate_limit_shared"] is False

    def test_providers_redis_includes_rate_limit_details(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REDIS_URL", "")
        from onepilot.core.config import get_settings

        get_settings.cache_clear()
        reset_rate_limiter()

        resp = client.get("/providers")
        assert resp.status_code == 200
        redis = next(p for p in resp.json()["providers"] if p["name"] == "Redis")
        assert redis["details"]["rate_limit_backend"] == "memory"
