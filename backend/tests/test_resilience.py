import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from app.services.resilience import CircuitBreaker, retry_on_api_error, get_circuit_breaker
from app.services.base_provider import ProviderError

@pytest.mark.asyncio
async def test_circuit_breaker_states():
    """Test standard state transitions."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, reset_timeout=0.1)
    mock_func = AsyncMock(side_effect=Exception("Down"))
    
    # 1. CLOSED -> OPEN
    with pytest.raises(Exception):
        await cb.call(mock_func)
    assert cb.state == "CLOSED"
    assert cb.failures == 1
    
    with pytest.raises(Exception):
        await cb.call(mock_func)
    assert cb.state == "OPEN"
    assert cb.failures == 2
    
    # 2. OPEN -> Blocks calls
    with pytest.raises(ProviderError) as exc:
        await cb.call(mock_func)
    assert "is OPEN" in str(exc.value)
    
    # 3. OPEN -> HALF-OPEN (after timeout)
    await asyncio.sleep(0.15)
    mock_func.side_effect = None
    mock_func.return_value = "Success"
    
    result = await cb.call(mock_func)
    assert result == "Success"
    assert cb.state == "CLOSED" # Successful call in HALF-OPEN closes it
    assert cb.failures == 0

@pytest.mark.asyncio
async def test_circuit_breaker_recovery_fair_opportunity():
    """
    Regression test: Transition to HALF-OPEN should reset failures 
    to provide a 'fair opportunity' for recovery.
    """
    cb = CircuitBreaker(name="recovery_cb", failure_threshold=3, reset_timeout=0.1)
    mock_func = AsyncMock(side_effect=Exception("Down"))
    
    # Trigger OPEN
    for _ in range(3):
        with pytest.raises(Exception):
            await cb.call(mock_func)
    assert cb.state == "OPEN"
    assert cb.failures == 3
    
    await asyncio.sleep(0.15)
    
    # Now should be HALF-OPEN on next call. 
    # A single failure should NOT re-open it because failures should have been reset to 0.
    # failures becomes 1, which is < 3.
    with pytest.raises(Exception):
        await cb.call(mock_func)
    
    assert cb.state == "HALF-OPEN"
    assert cb.failures == 1
    
    # Two more failures -> OPEN
    with pytest.raises(Exception):
        await cb.call(mock_func)
    with pytest.raises(Exception):
        await cb.call(mock_func)
        
    assert cb.state == "OPEN"
    assert cb.failures == 3

@pytest.mark.asyncio
async def test_retry_on_api_error_decorator():
    """Test the retry decorator works with exponential backoff."""
    mock_func = AsyncMock()
    # Fail 2 times, succeed on 3rd
    mock_func.side_effect = [
        Exception("Attempt 1 Failed"),
        Exception("Attempt 2 Failed"),
        "Success"
    ]
    
    @retry_on_api_error(retries=2, backoff_factor=0.01)
    async def decorated_func():
        return await mock_func()
    
    result = await decorated_func()
    assert result == "Success"
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_retry_on_api_error_exhausted():
    """Test retry decorator when all attempts fail."""
    mock_func = AsyncMock(side_effect=Exception("Always Fails"))
    
    @retry_on_api_error(retries=2, backoff_factor=0.01)
    async def decorated_func():
        return await mock_func()
    
    with pytest.raises(Exception) as exc:
        await decorated_func()
    assert "Always Fails" in str(exc.value)
    assert mock_func.call_count == 3 # 1 initial + 2 retries

def test_get_circuit_breaker_singleton():
    """Test that get_circuit_breaker returns the same instance."""
    cb1 = get_circuit_breaker("shared_cb")
    cb2 = get_circuit_breaker("shared_cb")
    assert cb1 is cb2
    
    cb3 = get_circuit_breaker("other_cb")
    assert cb1 is not cb3
