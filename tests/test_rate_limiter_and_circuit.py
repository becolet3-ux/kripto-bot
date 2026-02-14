import time
from src.utils.rate_limiter import RateLimiter
from src.utils.circuit_breaker import CircuitBreaker


def test_rate_limiter_allows_within_window(monkeypatch):
    rl = RateLimiter(max_requests=3, time_window=10)
    t = [1000.0]
    monkeypatch.setattr(time, "time", lambda: t[0])

    assert rl.allow_request() is True
    assert rl.allow_request() is True
    assert rl.allow_request() is True
    # 4th within same window blocked
    assert rl.allow_request() is False

    # Advance time beyond window
    t[0] += 11.0
    assert rl.allow_request() is True


def test_circuit_breaker_open_and_half_open(monkeypatch):
    cb = CircuitBreaker(failure_threshold=2, timeout=1, recovery_timeout=5)
    t = [1000.0]
    monkeypatch.setattr(time, "time", lambda: t[0])

    def fail():
        raise RuntimeError("boom")

    def ok():
        return 42

    # Two failures trigger OPEN
    for _ in range(2):
        try:
            cb.call(fail)
        except RuntimeError:
            pass
    assert cb.state == "OPEN"

    # Before recovery timeout, stays OPEN
    with_exc = False
    try:
        cb.call(ok)
    except Exception:
        with_exc = True
    assert with_exc is True

    # Advance beyond recovery timeout -> HALF_OPEN and allow call
    t[0] += 6.0
    assert cb.is_open() is False
    assert cb.state == "HALF_OPEN"
    assert cb.call(ok) == 42
    assert cb.state == "CLOSED"
