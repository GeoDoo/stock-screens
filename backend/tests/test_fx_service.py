import pytest
from unittest.mock import AsyncMock, patch
from app.services.fx_service import FXService

@pytest.mark.asyncio
async def test_get_rates_returns_valid_dict():
    fx = FXService()
    # Mocking the actual provider call inside FXService
    with patch.object(fx, '_fetch_live_rates', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"EUR": 0.92, "GBP": 0.78}
        
        rates = await fx.get_rates(["EUR", "GBP"])
        
        assert "EUR" in rates
        assert rates["EUR"] == 0.92
        assert "USD" in rates
        assert rates["USD"] == 1.0

@pytest.mark.asyncio
async def test_convert_amount_standard_case():
    fx = FXService()
    with patch.object(fx, '_fetch_live_rates', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"EUR": 0.92}
        
        # Convert 100 EUR to USD (100 / 0.92 ≈ 108.70)
        usd_amount = await fx.convert(100, from_currency="EUR", to_currency="USD")
        assert round(usd_amount, 2) == 108.70

@pytest.mark.asyncio
async def test_fallback_rates_used_on_failure():
    fx = FXService()
    # Simulate API failure
    with patch.object(fx, '_fetch_live_rates', side_effect=Exception("API Down")):
        rates = await fx.get_rates(["EUR"])
        
        assert "EUR" in rates
        # Fallback for EUR is typically around 0.92 in our repo
        assert rates["EUR"] > 0
