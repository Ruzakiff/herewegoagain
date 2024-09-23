from datetime import timedelta
from redis import Redis

from .template import RateLimiterBackend


ONE_SECOND = timedelta(seconds=1)


class RedisRateLimiterBackend(RateLimiterBackend):
    def __init__(self, client, default_expiry: timedelta = ONE_SECOND):
        self._client: Redis = client
        self._expiry = default_expiry.total_seconds()

    def increment_usage(
        self, key: str, expiry: timedelta = None, increment_by: int = 1
    ):
        expiry_ms = int((expiry or self._expiry).total_seconds() * 1000)

        # The increment and expiry aren't atomic. So usage count can cross the limit by 1 or 2.
        # It's not perfect but will work in all cases where the limit is not too low and need not
        # be strictly enforced.
        # The alternative is to write a Lua script to do both the increment and expiry in a single
        # atomic operation. But the eval() call is expensive and should be avoided if possible.
        current_usage = self._client.incrby(key, increment_by)
        if current_usage == increment_by:
            self._client.pexpire(key, expiry_ms)

        return current_usage
