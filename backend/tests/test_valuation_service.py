import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.valuation_service import ValuationService


class TestValuationService:
    @pytest.fixture
    def mock_fmp_data(self):
        """Realistic FMP data for testing."""
        return {
            "profile": {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "beta": 1.25,
                "marketCap": 3000000000000,
            },
            "income_statement": [
                {
                    "date": "2023-09-30",
                    "revenue": 383285000000,
                    "operatingIncome": 114301000000,
                    "incomeBeforeTax": 113736000000,
                    "incomeTaxExpense": 16741000000,
                    "interestExpense": 3933000000,
                    "weightedAverageShsOut": 15744231000,
                },
                {
                    "date": "2022-09-30",
                    "revenue": 394328000000,
                    "operatingIncome": 119437000000,
                    "incomeBeforeTax": 119103000000,
                    "incomeTaxExpense": 19300000000,
                    "interestExpense": 2931000000,
                    "weightedAverageShsOut": 16215963000,
                },
                {
                    "date": "2021-09-30",
                    "revenue": 365817000000,
                    "operatingIncome": 108949000000,
                    "incomeBeforeTax": 109207000000,
                    "incomeTaxExpense": 14527000000,
                    "interestExpense": 2645000000,
                    "weightedAverageShsOut": 16701272000,
                },
            ],
            "balance_sheet": [
                {
                    "date": "2023-09-30",
                    "totalDebt": 111088000000,
                    "cashAndCashEquivalents": 29965000000,
                    "totalCurrentAssets": 143566000000,
                    "totalCurrentLiabilities": 145308000000,
                },
                {
                    "date": "2022-09-30",
                    "totalDebt": 120069000000,
                    "cashAndCashEquivalents": 23646000000,
                    "totalCurrentAssets": 135405000000,
                    "totalCurrentLiabilities": 153982000000,
                },
                {
                    "date": "2021-09-30",
                    "totalDebt": 124719000000,
                    "cashAndCashEquivalents": 34940000000,
                    "totalCurrentAssets": 134836000000,
                    "totalCurrentLiabilities": 125481000000,
                },
            ],
            "cash_flow": [
                {
                    "date": "2023-09-30",
                    "freeCashFlow": 99584000000,
                    "depreciationAndAmortization": 11519000000,
                    "capitalExpenditure": -10959000000,
                },
                {
                    "date": "2022-09-30",
                    "freeCashFlow": 111443000000,
                    "depreciationAndAmortization": 11104000000,
                    "capitalExpenditure": -10708000000,
                },
                {
                    "date": "2021-09-30",
                    "freeCashFlow": 92953000000,
                    "depreciationAndAmortization": 11284000000,
                    "capitalExpenditure": -11085000000,
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_valuation_returns_intrinsic_value(self, mock_fmp_data):
        """Full valuation should return intrinsic value per share."""
        service = ValuationService(api_key="test_key")

        with patch.object(service.fmp_client, "get_stock_data", new_callable=AsyncMock) as mock_get_data, \
             patch.object(service.fmp_client, "get_treasury_rate", new_callable=AsyncMock) as mock_treasury:
            mock_get_data.return_value = mock_fmp_data
            mock_treasury.return_value = 0.045  # 4.5%

            result = await service.value_stock("AAPL")

            assert "intrinsic_value_per_share" in result
            assert "current_price" in result or "market_cap" in result
            assert result["intrinsic_value_per_share"] > 0

    @pytest.mark.asyncio
    async def test_valuation_includes_wacc(self, mock_fmp_data):
        """Valuation should calculate and include WACC."""
        service = ValuationService(api_key="test_key")

        with patch.object(service.fmp_client, "get_stock_data", new_callable=AsyncMock) as mock_get_data, \
             patch.object(service.fmp_client, "get_treasury_rate", new_callable=AsyncMock) as mock_treasury:
            mock_get_data.return_value = mock_fmp_data
            mock_treasury.return_value = 0.045

            result = await service.value_stock("AAPL")

            assert "wacc" in result
            assert 0 < result["wacc"] < 0.20  # Reasonable WACC range

    @pytest.mark.asyncio
    async def test_valuation_includes_fcf_projections(self, mock_fmp_data):
        """Valuation should include FCF projections."""
        service = ValuationService(api_key="test_key")

        with patch.object(service.fmp_client, "get_stock_data", new_callable=AsyncMock) as mock_get_data, \
             patch.object(service.fmp_client, "get_treasury_rate", new_callable=AsyncMock) as mock_treasury:
            mock_get_data.return_value = mock_fmp_data
            mock_treasury.return_value = 0.045

            result = await service.value_stock("AAPL", projection_years=5)

            assert "projections" in result
            assert len(result["projections"]) == 5

    @pytest.mark.asyncio
    async def test_valuation_allows_growth_override(self, mock_fmp_data):
        """User should be able to override growth rate."""
        service = ValuationService(api_key="test_key")

        with patch.object(service.fmp_client, "get_stock_data", new_callable=AsyncMock) as mock_get_data, \
             patch.object(service.fmp_client, "get_treasury_rate", new_callable=AsyncMock) as mock_treasury:
            mock_get_data.return_value = mock_fmp_data
            mock_treasury.return_value = 0.045

            result_default = await service.value_stock("AAPL")
            result_high_growth = await service.value_stock("AAPL", revenue_growth=0.15)

            # Higher growth should give higher intrinsic value
            assert result_high_growth["intrinsic_value_per_share"] > result_default["intrinsic_value_per_share"]

