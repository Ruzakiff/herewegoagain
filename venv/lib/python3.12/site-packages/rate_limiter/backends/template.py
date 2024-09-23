from abc import ABC, abstractmethod
from datetime import timedelta


class RateLimiterBackend(ABC):
    @abstractmethod
    def increment_usage(
        self, key: str, expiry: timedelta = None, increment_by: int = 1
    ):
        pass
