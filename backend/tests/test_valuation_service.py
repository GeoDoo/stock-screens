import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.valuation_service import ValuationService
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement


def create_mock_stock_data():
    """Create realistic mock stock data for testing."""
    return StockData(
        profile=CompanyProfile(
            symbol="AAPL",
            name="Apple Inc.",
            price=190.0,
            market_cap=3000000000000,
            beta=1.25,
            shares_outstanding=15744231000,
            currency="USD",
            exchange="NASDAQ",
            industry="Consumer Electronics",
            sector="Technology",
        ),
        financials=[
            FinancialStatement(
                date="2023-09-30",
                period="annual",
                revenue=383285000000,
                cost_of_revenue=214137000000,
                gross_profit=169148000000,
                operating_income=114301000000,
                net_income=96995000000,
                interest_expense=3933000000,
                income_tax_expense=16741000000,
                total_assets=352583000000,
                total_liabilities=290437000000,
                total_equity=62146000000,
                total_debt=111088000000,
                cash_and_equivalents=29965000000,
                current_assets=143566000000,
                current_liabilities=145308000000,
                operating_cash_flow=110543000000,
                capital_expenditure=-10959000000,
                free_cash_flow=99584000000,
                depreciation_amortization=11519000000,
            ),
            FinancialStatement(
                date="2022-09-30",
                period="annual",
                revenue=394328000000,
                cost_of_revenue=223546000000,
                gross_profit=170782000000,
                operating_income=119437000000,
                net_income=99803000000,
                interest_expense=2931000000,
                income_tax_expense=19300000000,
                total_assets=352755000000,
                total_liabilities=302083000000,
                total_equity=50672000000,
                total_debt=120069000000,
                cash_and_equivalents=23646000000,
                current_assets=135405000000,
                current_liabilities=153982000000,
                operating_cash_flow=122151000000,
                capital_expenditure=-10708000000,
                free_cash_flow=111443000000,
                depreciation_amortization=11104000000,
            ),
            FinancialStatement(
                date="2021-09-30",
                period="annual",
                revenue=365817000000,
                cost_of_revenue=212981000000,
                gross_profit=152836000000,
                operating_income=108949000000,
                net_income=94680000000,
                interest_expense=2645000000,
                income_tax_expense=14527000000,
                total_assets=351002000000,
                total_liabilities=287912000000,
                total_equity=63090000000,
                total_debt=124719000000,
                cash_and_equivalents=34940000000,
                current_assets=134836000000,
                current_liabilities=125481000000,
                operating_cash_flow=104038000000,
                capital_expenditure=-11085000000,
                free_cash_flow=92953000000,
                depreciation_amortization=11284000000,
            ),
        ],
        provider="fmp",
    )


class TestValuationService:
    @pytest.fixture
    def mock_client(self):
        """Create a mock StockDataClient."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client

    @pytest.mark.asyncio
    async def test_valuation_returns_intrinsic_value(self, mock_client):
        """Full valuation should return intrinsic value per share."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL")

        assert "intrinsic_value_per_share" in result
        assert "market_cap" in result
        assert result["intrinsic_value_per_share"] > 0

    @pytest.mark.asyncio
    async def test_valuation_includes_wacc(self, mock_client):
        """Valuation should calculate and include WACC."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL")

        assert "wacc" in result
        assert 0 < result["wacc"] < 0.20  # Reasonable WACC range

    @pytest.mark.asyncio
    async def test_valuation_includes_fcf_projections(self, mock_client):
        """Valuation should include FCF projections."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL", projection_years=5)

        assert "projections" in result
        assert len(result["projections"]) == 5

    @pytest.mark.asyncio
    async def test_valuation_allows_growth_override(self, mock_client):
        """User should be able to override growth rate."""
        service = ValuationService(client=mock_client)

        result_default = await service.value_stock("AAPL", revenue_growth=0.05)
        
        # Reset mock to ensure fresh call
        mock_client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        result_high_growth = await service.value_stock("AAPL", revenue_growth=0.15)

        # Higher growth should give higher intrinsic value
        assert result_high_growth["intrinsic_value_per_share"] > result_default["intrinsic_value_per_share"]

    @pytest.mark.asyncio
    async def test_valuation_with_custom_discount_rate(self, mock_client):
        """User should be able to override discount rate."""
        service = ValuationService(client=mock_client)

        result_default = await service.value_stock("AAPL")
        
        # Reset mock
        mock_client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        result_custom = await service.value_stock("AAPL", discount_rate_override=0.15)

        # Higher discount rate should give lower intrinsic value
        assert result_custom["intrinsic_value_per_share"] < result_default["intrinsic_value_per_share"]
        assert result_custom["using_custom_discount_rate"] is True
