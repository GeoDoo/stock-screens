import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.valuation_service import ValuationService
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement

@pytest.mark.asyncio
async def test_equity_bridge_currency_normalization():
    """
    TDD: Failing test for currency normalization of institutional equity bridge components.
    Ensures minority_interest, investments, etc. are normalized along with other financials.
    """
    # EUR/USD rate: 1 EUR = 1.1 USD
    # rate_EUR = 0.90909 (units per 1 USD)
    rates = {"EUR": 0.90909, "USD": 1.0}
    
    mock_stock_data = StockData(
        profile=CompanyProfile(
            symbol="TEST.DE",
            name="Test EUR Corp",
            price=100.0,
            market_cap=1000000000,
            currency="EUR",
            beta=1.0, # Added beta
        ),
        financials=[
            FinancialStatement(
                date="2024-12-31",
                period="annual",
                revenue=500000,
                total_assets=1000000,
                total_liabilities=500000,
                total_equity=500000,
                total_debt=200000, # Added total_debt
                operating_income=70000,
                # These are the fields I suspect are missing from normalization
                minority_interest=100000, 
                investments=50000,
                preferred_stock=20000,
                deferred_tax_assets=10000,
                pension_liability=30000,
            )
        ],
        provider="fmp"
    )
    
    mock_client = MagicMock()
    mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
    mock_client.get_treasury_rate = AsyncMock(return_value=0.04)
    
    with patch("app.services.valuation_service.FXService") as MockFX:
        mock_fx = MockFX.return_value
        mock_fx.get_rates = AsyncMock(return_value=rates)
        
        service = ValuationService(mock_client)
        # Use override to avoid WACC issues
        result = await service.value_stock("TEST.DE", target_currency="USD", discount_rate_override=0.10)
        
        bridge = result["equity_bridge"]
        
        # Original minority_interest was 100,000 EUR
        # Normalized should be ~110,000 USD (Factor = 1.1)
        assert bridge["minority_interest"] == pytest.approx(110000, rel=1e-2)
        assert bridge["investments"] == pytest.approx(55000, rel=1e-2)
        assert bridge["preferred_stock"] == pytest.approx(22000, rel=1e-2)
        assert bridge["deferred_tax_assets"] == pytest.approx(11000, rel=1e-2)
        assert bridge["pension_deficit"] == pytest.approx(33000, rel=1e-2)
