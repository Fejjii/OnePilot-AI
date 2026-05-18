from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """In-memory rate limiter keyed by (org_id, user_id, feature)."""

    def __init__(
        self,
        default_capacity: int = 60,
        default_refill_rate: float = 1.0,
    ) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._default_capacity = default_capacity
        self._default_refill_rate = default_refill_rate

    def _key(self, org_id: str, user_id: str, feature: str) -> str:
        return f"{org_id}:{user_id}:{feature}"

    def _get_bucket(self, key: str) -> TokenBucket:
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                capacity=self._default_capacity,
                refill_rate=self._default_refill_rate,
            )
        return self._buckets[key]

    def check(self, org_id: str, user_id: str, feature: str) -> bool:
        """Returns True if the request is allowed."""
        bucket = self._get_bucket(self._key(org_id, user_id, feature))
        return bucket.consume()

    def reset(self, org_id: str, user_id: str, feature: str) -> None:
        key = self._key(org_id, user_id, feature)
        self._buckets.pop(key, None)
