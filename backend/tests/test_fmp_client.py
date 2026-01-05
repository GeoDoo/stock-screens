import pytest
from unittest.mock import AsyncMock, patch
from app.services.fmp_client import FMPClient


@pytest.fixture
def fmp_client():
    return FMPClient(api_key="test_key")


class TestFMPClient:
    @pytest.mark.asyncio
    async def test_get_profile(self, fmp_client):
        mock_response = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "mktCap": 3000000000000,
            }
        ]

        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await fmp_client.get_profile("AAPL")

            mock_request.assert_called_once_with("/profile/AAPL")
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

            mock_request.assert_called_once_with("/income-statement/AAPL", limit=5)
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

            mock_request.assert_called_once_with("/balance-sheet-statement/AAPL", limit=5)
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

            mock_request.assert_called_once_with("/cash-flow-statement/AAPL", limit=5)
            assert result[0]["freeCashFlow"] == 99584000000

    @pytest.mark.asyncio
    async def test_get_ratios(self, fmp_client):
        mock_response = [
            {
                "date": "2023-09-30",
                "symbol": "AAPL",
                "peRatio": 28.5,
                "pbRatio": 45.2,
                "returnOnEquity": 1.56,
            }
        ]

        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await fmp_client.get_ratios("AAPL")

            mock_request.assert_called_once_with("/ratios/AAPL", limit=5)
            assert result[0]["peRatio"] == 28.5

    @pytest.mark.asyncio
    async def test_get_historical_prices(self, fmp_client):
        mock_response = {
            "symbol": "AAPL",
            "historical": [
                {"date": "2024-01-02", "open": 185.0, "high": 186.0, "low": 184.0, "close": 185.5, "volume": 50000000},
                {"date": "2024-01-03", "open": 185.5, "high": 187.0, "low": 185.0, "close": 186.0, "volume": 45000000},
            ],
        }

        with patch.object(fmp_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await fmp_client.get_historical_prices("AAPL")

            mock_request.assert_called_once_with("/historical-price-full/AAPL")
            assert result["symbol"] == "AAPL"
            assert len(result["historical"]) == 2

    @pytest.mark.asyncio
    async def test_get_stock_data_aggregates_all(self, fmp_client):
        """Test that get_stock_data fetches all required data for analysis."""
        with patch.object(fmp_client, "get_profile", new_callable=AsyncMock) as mock_profile, \
             patch.object(fmp_client, "get_income_statement", new_callable=AsyncMock) as mock_income, \
             patch.object(fmp_client, "get_balance_sheet", new_callable=AsyncMock) as mock_balance, \
             patch.object(fmp_client, "get_cash_flow", new_callable=AsyncMock) as mock_cash, \
             patch.object(fmp_client, "get_ratios", new_callable=AsyncMock) as mock_ratios, \
             patch.object(fmp_client, "get_historical_prices", new_callable=AsyncMock) as mock_prices:

            mock_profile.return_value = {"symbol": "AAPL", "companyName": "Apple Inc."}
            mock_income.return_value = [{"revenue": 100}]
            mock_balance.return_value = [{"totalAssets": 200}]
            mock_cash.return_value = [{"freeCashFlow": 50}]
            mock_ratios.return_value = [{"peRatio": 25}]
            mock_prices.return_value = {"historical": []}

            result = await fmp_client.get_stock_data("AAPL")

            assert "profile" in result
            assert "income_statement" in result
            assert "balance_sheet" in result
            assert "cash_flow" in result
            assert "ratios" in result
            assert "historical_prices" in result

