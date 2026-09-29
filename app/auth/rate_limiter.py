"""
Login rate limiting.

Backed by Redis (REDIS_URL) so the limit is shared across every
worker process/instance and survives restarts. The old in-memory
dict this replaced reset on every restart and was invisible to every
worker except the one that happened to handle a given request --
which made it silently do nothing useful anywhere Redis isn't wired
up with more than one uvicorn worker (which is the normal case in
production).

Falls back to an in-memory store when REDIS_URL isn't configured, so
local development without a Redis instance still works -- just
without the persistence/cross-process guarantees. A Redis outage
also fails *open* (attempts are allowed through, logged) rather than
breaking login entirely -- a rate limiter should never be a single
point of failure for authentication.
"""

import logging
from datetime import datetime

import redis

from app.auth.exceptions import RateLimitExceededError
from app.config.settings import settings

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BLOCK_SECONDS = 300


class _InMemoryRateLimiter:
    """
    Fallback used when REDIS_URL isn't configured. Same fixed-window
    semantics as the Redis-backed limiter, just process-local.
    """

    def __init__(self) -> None:
        self._attempts: dict[str, tuple[int, datetime]] = {}

    def check(self, key: str) -> None:

        now = datetime.now()
        data = self._attempts.get(key)

        if data:
            count, first_attempt = data

            if count >= MAX_ATTEMPTS:

                if (now - first_attempt).total_seconds() < BLOCK_SECONDS:
                    raise RateLimitExceededError(
                        "Too many attempts. Try again later."
                    )

                self._attempts[key] = (1, now)

            else:
                self._attempts[key] = (count + 1, first_attempt)
        else:
            self._attempts[key] = (1, now)

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


class _RedisRateLimiter:
    """
    Fixed-window counter in Redis: INCR the key, and on the first
    increment in a window set its TTL to the block duration -- so
    the window slides forward from the *first* attempt, matching the
    original in-memory implementation's semantics exactly.
    """

    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
        )

    @staticmethod
    def _redis_key(key: str) -> str:
        return f"rate_limit:login:{key}"

    def check(self, key: str) -> None:

        redis_key = self._redis_key(key)

        try:
            count = self._client.incr(redis_key)

            if count == 1:
                self._client.expire(redis_key, BLOCK_SECONDS)

        except redis.RedisError as exc:

            # Fail open: an infra outage on the rate limiter's own
            # backing store should not take down login for everyone.
            logger.error(
                "Redis rate limiter unavailable (%s) -- allowing "
                "the request through.",
                exc,
            )
            return

        if count > MAX_ATTEMPTS:
            raise RateLimitExceededError(
                "Too many attempts. Try again later."
            )

    def reset(self, key: str) -> None:

        try:
            self._client.delete(self._redis_key(key))
        except redis.RedisError as exc:
            logger.error(
                "Redis rate limiter unavailable (%s) -- could not "
                "reset attempts for this key.",
                exc,
            )


def _build_limiter():

    if settings.REDIS_URL:
        return _RedisRateLimiter(settings.REDIS_URL)

    logger.warning(
        "REDIS_URL not configured -- using an in-memory rate "
        "limiter. This resets on restart and is NOT shared across "
        "multiple worker processes/instances. Set REDIS_URL before "
        "deploying with more than one worker."
    )

    return _InMemoryRateLimiter()


_limiter = _build_limiter()


def check_rate_limit(key: str) -> None:
    _limiter.check(key)


def reset_attempts(key: str) -> None:
    _limiter.reset(key)