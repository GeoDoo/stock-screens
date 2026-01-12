import asyncio
import time
from functools import wraps
from typing import TypeVar, Callable, Any, Type
import tenacity
from app.services.logging_config import logger
from app.services.base_provider import ProviderError

T = TypeVar("T")

def retry_on_api_error(
    retries: int = 3,
    backoff_factor: float = 0.5,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator for retrying API calls with exponential backoff.
    
    Args:
        retries: Number of retry attempts.
        backoff_factor: Multiplier for exponential backoff.
        exceptions: Tuple of exceptions to catch and retry on.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            retryer = tenacity.AsyncRetrying(
                stop=tenacity.stop_after_attempt(retries),
                wait=tenacity.wait_exponential(multiplier=backoff_factor, min=1, max=10),
                retry=tenacity.retry_if_exception_type(exceptions),
                before_sleep=lambda retry_state: logger.warning(
                    "api_retry_attempt",
                    func=func.__name__,
                    attempt=retry_state.attempt_number,
                    exception=str(retry_state.outcome.exception()),
                ),
            )
            return await retryer(func, *args, **kwargs)
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Simple Circuit Breaker to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation, calls allowed.
    - OPEN: Calls blocked after failure threshold.
    - HALF-OPEN: One call allowed after reset timeout.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "CLOSED"
        self.last_failure_time = 0
        self.lock = asyncio.Lock()

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        async with self.lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.reset_timeout:
                    logger.info("circuit_breaker_half_open", name=self.name)
                    self.state = "HALF-OPEN"
                else:
                    logger.warning("circuit_breaker_open_blocked", name=self.name)
                    raise ProviderError(f"Circuit breaker {self.name} is OPEN")

            try:
                result = await func(*args, **kwargs)
                if self.state == "HALF-OPEN":
                    logger.info("circuit_breaker_closed", name=self.name)
                    self.state = "CLOSED"
                    self.failures = 0
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.failure_threshold:
                    logger.error("circuit_breaker_opened", name=self.name, failures=self.failures)
                    self.state = "OPEN"
                raise e

# Registry for circuit breakers
_breakers: dict[str, CircuitBreaker] = {}

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name, **kwargs)
    return _breakers[name]
