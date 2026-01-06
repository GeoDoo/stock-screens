"""
Tests for DividendAnalyzer service.
"""
import pytest
from datetime import datetime, timedelta
from app.services.dividend_analyzer import DividendAnalyzer, DividendHistory, DividendPayment


@pytest.fixture
def sample_dividends():
    """Sample dividend payments for testing."""
    # 5 years of quarterly dividends with growth
    payments = []
    base_date = datetime(2025, 1, 1)
    
    # Year 1: $0.20/quarter = $0.80/year
    for q in range(4):
        payments.append(DividendPayment(
            date=(base_date - timedelta(days=365*5 - q*91)).strftime("%Y-%m-%d"),
            amount=0.20
        ))
    
    # Year 2: $0.22/quarter = $0.88/year (10% increase)
    for q in range(4):
        payments.append(DividendPayment(
            date=(base_date - timedelta(days=365*4 - q*91)).strftime("%Y-%m-%d"),
            amount=0.22
        ))
    
    # Year 3: $0.24/quarter = $0.96/year (9% increase)
    for q in range(4):
        payments.append(DividendPayment(
            date=(base_date - timedelta(days=365*3 - q*91)).strftime("%Y-%m-%d"),
            amount=0.24
        ))
    
    # Year 4: $0.26/quarter = $1.04/year (8% increase)
    for q in range(4):
        payments.append(DividendPayment(
            date=(base_date - timedelta(days=365*2 - q*91)).strftime("%Y-%m-%d"),
            amount=0.26
        ))
    
    # Year 5 (current): $0.28/quarter = $1.12/year (8% increase)
    for q in range(4):
        payments.append(DividendPayment(
            date=(base_date - timedelta(days=365*1 - q*91)).strftime("%Y-%m-%d"),
            amount=0.28
        ))
    
    return payments


@pytest.fixture
def analyzer():
    return DividendAnalyzer()


class TestDividendAnalysis:
    """Tests for dividend analysis."""

    def test_analyze_with_dividends(self, analyzer, sample_dividends):
        """Analyze dividend history with payments."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        assert result.has_dividends is True
        assert result.current_annual_dividend is not None
        assert result.current_yield is not None
        assert len(result.annual_dividends) > 0

    def test_analyze_no_dividends(self, analyzer):
        """Handle company with no dividends."""
        result = analyzer.analyze(
            payments=[],
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        assert result.has_dividends is False
        assert result.current_annual_dividend is None
        assert result.current_yield is None
        assert result.dividend_cagr is None
        assert result.consecutive_years == 0

    def test_current_annual_dividend(self, analyzer, sample_dividends):
        """Calculate current annual dividend from recent payments."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        # Most recent year has $0.28 * 4 = $1.12
        assert result.current_annual_dividend == pytest.approx(1.12, rel=0.1)

    def test_current_yield(self, analyzer, sample_dividends):
        """Calculate current dividend yield."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        # Yield = $1.12 / $100 = 1.12%
        assert result.current_yield == pytest.approx(0.0112, rel=0.1)

    def test_dividend_cagr(self, analyzer, sample_dividends):
        """Calculate dividend compound annual growth rate."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        # From $0.80 to $1.12 over 4 years
        # CAGR = (1.12/0.80)^(1/4) - 1 ≈ 8.8%
        assert result.dividend_cagr is not None
        assert result.dividend_cagr > 0.05  # At least 5% growth
        assert result.dividend_cagr < 0.15  # Less than 15%

    def test_consecutive_years(self, analyzer, sample_dividends):
        """Count years of consecutive dividend payments."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        # 5 years of consecutive payments
        assert result.consecutive_years >= 4

    def test_annual_dividends_summary(self, analyzer, sample_dividends):
        """Get annual dividend totals."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        # Should have annual totals for each year
        assert len(result.annual_dividends) >= 4
        # Most recent year should be highest
        years = sorted(result.annual_dividends.keys(), reverse=True)
        if len(years) >= 2:
            assert result.annual_dividends[years[0]] >= result.annual_dividends[years[1]]

    def test_yield_history(self, analyzer, sample_dividends):
        """Calculate historical yield at each year's price."""
        # Need historical prices to calculate yield history
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        # Should have annual dividends even without price history
        assert len(result.annual_dividends) > 0


class TestPayoutRatio:
    """Tests for payout ratio calculation."""

    def test_payout_ratio_calculation(self, analyzer, sample_dividends):
        """Calculate payout ratio = Total Dividends / Net Income."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,  # 1B shares
            net_income=10000000000,  # $10B net income
        )
        
        # Annual dividend ~$1.12/share * 1B shares = $1.12B total dividends
        # Payout ratio = $1.12B / $10B = 11.2%
        assert result.payout_ratio is not None
        assert result.payout_ratio == pytest.approx(0.112, rel=0.1)

    def test_payout_ratio_no_net_income(self, analyzer, sample_dividends):
        """Handle missing net income."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
            net_income=None,
        )
        
        assert result.payout_ratio is None

    def test_payout_ratio_negative_net_income(self, analyzer, sample_dividends):
        """Handle negative net income (loss)."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=100.0,
            shares_outstanding=1000000000,
            net_income=-5000000000,  # Loss
        )
        
        # Can't calculate meaningful payout ratio with negative income
        assert result.payout_ratio is None

    def test_payout_ratio_no_dividends(self, analyzer):
        """Payout ratio is None when no dividends."""
        result = analyzer.analyze(
            payments=[],
            current_price=100.0,
            shares_outstanding=1000000000,
            net_income=10000000000,
        )
        
        assert result.payout_ratio is None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_single_dividend_payment(self, analyzer):
        """Handle company with only one dividend payment."""
        payments = [DividendPayment(date="2024-06-15", amount=0.50)]
        
        result = analyzer.analyze(
            payments=payments,
            current_price=50.0,
            shares_outstanding=1000000000,
        )
        
        assert result.has_dividends is True
        assert result.dividend_cagr is None  # Can't calculate CAGR with one year

    def test_irregular_dividends(self, analyzer):
        """Handle irregular dividend payments."""
        payments = [
            DividendPayment(date="2024-03-15", amount=0.50),
            DividendPayment(date="2024-12-15", amount=0.75),  # Special dividend
            DividendPayment(date="2023-06-15", amount=0.50),
        ]
        
        result = analyzer.analyze(
            payments=payments,
            current_price=100.0,
            shares_outstanding=1000000000,
        )
        
        assert result.has_dividends is True
        assert result.current_annual_dividend is not None

    def test_missing_price(self, analyzer, sample_dividends):
        """Handle missing price data."""
        result = analyzer.analyze(
            payments=sample_dividends,
            current_price=None,
            shares_outstanding=1000000000,
        )
        
        assert result.has_dividends is True
        assert result.current_yield is None  # Can't calculate without price

    def test_dividend_cut(self, analyzer):
        """Handle dividend reduction."""
        payments = [
            # Year 1: $1.00
            DividendPayment(date="2021-06-15", amount=0.25),
            DividendPayment(date="2021-09-15", amount=0.25),
            DividendPayment(date="2021-12-15", amount=0.25),
            DividendPayment(date="2022-03-15", amount=0.25),
            # Year 2: $0.80 (cut!)
            DividendPayment(date="2022-06-15", amount=0.20),
            DividendPayment(date="2022-09-15", amount=0.20),
            DividendPayment(date="2022-12-15", amount=0.20),
            DividendPayment(date="2023-03-15", amount=0.20),
        ]
        
        result = analyzer.analyze(
            payments=payments,
            current_price=50.0,
            shares_outstanding=1000000000,
        )
        
        # Should show negative CAGR
        assert result.dividend_cagr is not None
        assert result.dividend_cagr < 0  # Negative growth

