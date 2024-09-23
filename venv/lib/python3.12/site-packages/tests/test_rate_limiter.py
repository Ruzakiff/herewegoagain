from uuid import uuid4
from os import environ
from datetime import timedelta
from functools import wraps
from http import HTTPStatus

import pytest
from redis import Redis
from flask import Flask, Response, make_response, jsonify

from rate_limiter import RateLimiter, RateLimit, TooManyRequests
from rate_limiter.backends import RedisRateLimiterBackend


class NoOpClass:
    pass


redis_client = Redis(host=environ.get("REDIS_HOST"))


def get_rate_limiter(rate_limit):
    redis_backend = RedisRateLimiterBackend(client=redis_client)
    return RateLimiter(redis_backend, rate_limit=rate_limit)


def limit_requests(rate_limit: RateLimit, exception_handler=None):
    def inner_f(func):
        @wraps(func)
        def inner_inner_f(*args, **kwargs):
            key = func.__qualname__
            rate_limiter = get_rate_limiter(rate_limit)
            try:
                rate_limiter.increment_usage(key)
            except TooManyRequests as e:
                if exception_handler:
                    return exception_handler(e)
                else:
                    raise
            else:
                return func(*args, **kwargs)

        return inner_inner_f

    return inner_f


def test_increment_by_raises_error_if_increment_number_is_negative():
    TWO_PER_MINUTE = RateLimit(requests=2, time_duration=timedelta(minutes=1))
    redis_backend = RateLimiter(backend=NoOpClass, rate_limit=TWO_PER_MINUTE)

    with pytest.raises(AssertionError):
        redis_backend.increment_usage("lol", increment_by=-3)


def test_increment_by_raises_error_if_increment_number_is_greater_than_max_requests():
    TWO_PER_MINUTE = RateLimit(requests=2, time_duration=timedelta(minutes=1))
    redis_backend = RateLimiter(backend=NoOpClass, rate_limit=TWO_PER_MINUTE)

    with pytest.raises(AssertionError):
        redis_backend.increment_usage("lol", increment_by=10)


@pytest.mark.integration
def test_increment_by_properly_increases_usages():
    TWO_PER_MINUTE = RateLimit(requests=2, time_duration=timedelta(minutes=1))
    rate_limiter = get_rate_limiter(rate_limit=TWO_PER_MINUTE)
    key = f"lol-{uuid4()}"

    usages = rate_limiter.increment_usage(key)
    assert usages == 1

    usages = rate_limiter.increment_usage(key)
    assert usages == 2


@pytest.mark.integration
def test_increment_by_raises_TooManyRequests_error_when_requests_overflow():
    TWO_PER_MINUTE = RateLimit(requests=2, time_duration=timedelta(minutes=1))
    rate_limiter = get_rate_limiter(rate_limit=TWO_PER_MINUTE)

    key = f"lol-{uuid4()}"

    rate_limiter.increment_usage(key, increment_by=2)

    with pytest.raises(TooManyRequests):
        rate_limiter.increment_usage(key)


# NOTE: This test if run within one second twice will fail
@pytest.mark.integration
def test_rate_limit_decorator_throws_specified_error_after_rate_limit_is_exceeded():
    app = Flask(__name__)

    TWO_PER_MINUTE = RateLimit(requests=2, time_duration=timedelta(seconds=1))

    @app.route("/")
    @limit_requests(
        rate_limit=TWO_PER_MINUTE,
        exception_handler=lambda e: make_response(
            jsonify({"error": "fun"}), HTTPStatus.TOO_MANY_REQUESTS
        ),
    )
    def fun_fun_function():
        return Response(status=HTTPStatus.OK)

    with app.test_client() as client:
        res = client.get("/")
        assert res.status_code == HTTPStatus.OK

        res = client.get("/")
        assert res.status_code == HTTPStatus.OK

        res = client.get("/")
        assert res.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert res.get_json() == {"error": "fun"}
