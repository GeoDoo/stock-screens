import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement


client = TestClient(app)


def create_mock_stock_data(
    symbol="AAPL",
    name="Apple Inc.",
    industry="Consumer Electronics",
    sector="Technology",
    beta=1.25,
    market_cap=3000000000000,
    shares_outstanding=15744231000,
    price=190.0,
):
    """Create a mock StockData object for testing."""
    return StockData(
        profile=CompanyProfile(
            symbol=symbol,
            name=name,
            price=price,
            market_cap=market_cap,
            beta=beta,
            shares_outstanding=shares_outstanding,
            currency="USD",
            exchange="NASDAQ",
            industry=industry,
            sector=sector,
        ),
        financials=[
            FinancialStatement(
                date="2024-01-01",
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
                date="2023-01-01",
                period="annual",
                revenue=365817000000,
                cost_of_revenue=208000000000,
                gross_profit=157817000000,
                operating_income=108949000000,
                net_income=94680000000,
                interest_expense=2645000000,
                income_tax_expense=14527000000,
                total_assets=330000000000,
                total_liabilities=268000000000,
                total_equity=62000000000,
                total_debt=100000000000,
                cash_and_equivalents=25000000000,
                current_assets=140000000000,
                current_liabilities=140000000000,
                operating_cash_flow=100000000000,
                capital_expenditure=-10000000000,
                free_cash_flow=90000000000,
                depreciation_amortization=11000000000,
            ),
        ],
        provider="fmp",
    )


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStockEndpoint:
    def test_get_stock_returns_data_and_hints(self):
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL?provider=fmp")

            assert response.status_code == 200
            result = response.json()
            
            # Check structure
            assert "symbol" in result
            assert "company_name" in result
            assert "industry" in result
            assert "sector" in result
            assert "data" in result
            assert "hints" in result
            assert "validation" in result
            
            # Check data (read-only from provider)
            assert result["symbol"] == "AAPL"
            assert result["company_name"] == "Apple Inc."
            assert result["industry"] == "Consumer Electronics"
            assert result["sector"] == "Technology"
            assert result["data"]["beta"] == 1.25
            assert result["data"]["market_cap"] == 3000000000000
            assert result["data"]["risk_free_rate"] == 0.045
            
            # Check hints (calculated from historical)
            assert "revenue_growth" in result["hints"]
            assert "operating_margin" in result["hints"]
            
            # Check validation
            assert "has_errors" in result["validation"]
            assert "has_warnings" in result["validation"]

    def test_get_stock_without_api_key(self):
        with patch("app.main.FMP_API_KEY", ""):
            response = client.get("/api/stock/AAPL?provider=fmp")
            assert response.status_code == 400
            assert "API key" in response.json()["detail"]

    def test_get_stock_handles_missing_industry_sector(self):
        """Industry and sector should be None if not provided by provider."""
        mock_stock_data = create_mock_stock_data(
            symbol="TEST",
            name="Test Corp",
            industry=None,
            sector=None,
            beta=1.0,
            market_cap=1000000000,
        )
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/TEST?provider=fmp")
            
            assert response.status_code == 200
            result = response.json()
            assert result["industry"] is None
            assert result["sector"] is None

    def test_get_stock_unknown_provider(self):
        """Unknown provider should return 400."""
        response = client.get("/api/stock/AAPL?provider=invalid")
        assert response.status_code == 400
        assert "Unknown provider" in response.json()["detail"]


class TestValuationEndpoint:
    @pytest.fixture
    def mock_valuation_result(self):
        return {
            "symbol": "AAPL",
            "intrinsic_value_per_share": 187.45,
            "enterprise_value": 3100000000000,
            "equity_value": 3018877000000,
            "market_cap": 3000000000000,
            "wacc": 0.0923,
            "projections": [],
            "inputs": {},
        }

    def test_run_valuation_requires_all_inputs(self):
        """Valuation should require all user inputs."""
        mock_client = MagicMock()
        with patch("app.main.get_client_for_provider", return_value=mock_client):
            # Missing required fields should fail
            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={}
            )
            assert response.status_code == 422  # Validation error

    def test_run_valuation_with_all_inputs(self, mock_valuation_result):
        mock_client = MagicMock()
        with patch("app.main.get_client_for_provider", return_value=mock_client), \
             patch("app.main.ValuationService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.value_stock = AsyncMock(return_value=mock_valuation_result)

            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.10,
                    "operating_margin": 0.30,
                    "terminal_growth_rate": 0.03,
                    "market_risk_premium": 0.06,
                    "projection_years": 5,
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["intrinsic_value_per_share"] == 187.45

    def test_run_valuation_passes_user_inputs(self, mock_valuation_result):
        mock_client = MagicMock()
        with patch("app.main.get_client_for_provider", return_value=mock_client), \
             patch("app.main.ValuationService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.value_stock = AsyncMock(return_value=mock_valuation_result)

            response = client.post(
                "/api/stock/AAPL/valuation?provider=fmp",
                json={
                    "revenue_growth": 0.15,
                    "operating_margin": 0.32,
                    "terminal_growth_rate": 0.025,
                    "market_risk_premium": 0.07,
                    "projection_years": 10,
                }
            )

            assert response.status_code == 200
            # Verify user inputs were passed correctly
            mock_instance.value_stock.assert_called_once()
            call_kwargs = mock_instance.value_stock.call_args.kwargs
            assert call_kwargs["revenue_growth"] == 0.15
            assert call_kwargs["operating_margin"] == 0.32
            assert call_kwargs["terminal_growth_rate"] == 0.025
            assert call_kwargs["market_risk_premium"] == 0.07
            assert call_kwargs["projection_years"] == 10


class TestScenarioEndpoint:
    def test_scenarios_with_custom_discount_rate(self):
        """Scenario analysis should accept custom discount rate override."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/scenarios?provider=fmp",
                json={
                    "projection_years": 10,
                    "market_risk_premium": 0.06,
                    "discount_rate_override": 0.10,  # Custom 10% rate
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "scenarios" in data
            assert data["wacc"] == 0.10  # Should use our custom rate

    def test_scenarios_without_wacc_requires_custom_rate(self):
        """Scenario analysis should fail if WACC unavailable and no custom rate."""
        # Create stock data with missing beta (WACC can't be calculated)
        mock_stock_data = create_mock_stock_data(beta=None)
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/scenarios?provider=fmp",
                json={
                    "projection_years": 10,
                    "market_risk_premium": 0.06,
                    # No discount_rate_override provided
                }
            )
            
            assert response.status_code == 400
            assert "Cannot calculate WACC" in response.json()["detail"]

    def test_scenarios_with_missing_beta_and_custom_rate_succeeds(self):
        """Scenario analysis should work with custom rate even if beta missing."""
        # Create stock data with missing beta
        mock_stock_data = create_mock_stock_data(beta=None)
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            response = client.post(
                "/api/stock/AAPL/scenarios?provider=fmp",
                json={
                    "projection_years": 10,
                    "market_risk_premium": 0.06,
                    "discount_rate_override": 0.12,  # Custom rate bypasses WACC
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["wacc"] == 0.12  # Uses our custom rate
