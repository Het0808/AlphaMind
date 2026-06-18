"""Unit tests for the fixed-window rate limiter and API-key extraction."""

from api.ratelimit import RateLimiter
from api.security import extract_key


def test_rate_limiter_allows_up_to_limit_then_blocks():
    rl = RateLimiter(limit=3, window_seconds=60)
    results = [rl.check("client", now=0).allowed for _ in range(4)]
    assert results == [True, True, True, False]


def test_rate_limiter_reports_remaining():
    rl = RateLimiter(limit=5, window_seconds=60)
    d1 = rl.check("c", now=0)
    d2 = rl.check("c", now=0)
    assert d1.remaining == 4 and d2.remaining == 3


def test_rate_limiter_resets_after_window():
    rl = RateLimiter(limit=1, window_seconds=10)
    assert rl.check("c", now=0).allowed is True
    assert rl.check("c", now=5).allowed is False     # same window
    assert rl.check("c", now=11).allowed is True     # window elapsed → reset


def test_rate_limiter_isolates_clients():
    rl = RateLimiter(limit=1, window_seconds=60)
    assert rl.check("a", now=0).allowed is True
    assert rl.check("b", now=0).allowed is True       # different key, own bucket
    assert rl.check("a", now=0).allowed is False


def test_extract_key_from_header_and_bearer():
    assert extract_key("k123", None) == "k123"
    assert extract_key(None, "Bearer tok456") == "tok456"
    assert extract_key(None, "Basic xyz") is None
    assert extract_key(None, None) is None
