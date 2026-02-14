import pytest
from src.utils.circuit_breaker import circuit_breaker


calls = {"count": 0}


@circuit_breaker(failure_threshold=2, timeout=1)
def flaky():
    calls["count"] += 1
    # Always fail to trip breaker
    raise RuntimeError("boom")


def test_circuit_breaker_decorator_opens_after_failures():
    with pytest.raises(RuntimeError):
        flaky()
    with pytest.raises(RuntimeError):
        flaky()
    # After two failures, breaker should be OPEN and prevent further calls
    with pytest.raises(Exception) as ei:
        flaky()
    assert "Circuit breaker OPEN" in str(ei.value)
