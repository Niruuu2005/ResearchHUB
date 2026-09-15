import time
import pytest
from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitState


def test_circuit_breaker_transitions():
    cb = CircuitBreaker("test-provider", failure_threshold=3, recovery_timeout=0.2)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 1. Two failures do not trip circuit
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 2. Third failure trips circuit to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # 3. Synchronous execute raises CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        cb.execute(lambda: "should not run")

    # 4. Wait for recovery timeout to pass -> transitions to HALF_OPEN
    time.sleep(0.25)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 5. Success in HALF_OPEN recovers circuit to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_async_circuit_breaker_execution():
    cb = CircuitBreaker("async-test", failure_threshold=2, recovery_timeout=0.1)

    async def async_success():
        return "async-ok"

    res = await cb.call_async(async_success)
    assert res == "async-ok"
    assert cb.state == CircuitState.CLOSED

    async def async_fail():
        raise RuntimeError("network timeout")

    # First failure
    with pytest.raises(RuntimeError):
        await cb.call_async(async_fail)
    assert cb.state == CircuitState.CLOSED

    # Second failure -> trips to OPEN
    with pytest.raises(RuntimeError):
        await cb.call_async(async_fail)
    assert cb.state == CircuitState.OPEN

    # Subsequent call fast-fails with CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        await cb.call_async(async_success)
