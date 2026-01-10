import pytest
from unittest.mock import AsyncMock, patch
from app.services.fmp_client import FMPClient
from app.services.fmp_provider import FMPProvider


@pytest.fixture
def fmp_client():
    return FMPClient(api_key="test_key")


@pytest.fixture
def fmp_provider():
    return FMPProvider(api_key="test_key")


class TestFMPProviderPeriodMapping:
    """
    Tests for period mapping in FMPProvider._merge_financials.
    
    This ensures TTM/LTM periods are preserved and not collapsed to "quarterly".
    """
    
    def test_maps_fy_to_annual(self, fmp_provider):
        """FY (Fiscal Year) should map to 'annual'."""
        income = [{"date": "2024-09-30", "period": "FY", "revenue": 100_000}]
        balance = [{"date": "2024-09-30", "totalAssets": 200_000}]
        cash_flow = [{"date": "2024-09-30", "freeCashFlow": 50_000}]
        
        financials = fmp_provider._merge_financials(income, balance, cash_flow)
        
        assert len(financials) == 1
        assert financials[0].period == "annual"
    
    def test_maps_quarterly_to_quarterly(self, fmp_provider):
        """Q1-Q4 should map to 'quarterly'."""
        for quarter in ["Q1", "Q2", "Q3", "Q4"]:
            income = [{"date": "2024-09-30", "period": quarter, "revenue": 25_000}]
            balance = [{"date": "2024-09-30"}]
            cash_flow = [{"date": "2024-09-30"}]
            
            financials = fmp_provider._merge_financials(income, balance, cash_flow)
            
            assert financials[0].period == "quarterly", f"{quarter} should map to 'quarterly'"
    
    def test_maps_ttm_to_ttm(self, fmp_provider):
        """
        TTM should map to 'ttm' - NOT 'quarterly'.
        
        This is critical: if TTM is collapsed to 'quarterly', the downstream
        DataExtractor won't find it when looking for TTM data.
        """
        income = [{"date": "2024-09-30", "period": "TTM", "revenue": 100_000}]
        balance = [{"date": "2024-09-30"}]
        cash_flow = [{"date": "2024-09-30"}]
        
        financials = fmp_provider._merge_financials(income, balance, cash_flow)
        
        assert financials[0].period == "ttm", (
            "TTM period should be preserved, not collapsed to 'quarterly'"
        )
    
    def test_maps_ltm_to_ttm(self, fmp_provider):
        """LTM (Last Twelve Months) is equivalent to TTM."""
        income = [{"date": "2024-09-30", "period": "LTM", "revenue": 100_000}]
        balance = [{"date": "2024-09-30"}]
        cash_flow = [{"date": "2024-09-30"}]
        
        financials = fmp_provider._merge_financials(income, balance, cash_flow)
        
        assert financials[0].period == "ttm", (
            "LTM should be treated the same as TTM"
        )
    
    def test_handles_missing_period(self, fmp_provider):
        """Missing period should default to 'quarterly' (defensive)."""
        income = [{"date": "2024-09-30", "revenue": 100_000}]  # No period field
        balance = [{"date": "2024-09-30"}]
        cash_flow = [{"date": "2024-09-30"}]
        
        financials = fmp_provider._merge_financials(income, balance, cash_flow)
        
        # Missing period defaults to quarterly (safest assumption)
        assert financials[0].period == "quarterly"


class TestFMPClient:
    @pytest.mark.asyncio
    async def test_get_profile(self, fmp_client):
        mock_response = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "marketCap": 3000000000000,
            }
        ]

        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await fmp_client.get_profile("AAPL")

            mock_request.assert_called_once_with("/profile", symbol="AAPL")
            assert result["symbol"] == "AAPL"
            assert result["companyName"] == "Apple Inc."

    @pytest.mark.asyncio
    async def test_get_income_statement(self, fmp_client):
        mock_response = [
            {
                "date": "2023-09-30",
                "symbol": "AAPL",
                "revenue": 383285000000,
                "netIncome": 96995000000,
                "eps": 6.13,
            }
        ]

        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await fmp_client.get_income_statement("AAPL")

            mock_request.assert_called_once_with("/income-statement", symbol="AAPL", limit=5)
            assert len(result) == 1
            assert result[0]["revenue"] == 383285000000

    @pytest.mark.asyncio
    async def test_get_balance_sheet(self, fmp_client):
        mock_response = [
            {
                "date": "2023-09-30",
                "symbol": "AAPL",
                "totalAssets": 352583000000,
                "totalLiabilities": 290437000000,
                "totalStockholdersEquity": 62146000000,
            }
        ]

        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await fmp_client.get_balance_sheet("AAPL")

            mock_request.assert_called_once_with("/balance-sheet-statement", symbol="AAPL", limit=5)
            assert result[0]["totalAssets"] == 352583000000

    @pytest.mark.asyncio
    async def test_get_cash_flow(self, fmp_client):
        mock_response = [
            {
                "date": "2023-09-30",
                "symbol": "AAPL",
                "operatingCashFlow": 110543000000,
                "freeCashFlow": 99584000000,
            }
        ]

        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await fmp_client.get_cash_flow("AAPL")

            mock_request.assert_called_once_with("/cash-flow-statement", symbol="AAPL", limit=5)
            assert result[0]["freeCashFlow"] == 99584000000

    @pytest.mark.asyncio
    async def test_get_stock_data_aggregates_all(self, fmp_client):
        """Test that get_stock_data fetches all required data for DCF."""
        with patch.object(fmp_client, "get_profile", new_callable=AsyncMock) as mock_profile, \
             patch.object(fmp_client, "get_income_statement", new_callable=AsyncMock) as mock_income, \
             patch.object(fmp_client, "get_balance_sheet", new_callable=AsyncMock) as mock_balance, \
             patch.object(fmp_client, "get_cash_flow", new_callable=AsyncMock) as mock_cash:

            mock_profile.return_value = {"symbol": "AAPL", "companyName": "Apple Inc."}
            mock_income.return_value = [{"revenue": 100}]
            mock_balance.return_value = [{"totalAssets": 200}]
            mock_cash.return_value = [{"freeCashFlow": 50}]

            result = await fmp_client.get_stock_data("AAPL")

            assert "profile" in result
            assert "income_statement" in result
            assert "balance_sheet" in result
            assert "cash_flow" in result

    @pytest.mark.asyncio
    async def test_get_treasury_rate(self, fmp_client):
        """Test fetching 10-year treasury rate."""
        mock_response = [{"date": "2024-01-02", "year10": 4.25}]

        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await fmp_client.get_treasury_rate()

            # Should return as decimal (4.25% -> 0.0425)
            assert abs(result - 0.0425) < 0.0001

    @pytest.mark.asyncio
    async def test_get_treasury_rate_fallback(self, fmp_client):
        """Test fallback when treasury data unavailable."""
        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = []
            result = await fmp_client.get_treasury_rate()

            # Should return default 4.5%
            assert result == 0.045


class TestFMPProviderTTMReconstruction:
    """
    Tests for TTM (Trailing Twelve Months) reconstruction.
    
    P0 Fix: The "Quarterly Trap" - if FMP doesn't return TTM data and
    a company just filed a 10-Q, we might use 3-month revenue as
    "Latest Revenue" (catastrophic data integrity issue).
    
    Solution: Reconstruct TTM from quarterly data if no TTM is available:
    - Income/Cash flow items: Sum last 4 quarters
    - Balance sheet items: Use most recent quarter
    """
    
    @pytest.mark.asyncio
    async def test_reconstructs_ttm_from_quarterly_when_no_ttm_available(self, fmp_provider):
        """
        If FMP returns quarterly data but no TTM, we should reconstruct it.
        
        TTM Revenue = Q1 + Q2 + Q3 + Q4 = 100k * 4 = 400k
        """
        # Mock: FMP returns 4 quarterly periods but no TTM
        quarterly_income = [
            {"date": "2024-09-30", "period": "Q4", "revenue": 100_000, "netIncome": 25_000},
            {"date": "2024-06-30", "period": "Q3", "revenue": 100_000, "netIncome": 25_000},
            {"date": "2024-03-31", "period": "Q2", "revenue": 100_000, "netIncome": 25_000},
            {"date": "2023-12-31", "period": "Q1", "revenue": 100_000, "netIncome": 25_000},
        ]
        quarterly_balance = [
            {"date": "2024-09-30", "totalAssets": 500_000, "totalDebt": 100_000},
            {"date": "2024-06-30", "totalAssets": 480_000, "totalDebt": 95_000},
        ]
        quarterly_cash_flow = [
            {"date": "2024-09-30", "period": "Q4", "freeCashFlow": 20_000, "depreciationAndAmortization": 5_000},
            {"date": "2024-06-30", "period": "Q3", "freeCashFlow": 20_000, "depreciationAndAmortization": 5_000},
            {"date": "2024-03-31", "period": "Q2", "freeCashFlow": 20_000, "depreciationAndAmortization": 5_000},
            {"date": "2023-12-31", "period": "Q1", "freeCashFlow": 20_000, "depreciationAndAmortization": 5_000},
        ]
        
        with patch.object(fmp_provider, "_request", new_callable=AsyncMock) as mock_request:
            # Return annual and quarterly data (no TTM)
            async def side_effect(endpoint, **kwargs):
                if endpoint == "/profile":
                    return [{"symbol": "TEST", "companyName": "Test Corp", "marketCap": 1_000_000}]
                elif endpoint == "/income-statement":
                    return quarterly_income
                elif endpoint == "/balance-sheet-statement":
                    return quarterly_balance
                elif endpoint == "/cash-flow-statement":
                    return quarterly_cash_flow
                elif "quarter" in endpoint:  # Quarterly endpoints
                    if "income" in endpoint:
                        return quarterly_income
                    elif "balance" in endpoint:
                        return quarterly_balance
                    elif "cash" in endpoint:
                        return quarterly_cash_flow
                return []
            
            mock_request.side_effect = side_effect
            
            stock_data = await fmp_provider.get_stock_data("TEST")
            
            # Should have a TTM statement reconstructed
            ttm_statements = [f for f in stock_data.financials if f.period == "ttm"]
            assert len(ttm_statements) >= 1, "Should have reconstructed TTM statement"
            
            ttm = ttm_statements[0]
            
            # TTM Revenue = sum of 4 quarters = 400_000
            assert ttm.revenue == 400_000, f"TTM revenue should be 400k, got {ttm.revenue}"
            
            # TTM Net Income = sum of 4 quarters = 100_000
            assert ttm.net_income == 100_000, f"TTM net income should be 100k, got {ttm.net_income}"
            
            # Balance sheet uses latest quarter
            assert ttm.total_assets == 500_000, f"TTM total_assets should be 500k (latest quarter)"
    
    @pytest.mark.asyncio
    async def test_does_not_reconstruct_if_ttm_already_exists(self, fmp_provider):
        """
        If FMP already returns TTM data, don't reconstruct.
        """
        # FMP returns TTM directly
        income_with_ttm = [
            {"date": "2024-09-30", "period": "TTM", "revenue": 450_000, "netIncome": 110_000},
            {"date": "2024-06-30", "period": "Q3", "revenue": 100_000, "netIncome": 25_000},
        ]
        balance_sheet = [{"date": "2024-09-30", "totalAssets": 500_000}]
        cash_flow = [{"date": "2024-09-30", "period": "TTM", "freeCashFlow": 85_000}]
        
        with patch.object(fmp_provider, "_request", new_callable=AsyncMock) as mock_request:
            async def side_effect(endpoint, **kwargs):
                if endpoint == "/profile":
                    return [{"symbol": "TEST", "companyName": "Test Corp", "marketCap": 1_000_000}]
                elif endpoint == "/income-statement":
                    return income_with_ttm
                elif endpoint == "/balance-sheet-statement":
                    return balance_sheet
                elif endpoint == "/cash-flow-statement":
                    return cash_flow
                return []
            
            mock_request.side_effect = side_effect
            
            stock_data = await fmp_provider.get_stock_data("TEST")
            
            # Should have exactly 1 TTM statement (the original one, not reconstructed)
            ttm_statements = [f for f in stock_data.financials if f.period == "ttm"]
            assert len(ttm_statements) == 1, "Should have exactly 1 TTM (original)"
            
            # Revenue should be the original TTM value, not reconstructed
            assert ttm_statements[0].revenue == 450_000
    
    @pytest.mark.asyncio
    async def test_skips_ttm_reconstruction_if_insufficient_quarters(self, fmp_provider):
        """
        Don't try to reconstruct TTM if we have fewer than 4 quarters.
        """
        # Only 2 quarters available
        quarterly_income = [
            {"date": "2024-09-30", "period": "Q4", "revenue": 100_000},
            {"date": "2024-06-30", "period": "Q3", "revenue": 100_000},
        ]
        
        with patch.object(fmp_provider, "_request", new_callable=AsyncMock) as mock_request:
            async def side_effect(endpoint, **kwargs):
                if endpoint == "/profile":
                    return [{"symbol": "TEST", "companyName": "Test Corp", "marketCap": 1_000_000}]
                elif endpoint == "/income-statement":
                    return quarterly_income
                elif endpoint == "/balance-sheet-statement":
                    return []
                elif endpoint == "/cash-flow-statement":
                    return []
                return []
            
            mock_request.side_effect = side_effect
            
            stock_data = await fmp_provider.get_stock_data("TEST")
            
            # Should NOT have a TTM statement
            ttm_statements = [f for f in stock_data.financials if f.period == "ttm"]
            assert len(ttm_statements) == 0, "Should not reconstruct TTM with < 4 quarters"
