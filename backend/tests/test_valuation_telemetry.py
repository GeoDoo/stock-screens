import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.valuation_service import ValuationService
from app.services.stock_data_client import StockDataClient

@pytest.mark.asyncio
async def test_valuation_service_records_telemetry():
    """Regression test: Ensure ValuationService records success/failure metrics."""
    # Mock dependencies
    mock_client = MagicMock(spec=StockDataClient)
    mock_client.get_stock_data = AsyncMock()
    mock_client.get_treasury_rate = AsyncMock(return_value=0.04)
    
    # Mock telemetry repo
    with patch("app.services.valuation_service.get_telemetry_repository") as mock_get_repo:
        mock_repo = AsyncMock()
        mock_get_repo.return_value = mock_repo
        
        service = ValuationService(mock_client)
        
        # Test Success Case
        # Setup mock stock data that will pass extraction
        mock_stock = MagicMock()
        mock_stock.provider = "fmp"
        mock_stock.profile.sector = "Technology"
        mock_stock.profile.industry = "Software"
        mock_client.get_stock_data.return_value = mock_stock
        
        # Mock data_adapter and DataExtractor to return valid numbers
        with patch("app.services.valuation_service.stock_data_to_legacy"), \
             patch("app.services.valuation_service.DataExtractor") as mock_ext_class:
            
            mock_ext = mock_ext_class.return_value
            mock_ext.beta.return_value = 1.2
            mock_ext.market_cap.return_value = 1e12
            mock_ext.cost_of_debt.return_value = 0.05
            mock_ext.total_debt.return_value = 1e10
            mock_ext.cash.return_value = 5e10
            mock_ext.shares_outstanding.return_value = 1e9
            mock_ext.latest_revenue.return_value = 1e11
            mock_ext.latest_operating_income.return_value = 3e10
            mock_ext.revenue_history.return_value = [1e11, 0.9e11]
            mock_ext.ebit_history.return_value = [3e10, 2.5e10]
            mock_ext.da_history.return_value = [5e9, 4e9]
            mock_ext.capex_history.return_value = [6e9, 5e9]
            mock_ext.working_capital_history.return_value = [1e10, 0.9e10]
            mock_ext.tax_rate.return_value = 0.21
            mock_ext.market_risk_premium.return_value = 0.06
            mock_ext.shares_outstanding_type.return_value = "diluted"
            mock_ext.total_equity.return_value = 5e11
            mock_ext.minority_interest.return_value = 0.0
            mock_ext.preferred_stock.return_value = 0.0
            mock_ext.deferred_tax_assets.return_value = 0.0
            mock_ext.pension_liability.return_value = 0.0
            mock_ext.revenue_cagr.return_value = 0.1
            mock_ext.operating_margin.return_value = 0.25
            mock_ext.da_to_revenue_ratio.return_value = 0.05
            mock_ext.capex_to_revenue_ratio.return_value = 0.06
            mock_ext.wc_to_revenue_ratio.return_value = 0.1
            mock_ext.goodwill.return_value = 0.0
            mock_ext.intangible_assets.return_value = 0.0
            
            # Execute
            await service.value_stock("AAPL")
            
            # Verify success telemetry - using any_str/any_float for dynamic values
            # Extract arguments to verify
            found_success = False
            for call in mock_repo.record_metric.call_args_list:
                args, kwargs = call
                if kwargs.get("operation") == "valuation" and kwargs.get("status") == "success":
                    found_success = True
                    assert kwargs.get("ticker") == "AAPL"
            assert found_success, "Success telemetry not recorded"

        # Test Failure Case
        mock_client.get_stock_data.side_effect = Exception("API Down")
        
        with pytest.raises(Exception):
            await service.value_stock("AAPL")
            
        # Verify failure telemetry
        found_failure = False
        for call in mock_repo.record_metric.call_args_list:
            args, kwargs = call
            if kwargs.get("operation") == "valuation" and kwargs.get("status") == "failed":
                found_failure = True
                assert kwargs.get("ticker") == "AAPL"
                assert "API Down" in kwargs.get("error_message")
        assert found_failure, "Failure telemetry not recorded"
