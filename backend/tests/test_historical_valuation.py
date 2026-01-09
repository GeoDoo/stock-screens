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

    def test_single_year_with_invalid_date_raises_error(self, analyzer, sample_profile):
        """
        P0 Bug: Single year with malformed date silently returns empty result.
        Should raise ValueError so caller knows data is bad.
        """
        financials = [{
            "date": "invalid-date",  # Malformed date
            "revenue": 100000000000,
            "net_income": 10000000000,
            "total_equity": 50000000000,
        }]
        
        with pytest.raises(ValueError, match="No valid financial years"):
            analyzer.analyze(financials, sample_profile)
    
    def test_single_year_with_missing_date_raises_error(self, analyzer, sample_profile):
        """
        Single year with missing date should raise error.
        """
        financials = [{
            "date": None,  # Missing date
            "revenue": 100000000000,
            "net_income": 10000000000,
        }]
        
        with pytest.raises(ValueError, match="No valid financial years"):
            analyzer.analyze(financials, sample_profile)
    
    def test_all_years_invalid_raises_error(self, analyzer, sample_profile):
        """
        If all years have invalid dates, should raise error.
        """
        financials = [
            {"date": "bad1", "revenue": 100},
            {"date": "bad2", "revenue": 200},
            {"date": None, "revenue": 300},
        ]
        
        with pytest.raises(ValueError, match="No valid financial years"):
            analyzer.analyze(financials, sample_profile)
    
    def test_partial_valid_years_succeeds(self, analyzer, sample_profile):
        """
        If some years are valid, should succeed with valid data.
        """
        financials = [
            {"date": "2024-12-31", "revenue": 100000000000, "net_income": 10000000000, "total_equity": 50000000000},
            {"date": "invalid", "revenue": 200},  # Invalid year
            {"date": "2023-12-31", "revenue": 90000000000, "net_income": 9000000000, "total_equity": 45000000000},
        ]
        
        result = analyzer.analyze(financials, sample_profile)
        
        # Should have 2 valid years
        assert len(result.yearly_metrics) == 2
        assert result.avg_pe_5yr is not None  # Can calculate with 2 years

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


class TestTrueHistoricalValuation:
    """
    Tests for true historical valuation using actual historical prices.
    
    Bug: Previous implementation used current market cap to calculate 
    "historical" multiples, which is misleading. True historical valuation
    requires the stock price FROM that year.
    
    Example showing the difference:
    - 2021 Net Income: $70B
    - Current Market Cap: $2.4T → "Historical" P/E = 34x (WRONG)
    - 2021 Stock Price: $100 → Shares: 16B → Market Cap: $1.6T → True P/E = 23x (CORRECT)
    """
    
    @pytest.fixture
    def sample_historical_prices(self):
        """
        Historical prices at year-end for each fiscal year.
        Format: {year: price_at_year_end}
        """
        return {
            2024: 150.0,  # Most recent - should match current
            2023: 130.0,  # Stock was lower last year
            2022: 110.0,  # Even lower 2 years ago
            2021: 100.0,  # Lower still
            2020: 85.0,   # Lowest
        }
    
    def test_true_historical_uses_actual_prices(self, analyzer, sample_financials, sample_profile, sample_historical_prices):
        """
        When historical prices are provided, use them for true historical multiples.
        """
        result = analyzer.analyze(
            sample_financials, 
            sample_profile,
            historical_prices=sample_historical_prices,
        )
        
        # Should indicate that true historical prices were used
        assert result.uses_true_historical_prices is True
        
        # For 2021: price=$100, shares=16B → market cap = $1.6T
        # Net income 2021 = $70B
        # True P/E = 1.6T / 70B = 22.86
        year_2021 = next((ym for ym in result.yearly_metrics if ym.year == 2021), None)
        assert year_2021 is not None
        
        # With current market cap proxy, P/E would be 2.4T/70B = 34.3
        # With true historical price, P/E should be ~22.9
        assert year_2021.pe is not None
        assert 20 < year_2021.pe < 25, (
            f"2021 P/E should be ~22.9 with historical price, got {year_2021.pe}. "
            "Ensure historical price is used, not current market cap."
        )
    
    def test_proxy_mode_without_historical_prices(self, analyzer, sample_financials, sample_profile):
        """
        Without historical prices, fall back to proxy mode (current market cap).
        """
        result = analyzer.analyze(sample_financials, sample_profile)
        
        # Should indicate proxy mode
        assert result.uses_true_historical_prices is False
        
        # With proxy mode, all years use current market cap ($2.4T)
        # 2021 Net income = $70B → P/E = 2.4T/70B = 34.3
        year_2021 = next((ym for ym in result.yearly_metrics if ym.year == 2021), None)
        assert year_2021 is not None
        assert year_2021.pe is not None
        assert 30 < year_2021.pe < 40, (
            f"2021 P/E in proxy mode should be ~34.3, got {year_2021.pe}"
        )
    
    def test_historical_ps_uses_historical_prices(self, analyzer, sample_financials, sample_profile, sample_historical_prices):
        """
        P/S should also use historical market cap when historical prices available.
        """
        result = analyzer.analyze(
            sample_financials, 
            sample_profile,
            historical_prices=sample_historical_prices,
        )
        
        # For 2021: price=$100, shares=16B → market cap = $1.6T
        # Revenue 2021 = $300B
        # True P/S = 1.6T / 300B = 5.33
        year_2021 = next((ym for ym in result.yearly_metrics if ym.year == 2021), None)
        assert year_2021 is not None
        
        # With current market cap: 2.4T/300B = 8
        # With historical price: 1.6T/300B = 5.33
        assert year_2021.ps is not None
        assert 4.5 < year_2021.ps < 6.5, (
            f"2021 P/S should be ~5.33 with historical price, got {year_2021.ps}"
        )
    
    def test_averages_reflect_true_historical(self, analyzer, sample_financials, sample_profile, sample_historical_prices):
        """
        5-year averages should be calculated from true historical multiples.
        """
        result = analyzer.analyze(
            sample_financials, 
            sample_profile,
            historical_prices=sample_historical_prices,
        )
        
        # Average P/E with true historical should be lower than with proxy
        # because stock price was lower in past years
        assert result.avg_pe_5yr is not None
        
        # Calculate proxy average for comparison
        proxy_result = analyzer.analyze(sample_financials, sample_profile)
        
        # True historical average should be lower (stock was cheaper in past)
        assert result.avg_pe_5yr < proxy_result.avg_pe_5yr, (
            f"True historical avg P/E ({result.avg_pe_5yr:.1f}) should be lower "
            f"than proxy avg ({proxy_result.avg_pe_5yr:.1f}) since stock was cheaper in past"
        )
    
    def test_missing_year_falls_back_to_proxy(self, analyzer, sample_financials, sample_profile):
        """
        If historical price missing for a year, use proxy for that year only.
        """
        partial_prices = {
            2024: 150.0,
            2023: 130.0,
            # 2022, 2021, 2020 missing
        }
        
        result = analyzer.analyze(
            sample_financials, 
            sample_profile,
            historical_prices=partial_prices,
        )
        
        # 2024 and 2023 should use historical prices
        # Other years should fall back to current market cap
        year_2023 = next((ym for ym in result.yearly_metrics if ym.year == 2023), None)
        year_2021 = next((ym for ym in result.yearly_metrics if ym.year == 2021), None)
        
        assert year_2023 is not None
        assert year_2021 is not None
        
        # Both should have P/E calculated (mixed mode should work)
        assert year_2023.pe is not None
        assert year_2021.pe is not None

