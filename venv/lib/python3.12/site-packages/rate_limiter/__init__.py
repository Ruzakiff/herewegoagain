from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from rate_limiter.backends.template import RateLimiterBackend


@dataclass
class RateLimit:
    requests: int
    time_duration: timedelta


class TooManyRequests(Exception):
    pass


class RateLimiter:
    def __init__(self, backend, rate_limit, namespace="default"):
        self._backend: RateLimiterBackend = backend
        self.namespace: str = namespace
        self._rate: RateLimit = rate_limit

    def increment_usage(self, key: str, increment_by: int = 1) -> int:
        assert 0 < increment_by <= self._rate.requests

        current_usage = self._backend.increment_usage(
            key=self._mk_key(key),
            increment_by=increment_by,
            expiry=self._rate.time_duration,
        )

        if int(current_usage) > self._rate.requests:
            raise TooManyRequests

        return current_usage

    def _mk_key(self, key: Any) -> str:
        return f"ratelimit:{self.namespace}:{key}"
