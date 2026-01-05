import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStockEndpoint:
    @pytest.fixture
    def mock_fmp_data(self):
        return {
            "profile": {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "beta": 1.25,
                "marketCap": 3000000000000,
            },
            "income_statement": [
                {
                    "revenue": 383285000000,
                    "operatingIncome": 114301000000,
                    "incomeBeforeTax": 113736000000,
                    "incomeTaxExpense": 16741000000,
                    "interestExpense": 3933000000,
                    "weightedAverageShsOut": 15744231000,
                },
                {
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
                    "totalDebt": 111088000000,
                    "cashAndCashEquivalents": 29965000000,
                    "totalCurrentAssets": 143566000000,
                    "totalCurrentLiabilities": 145308000000,
                },
            ],
            "cash_flow": [
                {
                    "freeCashFlow": 99584000000,
                    "depreciationAndAmortization": 11519000000,
                    "capitalExpenditure": -10959000000,
                },
            ],
        }

    def test_get_stock_returns_data_and_hints(self, mock_fmp_data):
        with patch("app.main.FMP_API_KEY", "test_key"), \
             patch("app.main.FMPClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_stock_data = AsyncMock(return_value=mock_fmp_data)
            mock_instance.get_treasury_rate = AsyncMock(return_value=0.045)

            response = client.get("/api/stock/AAPL")

            assert response.status_code == 200
            result = response.json()
            
            # Check structure
            assert "symbol" in result
            assert "company_name" in result
            assert "data" in result
            assert "hints" in result
            assert "validation" in result
            
            # Check data (read-only from FMP)
            assert result["symbol"] == "AAPL"
            assert result["company_name"] == "Apple Inc."
            assert result["data"]["beta"] == 1.25
            assert result["data"]["market_cap"] == 3000000000000
            assert result["data"]["risk_free_rate"] == 0.045
            
            # Check hints (calculated from historical)
            assert "revenue_growth" in result["hints"]
            assert "operating_margin" in result["hints"]
            
            # Check validation
            assert "has_errors" in result["validation"]
            assert "has_warnings" in result["validation"]
            assert "errors" in result["validation"]
            assert "warnings" in result["validation"]

    def test_get_stock_without_api_key(self):
        with patch("app.main.FMP_API_KEY", ""):
            response = client.get("/api/stock/AAPL")
            assert response.status_code == 500
            assert "FMP_API_KEY" in response.json()["detail"]


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
        with patch("app.main.FMP_API_KEY", "test_key"):
            # Missing required fields should fail
            response = client.post(
                "/api/stock/AAPL/valuation",
                json={}
            )
            assert response.status_code == 422  # Validation error

    def test_run_valuation_with_all_inputs(self, mock_valuation_result):
        with patch("app.main.FMP_API_KEY", "test_key"), \
             patch("app.main.ValuationService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.value_stock = AsyncMock(return_value=mock_valuation_result)

            response = client.post(
                "/api/stock/AAPL/valuation",
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
        with patch("app.main.FMP_API_KEY", "test_key"), \
             patch("app.main.ValuationService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.value_stock = AsyncMock(return_value=mock_valuation_result)

            response = client.post(
                "/api/stock/AAPL/valuation",
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
