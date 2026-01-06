"""
Tests for HistoricalValuationAnalyzer service.
"""
import pytest
from app.services.historical_valuation import (
    HistoricalValuationAnalyzer,
    HistoricalValuation,
    YearlyMetrics,
)


@pytest.fixture
def sample_financials():
    """Sample 5 years of financials with consistent growth."""
    # Year 1 to 5 with revenue and earnings growth
    return [
        {
            "date": "2024-12-31",
            "revenue": 400000000000,  # 400B
            "operating_income": 120000000000,  # 120B
            "net_income": 100000000000,  # 100B
            "total_assets": 350000000000,
            "total_debt": 100000000000,
            "cash_and_equivalents": 25000000000,
            "total_equity": 60000000000,
            "depreciation_amortization": 10000000000,
        },
        {
            "date": "2023-12-31",
            "revenue": 360000000000,
            "operating_income": 105000000000,
            "net_income": 88000000000,
            "total_assets": 330000000000,
            "total_debt": 95000000000,
            "cash_and_equivalents": 22000000000,
            "total_equity": 55000000000,
            "depreciation_amortization": 9000000000,
        },
        {
            "date": "2022-12-31",
            "revenue": 330000000000,
            "operating_income": 95000000000,
            "net_income": 80000000000,
            "total_assets": 310000000000,
            "total_debt": 90000000000,
            "cash_and_equivalents": 20000000000,
            "total_equity": 50000000000,
            "depreciation_amortization": 8500000000,
        },
        {
            "date": "2021-12-31",
            "revenue": 300000000000,
            "operating_income": 85000000000,
            "net_income": 70000000000,
            "total_assets": 290000000000,
            "total_debt": 85000000000,
            "cash_and_equivalents": 18000000000,
            "total_equity": 45000000000,
            "depreciation_amortization": 8000000000,
        },
        {
            "date": "2020-12-31",
            "revenue": 275000000000,
            "operating_income": 75000000000,
            "net_income": 60000000000,
            "total_assets": 270000000000,
            "total_debt": 80000000000,
            "cash_and_equivalents": 15000000000,
            "total_equity": 40000000000,
            "depreciation_amortization": 7500000000,
        },
    ]


@pytest.fixture
def sample_profile():
    """Sample current company profile."""
    return {
        "price": 150.0,
        "market_cap": 2400000000000,  # 2.4T
        "shares_outstanding": 16000000000,
    }


@pytest.fixture
def analyzer():
    return HistoricalValuationAnalyzer()


class TestHistoricalValuation:
    """Tests for historical valuation analysis."""

    def test_analyze_basic(self, analyzer, sample_financials, sample_profile):
        """Basic analysis with multiple years."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        assert result.current_pe is not None
        assert result.avg_pe_5yr is not None
        assert len(result.yearly_metrics) > 0

    def test_current_pe(self, analyzer, sample_financials, sample_profile):
        """Calculate current P/E ratio."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # Market cap / Net income = 2.4T / 100B = 24
        assert result.current_pe == pytest.approx(24.0, rel=0.1)

    def test_current_ps(self, analyzer, sample_financials, sample_profile):
        """Calculate current P/S ratio."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # Market cap / Revenue = 2.4T / 400B = 6
        assert result.current_ps == pytest.approx(6.0, rel=0.1)

    def test_current_pb(self, analyzer, sample_financials, sample_profile):
        """Calculate current P/B ratio."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # Market cap / Equity = 2.4T / 60B = 40
        assert result.current_pb == pytest.approx(40.0, rel=0.1)

    def test_current_ev_ebitda(self, analyzer, sample_financials, sample_profile):
        """Calculate current EV/EBITDA."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # EV = Market cap + Debt - Cash = 2.4T + 100B - 25B = 2.475T
        # EBITDA = Operating income + D&A = 120B + 10B = 130B
        # EV/EBITDA = 2.475T / 130B ≈ 19
        assert result.current_ev_ebitda is not None
        assert result.current_ev_ebitda > 15
        assert result.current_ev_ebitda < 25

    def test_average_calculations(self, analyzer, sample_financials, sample_profile):
        """Calculate 5-year averages."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # Should have averages for all metrics
        assert result.avg_pe_5yr is not None
        assert result.avg_ps_5yr is not None
        assert result.avg_pb_5yr is not None
        assert result.avg_ev_ebitda_5yr is not None

    def test_premium_discount_calculation(self, analyzer, sample_financials, sample_profile):
        """Calculate premium/discount vs historical."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # premium_discount_pe = (current_pe - avg_pe) / avg_pe
        assert result.premium_discount_pe is not None

    def test_yearly_metrics(self, analyzer, sample_financials, sample_profile):
        """Get metrics for each year."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # Should have data for each year
        assert len(result.yearly_metrics) == 5
        
        # Each year should have metrics
        for ym in result.yearly_metrics:
            assert ym.year is not None
            assert ym.pe is not None or ym.net_income is None  # PE can be None if no earnings

    def test_valuation_assessment(self, analyzer, sample_financials, sample_profile):
        """Generate valuation assessment."""
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # Should have assessment strings
        assert result.pe_assessment in ["cheap", "fair", "expensive"]
        assert result.ps_assessment in ["cheap", "fair", "expensive"]


class TestEdgeCases:
    """Tests for edge cases."""

    def test_single_year(self, analyzer, sample_profile):
        """Handle single year of data."""
        financials = [{
            "date": "2024-12-31",
            "revenue": 100000000000,
            "net_income": 10000000000,
            "total_equity": 50000000000,
        }]
        
        result = analyzer.analyze(financials, sample_profile)
        
        assert result.current_pe is not None
        assert result.avg_pe_5yr is None  # Can't calculate average with one year

    def test_missing_net_income(self, analyzer, sample_profile):
        """Handle missing net income (loss-making company)."""
        financials = [{
            "date": "2024-12-31",
            "revenue": 100000000000,
            "net_income": None,
            "total_equity": 50000000000,
        }]
        
        result = analyzer.analyze(financials, sample_profile)
        
        assert result.current_pe is None
        assert result.current_ps is not None  # P/S still works

    def test_negative_earnings(self, analyzer, sample_profile):
        """Handle negative earnings."""
        financials = [{
            "date": "2024-12-31",
            "revenue": 100000000000,
            "net_income": -10000000000,  # Loss
            "total_equity": 50000000000,
        }]
        
        result = analyzer.analyze(financials, sample_profile)
        
        # P/E doesn't make sense for losses
        assert result.current_pe is None

    def test_missing_price_data(self, analyzer, sample_financials):
        """Handle missing market data."""
        profile = {"price": None, "market_cap": None, "shares_outstanding": None}
        
        result = analyzer.analyze(sample_financials, profile)
        
        # Can't calculate current multiples without price
        assert result.current_pe is None
        assert result.current_ps is None

    def test_empty_financials(self, analyzer, sample_profile):
        """Handle no financial data."""
        result = analyzer.analyze([], sample_profile)
        
        assert result.current_pe is None
        assert result.avg_pe_5yr is None
        assert len(result.yearly_metrics) == 0


