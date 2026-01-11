"""Tests for elite valuation API endpoints (Monte Carlo, Capital Efficiency)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement


client = TestClient(app)


class TestMonteCarloAPI:
    """Tests for the Monte Carlo simulation endpoint."""
    
    @pytest.fixture
    def mock_stock_data(self):
        """Mock stock data response using proper dataclasses."""
        profile = CompanyProfile(
            symbol="AAPL",
            name="Apple Inc",
            price=180.0,
            market_cap=3000000000000,
            beta=1.2,
            shares_outstanding=15000000000,
            industry="Technology",
            sector="Technology",
        )
        
        financials = [
            FinancialStatement(
                date="2024-01-01",
                period="annual",
                revenue=400000000000,
                operating_income=100000000000,
                total_debt=100000000000,
                cash_and_equivalents=60000000000,
                depreciation_amortization=10000000000,
                capital_expenditure=-12000000000,
                current_assets=100000000000,
                current_liabilities=80000000000,
            ),
            FinancialStatement(
                date="2023-01-01",
                period="annual",
                revenue=380000000000,
                operating_income=95000000000,
            ),
        ]
        
        return StockData(
            profile=profile,
            financials=financials,
            provider="yahoo",
        )
    
    @patch("app.routers.stock.get_client_for_provider")
    def test_monte_carlo_returns_distribution(self, mock_get_client, mock_stock_data):
        """Monte Carlo endpoint returns value distribution."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/api/stock/AAPL/monte-carlo?provider=yahoo",
            json={
                "base_growth": 0.10,
                "growth_std": 0.03,
                "base_margin": 0.25,
                "margin_std": 0.02,
                "base_discount_rate": 0.10,
                "discount_std": 0.01,
                "terminal_growth": 0.03,
                "projection_years": 5,
                "iterations": 100,  # Small for test speed
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert data["symbol"] == "AAPL"
        assert data["iterations"] == 100
        assert data["valid_simulations"] > 0
        
        # Enterprise value distribution
        assert "enterprise_value" in data
        assert "mean" in data["enterprise_value"]
        assert "std_dev" in data["enterprise_value"]
        assert "percentiles" in data["enterprise_value"]
        
        # Per-share values
        assert "per_share" in data
        assert "mean" in data["per_share"]
        assert "percentiles" in data["per_share"]
        
        # Percentiles should be ordered
        percentiles = data["enterprise_value"]["percentiles"]
        assert percentiles["p10"] <= percentiles["p50"]
        assert percentiles["p50"] <= percentiles["p90"]
    
    @patch("app.routers.stock.get_client_for_provider")
    def test_monte_carlo_includes_inputs(self, mock_get_client, mock_stock_data):
        """Monte Carlo response includes the input parameters used."""
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/api/stock/TEST/monte-carlo?provider=yahoo",
            json={
                "base_growth": 0.15,
                "growth_std": 0.05,
                "base_margin": 0.20,
                "margin_std": 0.03,
                "base_discount_rate": 0.08,
                "discount_std": 0.02,
                "terminal_growth": 0.025,
                "projection_years": 7,
                "iterations": 50,
            },
        )
        
        assert response.status_code == 200
        inputs = response.json()["inputs"]
        
        assert inputs["base_growth"] == 0.15
        assert inputs["growth_std"] == 0.05
        assert inputs["base_margin"] == 0.20
        assert inputs["projection_years"] == 7
    
    @patch("app.routers.stock.get_client_for_provider")
    def test_monte_carlo_uses_full_equity_bridge(self, mock_get_client):
        """
        P1 Fix: Quick Monte Carlo should use full equity bridge, not just net debt.
        
        Bug: EV→equity conversion only subtracted net debt, ignoring:
        - Minority interest (reduces equity)
        - Preferred stock (reduces equity)
        - Deferred tax assets (adds to equity)
        - Pension deficit (reduces equity)
        
        For a company with significant MI/preferred/pensions, per-share values
        would be overstated.
        """
        profile = CompanyProfile(
            symbol="AAPL",
            name="Apple Inc",
            price=180.0,
            market_cap=3000000000000,
            beta=1.2,
            shares_outstanding=1000000000,  # 1B shares
            industry="Technology",
            sector="Technology",
        )
        
        financials = [
            FinancialStatement(
                date="2024-01-01",
                period="annual",
                revenue=400000000000,
                operating_income=100000000000,
                total_debt=100000000000,  # 100B debt
                cash_and_equivalents=60000000000,  # 60B cash -> Net debt = 40B
                depreciation_amortization=10000000000,
                capital_expenditure=-12000000000,
                current_assets=100000000000,
                current_liabilities=80000000000,
                # Add equity bridge components
                minority_interest=20000000000,  # 20B minority interest
                preferred_stock=5000000000,  # 5B preferred stock
                deferred_tax_assets=3000000000,  # 3B DTA (adds to equity)
                pension_liability=2000000000,  # 2B pension deficit
            ),
            FinancialStatement(
                date="2023-01-01",
                period="annual",
                revenue=380000000000,
                operating_income=95000000000,
            ),
        ]
        
        stock_data = StockData(
            profile=profile,
            financials=financials,
            provider="yahoo",
        )
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=stock_data)
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/api/stock/AAPL/monte-carlo?provider=yahoo",
            json={
                "base_growth": 0.10,
                "growth_std": 0.03,
                "base_margin": 0.25,
                "margin_std": 0.02,
                "base_discount_rate": 0.10,
                "discount_std": 0.01,
                "terminal_growth": 0.03,
                "projection_years": 5,
                "iterations": 100,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # P1: Response should include equity bridge info for transparency
        assert "equity_bridge" in data, \
            "Response should include equity_bridge components for transparency"
        
        bridge = data["equity_bridge"]
        
        # Verify bridge components are present and correct
        assert bridge["net_debt"] == 40000000000  # 100B - 60B
        assert bridge["minority_interest"] == 20000000000
        assert bridge["preferred_stock"] == 5000000000
        assert bridge["deferred_tax_assets"] == 3000000000
        assert bridge["pension_deficit"] == 2000000000
        
        # Calculate expected equity adjustment:
        # Net debt = 40B
        # + Minority interest = 20B (reduces equity)
        # + Preferred stock = 5B (reduces equity)
        # - Deferred tax assets = 3B (adds to equity)
        # + Pension deficit = 2B (reduces equity)
        # Total EV→Equity adjustment = 40 + 20 + 5 - 3 + 2 = 64B
        
        # With full bridge, equity is lower than with net debt only
        # This means per_share should be lower than if we just used net debt
        # With mean EV, verify the math is correct
        mean_ev = data["enterprise_value"]["mean"]
        mean_per_share = data["per_share"]["mean"]
        shares = 1000000000
        
        expected_equity = mean_ev - 64000000000  # Full equity bridge
        expected_per_share = expected_equity / shares
        
        assert abs(mean_per_share - expected_per_share) < 0.01, \
            f"Per share should use full equity bridge. Expected ~{expected_per_share:.2f}, got {mean_per_share:.2f}"


class TestCapitalEfficiencyAPI:
    """Tests for the capital efficiency endpoint."""
    
    def test_capital_efficiency_value_creator(self):
        """Test analysis of a value-creating company."""
        response = client.post(
            "/api/capital-efficiency",
            json={
                "nopat": 200,
                "invested_capital": 1000,  # ROIC = 20%
                "revenue_growth": 0.10,
                "wacc": 0.10,  # WACC = 10%
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["roic"] == 0.20
        assert data["roic_formatted"] == "20.0%"
        assert data["is_value_creating"] is True
        assert abs(data["value_spread"] - 0.10) < 0.001  # 20% - 10%
        # Assessment should indicate value creation (modest or strong)
        assert "creator" in data["assessment"].lower() or "exceeds" in data["assessment"].lower()
    
    def test_capital_efficiency_value_destroyer(self):
        """Test analysis of a value-destroying company."""
        response = client.post(
            "/api/capital-efficiency",
            json={
                "nopat": 50,
                "invested_capital": 1000,  # ROIC = 5%
                "revenue_growth": 0.15,
                "wacc": 0.12,  # WACC = 12%
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["roic"] == 0.05
        assert data["is_value_creating"] is False
        assert abs(data["value_spread"] - (-0.07)) < 0.001  # 5% - 12%
        assert "destroyer" in data["assessment"].lower() or "reduces" in data["assessment"].lower()
    
    def test_capital_efficiency_reinvestment_rate(self):
        """Test reinvestment rate calculation."""
        response = client.post(
            "/api/capital-efficiency",
            json={
                "nopat": 100,
                "invested_capital": 500,  # ROIC = 20%
                "revenue_growth": 0.10,  # 10% growth
                "wacc": 0.10,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Reinvestment rate = growth / ROIC = 10% / 20% = 50%
        assert abs(data["reinvestment_rate"] - 0.50) < 0.001
        assert data["reinvestment_rate_formatted"] == "50.0%"
    
    def test_capital_efficiency_economic_profit(self):
        """Test economic profit (EVA) calculation."""
        response = client.post(
            "/api/capital-efficiency",
            json={
                "nopat": 200,
                "invested_capital": 1000,  # ROIC = 20%
                "revenue_growth": 0.10,
                "wacc": 0.10,  # Spread = 10%
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Economic profit = (ROIC - WACC) × Invested Capital
        # = (20% - 10%) × 1000 = 100
        assert abs(data["economic_profit"] - 100) < 0.1
    
    def test_capital_efficiency_zero_invested_capital(self):
        """Handle zero invested capital gracefully."""
        response = client.post(
            "/api/capital-efficiency",
            json={
                "nopat": 100,
                "invested_capital": 0,
                "revenue_growth": 0.10,
                "wacc": 0.10,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["roic"] is None
        assert data["roic_formatted"] is None
