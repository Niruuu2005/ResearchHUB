import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal operational state
    OPEN = "OPEN"            # Tripped; requests immediately rejected
    HALF_OPEN = "HALF_OPEN"  # Testing recovery with probe request


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Protects downstream research providers by fast-failing traffic when repeated failures occur.
    Transitions:
      CLOSED -> (failure threshold reached) -> OPEN -> (recovery timeout elapsed) -> HALF_OPEN
      HALF_OPEN -> (success) -> CLOSED
      HALF_OPEN -> (failure) -> OPEN
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    def record_success(self):
        """Record successful call, resetting circuit to CLOSED."""
        self.failure_count = 0
        if self.state != CircuitState.CLOSED:
            logger.info(f"CircuitBreaker [{self.name}] recovered to CLOSED state.")
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()

    def record_failure(self, exc: Optional[Exception] = None):
        """Record failed call; trip circuit to OPEN if threshold reached."""
        self.failure_count += 1
        logger.warning(
            f"CircuitBreaker [{self.name}] recorded failure ({self.failure_count}/{self.failure_threshold}): {exc}"
        )
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.error(f"CircuitBreaker [{self.name}] TRIPPED to OPEN state for {self.recovery_timeout}s.")

    def can_execute(self) -> bool:
        """Check if request is permitted through the circuit."""
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.recovery_timeout:
                logger.info(f"CircuitBreaker [{self.name}] entering HALF_OPEN probe state.")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False
        return True

    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute synchronous function through circuit breaker."""
        if not self.can_execute():
            raise CircuitBreakerOpenException(
                f"Provider '{self.name}' circuit breaker is OPEN. Upstream service is temporarily paused."
            )

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Alias for call_sync."""
        return self.call_sync(func, *args, **kwargs)

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute asynchronous function through circuit breaker."""
        if not self.can_execute():
            raise CircuitBreakerOpenException(
                f"Provider '{self.name}' circuit breaker is OPEN. Upstream service is temporarily paused."
            )

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise
