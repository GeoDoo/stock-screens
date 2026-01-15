import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.valuation_service import ValuationService
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement

@pytest.mark.asyncio
async def test_valuation_service_normalizes_currency():
    # 1. Setup mock data in EUR
    mock_profile = CompanyProfile(
        symbol="MC.PA", # LVMH in Paris
        name="LVMH",
        currency="EUR",
        price=700.0, # EUR
        market_cap=350000000000, # EUR
        beta=1.0,
        shares_outstanding=500000000,
    )
    
    mock_financials = [
        FinancialStatement(
            date="2024-12-31",
            period="annual",
            revenue=86000000000, # EUR
            net_income=15000000000, # EUR
            operating_income=22000000000, # EUR
            total_assets=140000000000, # EUR
            total_liabilities=60000000000, # EUR
            total_equity=80000000000, # EUR
            total_debt=20000000000, # EUR
            cash_and_equivalents=10000000000, # EUR
            operating_cash_flow=18000000000, # EUR
            capital_expenditure=-5000000000, # EUR
            free_cash_flow=13000000000, # EUR
        )
    ]
    
    mock_stock_data = StockData(profile=mock_profile, financials=mock_financials, provider="fmp")
    
    mock_client = MagicMock()
    mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
    mock_client.get_treasury_rate = AsyncMock(return_value=0.04)
    
    service = ValuationService(mock_client)
    
    # Mock FX conversion
    with patch("app.services.valuation_service.FXService") as mock_fx_class:
        mock_fx = mock_fx_class.return_value
        # Mock EUR to USD rate: 1 EUR = 1.1 USD (rate = 0.91 EUR per 1 USD)
        mock_fx.get_rates = AsyncMock(return_value={"EUR": 0.91, "USD": 1.0})
        mock_fx.convert = AsyncMock(side_effect=lambda amt, f, t: amt / 0.91 if f=="EUR" else amt)
        
        # 2. Run valuation
        result = await service.value_stock("MC.PA")
        
        # 3. Assertions
        assert result["symbol"] == "MC.PA"
        # The result should indicate the currency was normalized
        assert result["currency"] == "USD"
        assert result["original_currency"] == "EUR"
        assert result["fx_conversion"]["rate"] == 0.91
        
        # Price should be normalized from 700 EUR to USD
        # 700 / 0.91 approx 769.23
        assert round(result["inputs"]["price"], 2) == 769.23
        
        # Revenue should be normalized from 86B EUR
        # 86B / 0.91 approx 94.5B
        assert result["projections"][0]["revenue"] > 94000000000
