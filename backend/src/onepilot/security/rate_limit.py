from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from onepilot.core.config import Settings, get_settings
from onepilot.core.errors import RateLimitExceededError
from onepilot.security.auth import Principal

logger = logging.getLogger(__name__)

FEATURE_CHAT = "chat"
FEATURE_DOCUMENT_UPLOAD = "document_upload"
FEATURE_AUTH_LOGIN = "auth_login"
FEATURE_AUTH_REGISTER = "auth_register"

# Per-feature limits: (max requests, window seconds).
_FEATURE_LIMITS: dict[str, tuple[int, int]] = {
    FEATURE_CHAT: (60, 60),
    FEATURE_DOCUMENT_UPLOAD: (20, 60),
    FEATURE_AUTH_LOGIN: (10, 60),
    FEATURE_AUTH_REGISTER: (5, 3600),
}

_KEY_PREFIX = "onepilot:rl:v1"

_rate_limiter: RateLimiterBackend | None = None


def _hash_identifier(value: str) -> str:
    """Hash identifiers so Redis keys do not store raw emails or IPs."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _limits_for(feature: str, *, default_capacity: int = 60, default_window: int = 60) -> tuple[int, int]:
    return _FEATURE_LIMITS.get(feature, (default_capacity, default_window))


class RateLimiterBackend(Protocol):
    def check(self, org_id: str, user_id: str, feature: str) -> bool: ...

    def reset(self, org_id: str, user_id: str, feature: str) -> None: ...

    @property
    def backend_mode(self) -> str: ...


@dataclass
class _WindowCounter:
    count: int = 0
    window_start: float = field(default_factory=time.monotonic)


class MemoryRateLimiter:
    """Fixed-window in-memory rate limiter keyed by (org_id, user_id, feature)."""

    def __init__(
        self,
        default_capacity: int = 60,
        default_window: int = 60,
    ) -> None:
        self._counters: dict[str, _WindowCounter] = {}
        self._default_capacity = default_capacity
        self._default_window = default_window

    @property
    def backend_mode(self) -> str:
        return "memory"

    def _storage_key(self, org_id: str, user_id: str, feature: str) -> str:
        return f"{org_id}:{user_id}:{feature}"

    def check(self, org_id: str, user_id: str, feature: str) -> bool:
        capacity, window_seconds = _limits_for(
            feature,
            default_capacity=self._default_capacity,
            default_window=self._default_window,
        )
        key = self._storage_key(org_id, user_id, feature)
        now = time.monotonic()
        counter = self._counters.get(key)
        if counter is None or now - counter.window_start >= window_seconds:
            counter = _WindowCounter(count=0, window_start=now)
            self._counters[key] = counter
        if counter.count >= capacity:
            return False
        counter.count += 1
        return True

    def reset(self, org_id: str, user_id: str, feature: str) -> None:
        self._counters.pop(self._storage_key(org_id, user_id, feature), None)


_INCR_EXPIRE_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class RedisRateLimiter:
    """Fixed-window Redis rate limiter with hashed key parts."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._script = client.register_script(_INCR_EXPIRE_LUA)

    @property
    def backend_mode(self) -> str:
        return "redis"

    def _redis_key(self, org_id: str, user_id: str, feature: str) -> str:
        return (
            f"{_KEY_PREFIX}:{feature}:"
            f"{_hash_identifier(org_id)}:{_hash_identifier(user_id)}"
        )

    def check(self, org_id: str, user_id: str, feature: str) -> bool:
        capacity, window_seconds = _limits_for(feature)
        redis_key = self._redis_key(org_id, user_id, feature)
        count = int(self._script(keys=[redis_key], args=[window_seconds]))
        return count <= capacity

    def reset(self, org_id: str, user_id: str, feature: str) -> None:
        self._client.delete(self._redis_key(org_id, user_id, feature))


class CompositeRateLimiter:
    """Prefer Redis; fall back to memory when Redis is missing or errors."""

    def __init__(self, *, redis_backend: RedisRateLimiter, memory_backend: MemoryRateLimiter) -> None:
        self._redis = redis_backend
        self._memory = memory_backend
        self._use_redis = True

    @property
    def backend_mode(self) -> str:
        return "redis" if self._use_redis else "memory"

    def check(self, org_id: str, user_id: str, feature: str) -> bool:
        if self._use_redis:
            try:
                return self._redis.check(org_id, user_id, feature)
            except Exception as exc:
                logger.warning(
                    "rate_limit_redis_check_failed",
                    extra={"error": str(exc), "feature": feature},
                )
                self._use_redis = False
        return self._memory.check(org_id, user_id, feature)

    def reset(self, org_id: str, user_id: str, feature: str) -> None:
        if self._use_redis:
            try:
                self._redis.reset(org_id, user_id, feature)
            except Exception:
                pass
        self._memory.reset(org_id, user_id, feature)


# Backward-compatible alias used in existing unit tests.
RateLimiter = MemoryRateLimiter


def _create_redis_client(redis_url: str) -> Any:
    import redis

    return redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def _build_rate_limiter(settings: Settings | None = None) -> RateLimiterBackend:
    settings = settings or get_settings()
    memory = MemoryRateLimiter()

    if not settings.has_redis:
        return memory

    try:
        client = _create_redis_client(settings.REDIS_URL)
        client.ping()
        return CompositeRateLimiter(
            redis_backend=RedisRateLimiter(client),
            memory_backend=memory,
        )
    except Exception as exc:
        logger.warning(
            "rate_limit_redis_unavailable",
            extra={"error": str(exc), "fallback": "memory"},
        )
        return memory


def get_rate_limiter() -> RateLimiterBackend:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = _build_rate_limiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Drop the process-wide limiter; intended for tests."""
    global _rate_limiter
    _rate_limiter = None


def rate_limit_runtime_status(settings: Settings | None = None) -> dict[str, str | bool]:
    """Safe rate-limit backend status for health/diagnostics (no user identifiers)."""
    settings = settings or get_settings()
    limiter = get_rate_limiter()
    mode = getattr(limiter, "backend_mode", "memory")
    redis_configured = settings.has_redis
    return {
        "rate_limit_backend": mode,
        "rate_limit_redis_configured": redis_configured,
        "rate_limit_shared": mode == "redis",
    }


def enforce_rate_limit(
    *,
    organization_id: str,
    user_id: str,
    feature: str,
) -> None:
    """Raise :class:`RateLimitExceededError` when the bucket is exhausted."""
    if not get_rate_limiter().check(organization_id, user_id, feature):
        raise RateLimitExceededError(
            f"Rate limit exceeded for '{feature}'. Please try again shortly."
        )


def enforce_rate_limit_for_principal(principal: Principal, feature: str) -> None:
    enforce_rate_limit(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        feature=feature,
    )


def enforce_rate_limit_for_client(client_key: str, feature: str) -> None:
    """Rate limit unauthenticated endpoints (login/register) by client identifier."""
    enforce_rate_limit(
        organization_id="_public",
        user_id=client_key,
        feature=feature,
    )
