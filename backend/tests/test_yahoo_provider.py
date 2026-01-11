"""
Tests for YahooProvider TTM data freshness validation.

P0 Issue: The Yahoo provider sums last 4 quarters to create TTM data,
but never checks how old those quarters are. This could return data
from a bankrupt/delisted company as "fresh TTM".

Fix: Reject TTM data if the most recent quarter is older than 6 months.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pandas as pd

from app.services.yahoo_provider import YahooProvider


class TestTTMFreshnessValidation:
    """
    Tests for P0: TTM data freshness check.
    
    Problem: User types ticker for a delisted/bankrupt company.
    Yahoo still has historical quarterly data from 2+ years ago.
    System sums those quarters and returns as "TTM" - implying current data.
    User makes investment decision on years-old stale data.
    
    Fix: Check the date of the most recent quarterly data.
    If older than 6 months (2 quarters missed), reject as stale.
    """
    
    @pytest.fixture
    def yahoo_provider(self):
        return YahooProvider()
    
    def _create_mock_quarterly_data(self, most_recent_date: datetime, num_quarters: int = 4):
        """Create mock quarterly financials with specified most recent date."""
        # Generate quarter dates going back from most_recent_date
        dates = [most_recent_date - timedelta(days=90 * i) for i in range(num_quarters)]
        
        # Create DataFrame with quarterly data
        income_data = {
            pd.Timestamp(d): [100_000_000, 40_000_000, 60_000_000, 15_000_000, 10_000_000, 1_000_000, 3_000_000]
            for d in dates
        }
        income_df = pd.DataFrame(
            income_data,
            index=["Total Revenue", "Cost Of Revenue", "Gross Profit", 
                   "Operating Income", "Net Income", "Interest Expense", "Tax Provision"]
        )
        
        balance_data = {
            pd.Timestamp(dates[0]): [500_000_000, 200_000_000, 300_000_000, 100_000_000, 
                                     50_000_000, 150_000_000, 80_000_000]
        }
        balance_df = pd.DataFrame(
            balance_data,
            index=["Total Assets", "Total Liabilities Net Minority Interest", 
                   "Total Equity Gross Minority Interest", "Total Debt",
                   "Cash And Cash Equivalents", "Current Assets", "Current Liabilities"]
        )
        
        cash_data = {
            pd.Timestamp(d): [20_000_000, -5_000_000, 15_000_000, 8_000_000, -2_000_000]
            for d in dates
        }
        cash_df = pd.DataFrame(
            cash_data,
            index=["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow",
                   "Depreciation And Amortization", "Cash Dividends Paid"]
        )
        
        return income_df, balance_df, cash_df
    
    def test_rejects_ttm_data_older_than_6_months(self, yahoo_provider):
        """
        TTM data from quarters older than 6 months should be rejected.
        
        This prevents using years-old data from delisted/bankrupt companies.
        """
        # Create mock quarterly data from 8 months ago
        stale_date = datetime.now() - timedelta(days=240)  # 8 months ago
        income_df, balance_df, cash_df = self._create_mock_quarterly_data(stale_date)
        
        mock_ticker = MagicMock()
        mock_ticker.quarterly_financials = income_df
        mock_ticker.quarterly_balance_sheet = balance_df
        mock_ticker.quarterly_cashflow = cash_df
        
        # Should return None for stale data
        result = yahoo_provider._get_ttm_financials(mock_ticker)
        
        assert result is None, (
            "TTM data older than 6 months should be rejected as stale. "
            "This prevents using data from delisted/bankrupt companies."
        )
    
    def test_accepts_fresh_ttm_data(self, yahoo_provider):
        """
        TTM data from recent quarters (< 4 months old) should be accepted.
        """
        # Create mock quarterly data from 2 months ago (fresh)
        fresh_date = datetime.now() - timedelta(days=60)  # 2 months ago
        income_df, balance_df, cash_df = self._create_mock_quarterly_data(fresh_date)
        
        mock_ticker = MagicMock()
        mock_ticker.quarterly_financials = income_df
        mock_ticker.quarterly_balance_sheet = balance_df
        mock_ticker.quarterly_cashflow = cash_df
        
        result = yahoo_provider._get_ttm_financials(mock_ticker)
        
        assert result is not None, "Fresh TTM data should be accepted"
        assert result.period == "ttm"
        assert result.revenue is not None
    
    def test_accepts_ttm_data_at_4_month_boundary(self, yahoo_provider):
        """
        TTM data at exactly 4 months should be accepted (normal reporting lag).
        """
        # Create mock quarterly data from exactly 4 months ago
        boundary_date = datetime.now() - timedelta(days=120)  # 4 months ago
        income_df, balance_df, cash_df = self._create_mock_quarterly_data(boundary_date)
        
        mock_ticker = MagicMock()
        mock_ticker.quarterly_financials = income_df
        mock_ticker.quarterly_balance_sheet = balance_df
        mock_ticker.quarterly_cashflow = cash_df
        
        result = yahoo_provider._get_ttm_financials(mock_ticker)
        
        assert result is not None, "TTM data at 4-month boundary should be accepted"
    
    def test_rejects_ttm_at_7_month_boundary(self, yahoo_provider):
        """
        TTM data at 7 months should be rejected (past 6-month threshold).
        """
        # Create mock quarterly data from 7 months ago
        stale_date = datetime.now() - timedelta(days=210)  # 7 months ago
        income_df, balance_df, cash_df = self._create_mock_quarterly_data(stale_date)
        
        mock_ticker = MagicMock()
        mock_ticker.quarterly_financials = income_df
        mock_ticker.quarterly_balance_sheet = balance_df
        mock_ticker.quarterly_cashflow = cash_df
        
        result = yahoo_provider._get_ttm_financials(mock_ticker)
        
        assert result is None, "TTM data at 7 months should be rejected"
    
    def test_ttm_date_reflects_actual_quarter_not_hardcoded(self, yahoo_provider):
        """
        The TTM FinancialStatement.date should reflect the actual most recent
        quarter date, not be hardcoded to "TTM".
        
        This allows consumers to know exactly when the data is from.
        """
        # Create fresh quarterly data
        recent_date = datetime.now() - timedelta(days=30)
        income_df, balance_df, cash_df = self._create_mock_quarterly_data(recent_date)
        
        mock_ticker = MagicMock()
        mock_ticker.quarterly_financials = income_df
        mock_ticker.quarterly_balance_sheet = balance_df
        mock_ticker.quarterly_cashflow = cash_df
        
        result = yahoo_provider._get_ttm_financials(mock_ticker)
        
        assert result is not None
        # Date should NOT be just "TTM" - it should have actual date info
        # Accept either the date string or a format that includes date info
        assert result.date != "TTM" or "20" in result.date, (
            f"TTM date should reflect actual quarter date, got: {result.date}"
        )
