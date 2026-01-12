import pytest
import asyncio
import time
from unittest.mock import AsyncMock
from app.services.resilience import CircuitBreaker
from app.services.base_provider import ProviderError

@pytest.mark.asyncio
async def test_circuit_breaker_recovery_bug():
    """
    Regression test for CircuitBreaker failure reset bug.
    Verifies that failures are reset when transitioning to HALF-OPEN.
    """
    # Threshold of 2 for quick testing
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, reset_timeout=0.1)
    
    mock_func = AsyncMock()
    mock_func.side_effect = Exception("Service Down")
    
    # 1. Trigger OPEN state
    # First failure
    with pytest.raises(Exception):
        await cb.call(mock_func)
    assert cb.failures == 1
    assert cb.state == "CLOSED"
    
    # Second failure -> OPEN
    with pytest.raises(Exception):
        await cb.call(mock_func)
    assert cb.failures == 2
    assert cb.state == "OPEN"
    
    # 2. Wait for reset timeout
    await asyncio.sleep(0.15)
    
    # 3. Transition to HALF-OPEN should happen on next call.
    # The bug is that 'failures' is NOT reset to 0 at this point.
    # So it's still 2.
    
    # A single failure in HALF-OPEN should be tested against a fresh counter.
    # If the counter is reset to 0, failures becomes 1.
    # 1 < 2 (threshold), so it should stay HALF-OPEN.
    # Currently, failures becomes 3, 3 >= 2, so it re-opens immediately.
    
    mock_func.side_effect = Exception("Still Down")
    with pytest.raises(Exception):
        await cb.call(mock_func)
    
    # EXPECTATION: A fair opportunity means it stays in HALF-OPEN for at least 
    # one more attempt if threshold > 1, because the counter should have been reset.
    assert cb.state == "HALF-OPEN", f"Circuit should be HALF-OPEN after 1 failure if threshold is 2, but was {cb.state}"
    assert cb.failures == 1
