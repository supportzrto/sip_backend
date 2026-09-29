import time

import pytest
import redis as redis_module

from app.auth.exceptions import RateLimitExceededError
from app.auth.rate_limiter import (
    BLOCK_SECONDS,
    MAX_ATTEMPTS,
    _InMemoryRateLimiter,
    _RedisRateLimiter,
)


# ---------------------------------------------------------------------------
# In-memory fallback (used when REDIS_URL isn't configured)
# ---------------------------------------------------------------------------


def test_in_memory_limiter_allows_up_to_max_attempts():

    limiter = _InMemoryRateLimiter()

    for _ in range(MAX_ATTEMPTS):
        limiter.check("someone@example.com")  # should not raise


def test_in_memory_limiter_blocks_after_max_attempts():

    limiter = _InMemoryRateLimiter()

    for _ in range(MAX_ATTEMPTS):
        limiter.check("someone@example.com")

    with pytest.raises(RateLimitExceededError):
        limiter.check("someone@example.com")


def test_in_memory_limiter_reset_clears_the_counter():

    limiter = _InMemoryRateLimiter()

    for _ in range(MAX_ATTEMPTS):
        limiter.check("someone@example.com")

    limiter.reset("someone@example.com")

    limiter.check("someone@example.com")  # should not raise


def test_in_memory_limiter_keys_are_independent():

    limiter = _InMemoryRateLimiter()

    for _ in range(MAX_ATTEMPTS):
        limiter.check("a@example.com")

    limiter.check("b@example.com")  # different key, should not raise


# ---------------------------------------------------------------------------
# Redis-backed limiter -- exercised against a minimal fake client so the
# suite doesn't need a real Redis server.
# ---------------------------------------------------------------------------


class _FakeRedisClient:
    """
    Just enough of the redis-py client surface (incr/expire/delete)
    for _RedisRateLimiter, backed by a plain dict.
    """

    def __init__(self):
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, seconds):
        self.ttls[key] = seconds

    def delete(self, key):
        self.store.pop(key, None)
        self.ttls.pop(key, None)


@pytest.fixture
def redis_limiter(monkeypatch):

    limiter = _RedisRateLimiter.__new__(_RedisRateLimiter)
    limiter._client = _FakeRedisClient()

    return limiter


def test_redis_limiter_allows_up_to_max_attempts(redis_limiter):

    for _ in range(MAX_ATTEMPTS):
        redis_limiter.check("someone@example.com")  # should not raise


def test_redis_limiter_blocks_after_max_attempts(redis_limiter):

    for _ in range(MAX_ATTEMPTS):
        redis_limiter.check("someone@example.com")

    with pytest.raises(RateLimitExceededError):
        redis_limiter.check("someone@example.com")


def test_redis_limiter_sets_ttl_on_first_attempt_only(redis_limiter):

    redis_limiter.check("someone@example.com")
    redis_limiter.check("someone@example.com")

    key = redis_limiter._redis_key("someone@example.com")

    assert redis_limiter._client.ttls[key] == BLOCK_SECONDS
    assert redis_limiter._client.store[key] == 2


def test_redis_limiter_reset_clears_the_counter(redis_limiter):

    for _ in range(MAX_ATTEMPTS):
        redis_limiter.check("someone@example.com")

    redis_limiter.reset("someone@example.com")

    redis_limiter.check("someone@example.com")  # should not raise


def test_redis_limiter_fails_open_when_redis_is_unavailable(redis_limiter):
    """
    If Redis itself is down, login must not be broken for everyone --
    the limiter should log and let the request through rather than
    propagating the connection error.
    """

    class _BrokenClient:
        def incr(self, key):
            raise redis_module.ConnectionError("connection refused")

    redis_limiter._client = _BrokenClient()

    redis_limiter.check("someone@example.com")  # must not raise