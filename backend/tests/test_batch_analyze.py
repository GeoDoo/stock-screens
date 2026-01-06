"""Tests for batched analyze endpoint."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement

client = TestClient(app)


def create_mock_stock_data():
    """Create mock stock data for testing."""
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
                dividends_paid=-15000000000,
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
                dividends_paid=-14000000000,
            ),
        ],
        provider="fmp",
    )


class TestBatchAnalyzeEndpoint:
    """Tests for the /api/stock/{symbol}/analyze endpoint."""
    
    def test_batch_analyze_returns_all_data(self):
        """Batch analyze should return stock data, ratios, dividends, and historical valuation."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=["MSFT", "GOOGL"])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")

            assert response.status_code == 200
            data = response.json()
            
            # Should have all sections
            assert "stock" in data
            assert "ratios" in data
            assert "dividends" in data
            assert "historical_valuation" in data
            
            # Stock data should be present
            assert data["stock"]["symbol"] == "AAPL"
            assert data["stock"]["company_name"] == "Apple Inc."
    
    def test_batch_analyze_reduces_api_calls(self):
        """Batch analyze should make fewer API calls than individual endpoints."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=["MSFT", "GOOGL"])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")
            
            assert response.status_code == 200
            
            # Should only call get_stock_data once (not multiple times for each section)
            assert mock_client.get_stock_data.call_count == 1
    
    def test_batch_analyze_includes_rate_limit_stats(self):
        """Batch analyze should include rate limit statistics."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=[])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")

            assert response.status_code == 200
            data = response.json()
            
            assert "rate_limit" in data
            assert "used" in data["rate_limit"]
            assert "remaining" in data["rate_limit"]


class TestRateLimitEndpoint:
    """Tests for the /api/rate-limits endpoint."""
    
    def test_get_rate_limits(self):
        """Should return current rate limit stats for all providers."""
        response = client.get("/api/rate-limits")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fmp" in data
        assert "yahoo" in data
        assert "massive" in data
        
        # Each should have stats
        assert "used" in data["fmp"]
        assert "limit" in data["fmp"]
        assert "remaining" in data["fmp"]
    
    def test_reset_rate_limits(self):
        """Should be able to reset rate limit counts."""
        # First, make some calls to increment
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.main.get_client_for_provider", return_value=mock_client):
            client.get("/api/stock/AAPL?provider=fmp")
        
        # Reset
        response = client.post("/api/rate-limits/reset")
        assert response.status_code == 200
        
        # Check counts are reset
        response = client.get("/api/rate-limits")
        data = response.json()
        assert data["fmp"]["used"] == 0


