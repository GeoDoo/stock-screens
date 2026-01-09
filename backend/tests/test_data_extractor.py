import pytest
from app.services.data_extractor import DataExtractor


class TestDataExtractor:
    def test_extract_beta(self):
        """Extract beta from profile data."""
        data = {
            "profile": {"beta": 1.25},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.beta() == 1.25

    def test_extract_market_cap(self):
        """Extract market cap from profile data."""
        data = {
            "profile": {"marketCap": 3000000000000},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.market_cap() == 3000000000000

    def test_extract_total_debt(self):
        """Extract total debt from balance sheet."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{"totalDebt": 100000000000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.total_debt() == 100000000000

    def test_extract_cash(self):
        """Extract cash from balance sheet."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{"cashAndCashEquivalents": 50000000000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.cash() == 50000000000

    def test_extract_tax_rate(self):
        """Calculate effective tax rate from income statement."""
        data = {
            "profile": {},
            "income_statement": [
                {"incomeTaxExpense": 25000000, "incomeBeforeTax": 100000000}
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        # 25M / 100M = 0.25 (25%)
        assert abs(extractor.tax_rate() - 0.25) < 0.001

    def test_extract_cost_of_debt(self):
        """Calculate cost of debt from interest expense and total debt.
        
        Cost of debt has a floor of risk-free rate + credit spread (6.5%).
        """
        data = {
            "profile": {},
            "income_statement": [{"interestExpense": 8000000}],  # 8M interest
            "balance_sheet": [{"totalDebt": 100000000}],  # 100M debt
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        # 8M / 100M = 0.08 (8%) - above floor, so actual rate used
        assert abs(extractor.cost_of_debt() - 0.08) < 0.001
    
    def test_cost_of_debt_applies_floor(self):
        """Cost of debt should not go below floor (risk-free + spread = 6.5%)."""
        data = {
            "profile": {},
            "income_statement": [{"interestExpense": 3000000}],  # Very low interest
            "balance_sheet": [{"totalDebt": 100000000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        # 3M / 100M = 0.03 (3%) - below floor, so floor (6.5%) used
        # Floor = DEFAULT_TREASURY_RATE (4.5%) + DEFAULT_CREDIT_SPREAD (2%) = 6.5%
        assert abs(extractor.cost_of_debt() - 0.065) < 0.001

    def test_extract_fcf(self):
        """Extract free cash flow from cash flow statement."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [{"freeCashFlow": 99000000000}],
        }
        extractor = DataExtractor(data)
        assert extractor.free_cash_flow() == 99000000000

    def test_extract_shares_outstanding(self):
        """Extract shares outstanding from income statement."""
        data = {
            "profile": {},
            "income_statement": [{"weightedAverageShsOut": 15500000000}],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.shares_outstanding() == 15500000000

    def test_handles_missing_data_gracefully(self):
        """Return None for missing data instead of crashing."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.beta() is None
        assert extractor.total_debt() is None

    def test_handles_zero_debt_for_cost_of_debt(self):
        """Cost of debt should be 0 if no debt."""
        data = {
            "profile": {},
            "income_statement": [{"interestExpense": 0}],
            "balance_sheet": [{"totalDebt": 0}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.cost_of_debt() == 0.0

    def test_handles_missing_interest_expense_with_debt(self):
        """Cost of debt applies floor when interest expense is missing but debt exists.
        
        This happens for companies like Apple where interest income exceeds expense,
        or when data is missing. Using 0% would understate WACC and inflate valuations.
        """
        data = {
            "profile": {},
            "income_statement": [{}],  # No interestExpense field
            "balance_sheet": [{"totalDebt": 100000000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        # Company has debt but no interest expense - apply conservative floor
        # Floor = DEFAULT_TREASURY_RATE (4.5%) + DEFAULT_CREDIT_SPREAD (2%) = 6.5%
        assert abs(extractor.cost_of_debt() - 0.065) < 0.001

    def test_market_risk_premium_default(self):
        """Market risk premium defaults to 6%."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.market_risk_premium() == 0.06

    def test_market_risk_premium_override(self):
        """User can override market risk premium."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data, market_risk_premium=0.07)
        assert extractor.market_risk_premium() == 0.07

    def test_extract_total_equity(self):
        """Extract total stockholders equity from balance sheet."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{"totalStockholdersEquity": 73733000000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.total_equity() == 73733000000

    def test_extract_total_equity_missing(self):
        """Returns None when total equity is missing."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.total_equity() is None

    def test_extract_latest_revenue(self):
        """Extract latest revenue from income statement."""
        data = {
            "profile": {},
            "income_statement": [{"revenue": 416161000000}],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.latest_revenue() == 416161000000

    def test_extract_latest_working_capital(self):
        """Calculate working capital from current assets and liabilities."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{
                "totalCurrentAssets": 143566000000,
                "totalCurrentLiabilities": 105392000000,
            }],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        # 143.5B - 105.4B = 38.2B
        assert extractor.latest_working_capital() == 38174000000

    def test_extract_latest_working_capital_negative(self):
        """Working capital can be negative (current liabilities > assets)."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{
                "totalCurrentAssets": 100000000000,
                "totalCurrentLiabilities": 120000000000,
            }],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        # 100B - 120B = -20B (negative working capital)
        assert extractor.latest_working_capital() == -20000000000

    def test_extract_latest_working_capital_missing_data(self):
        """Returns None when current assets or liabilities missing."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{"totalCurrentAssets": 100000000000}],  # Missing liabilities
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.latest_working_capital() is None


class TestNonCashWorkingCapital:
    """
    Regression tests for Non-Cash Working Capital calculation.
    
    Bug: DataExtractor used standard accounting Working Capital:
        WC = Current Assets - Current Liabilities
    
    Professional DCF requires Non-Cash Working Capital:
        NCWC = (Current Assets - Cash) - (Current Liabilities - Short-term Debt)
    
    Why: Cash is already added back at end of DCF (EV → Equity Value).
         Short-term debt is financing, not operating.
         Including them double-counts and distorts FCF projections.
    """
    
    def test_non_cash_working_capital_excludes_cash(self):
        """
        NCWC should exclude cash from current assets.
        
        Cash is added back separately when converting EV to Equity Value.
        Including it in WC double-counts it.
        """
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{
                "totalCurrentAssets": 150000000000,  # 150B
                "totalCurrentLiabilities": 100000000000,  # 100B
                "cashAndCashEquivalents": 50000000000,  # 50B cash
                "shortTermDebt": 0,  # No short-term debt
            }],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # OLD (wrong): 150B - 100B = 50B
        # NEW (correct): (150B - 50B) - (100B - 0) = 100B - 100B = 0B
        
        ncwc = extractor.latest_working_capital()
        assert ncwc == 0, (
            f"NCWC should be 0 (cash excluded), got {ncwc}. "
            "Cash must be excluded from working capital in DCF."
        )
    
    def test_non_cash_working_capital_excludes_short_term_debt(self):
        """
        NCWC should exclude short-term debt from current liabilities.
        
        Short-term debt is a financing activity, not operating.
        It's already in total debt which affects EV calculation.
        """
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{
                "totalCurrentAssets": 100000000000,  # 100B
                "totalCurrentLiabilities": 80000000000,  # 80B
                "cashAndCashEquivalents": 0,  # No cash
                "shortTermDebt": 30000000000,  # 30B short-term debt
            }],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # OLD (wrong): 100B - 80B = 20B
        # NEW (correct): (100B - 0) - (80B - 30B) = 100B - 50B = 50B
        
        ncwc = extractor.latest_working_capital()
        assert ncwc == 50000000000, (
            f"NCWC should be 50B (short-term debt excluded), got {ncwc}. "
            "Short-term debt must be excluded from working capital in DCF."
        )
    
    def test_non_cash_working_capital_full_calculation(self):
        """
        Full NCWC calculation with both cash and short-term debt.
        
        Formula: (Current Assets - Cash) - (Current Liabilities - Short-term Debt)
        """
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{
                "totalCurrentAssets": 200000000000,  # 200B
                "totalCurrentLiabilities": 150000000000,  # 150B
                "cashAndCashEquivalents": 60000000000,  # 60B cash
                "shortTermDebt": 40000000000,  # 40B short-term debt
            }],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # OLD (wrong): 200B - 150B = 50B
        # NEW (correct): (200B - 60B) - (150B - 40B) = 140B - 110B = 30B
        
        ncwc = extractor.latest_working_capital()
        assert ncwc == 30000000000, (
            f"NCWC should be 30B, got {ncwc}. "
            "NCWC = (Current Assets - Cash) - (Current Liabilities - Short-term Debt)"
        )
    
    def test_non_cash_working_capital_handles_missing_cash(self):
        """
        When cash data is missing, treat as 0 (conservative).
        """
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{
                "totalCurrentAssets": 100000000000,
                "totalCurrentLiabilities": 80000000000,
                # No cashAndCashEquivalents field
                "shortTermDebt": 10000000000,
            }],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # (100B - 0) - (80B - 10B) = 100B - 70B = 30B
        ncwc = extractor.latest_working_capital()
        assert ncwc == 30000000000
    
    def test_non_cash_working_capital_handles_missing_short_term_debt(self):
        """
        When short-term debt data is missing, treat as 0 (conservative).
        """
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{
                "totalCurrentAssets": 100000000000,
                "totalCurrentLiabilities": 80000000000,
                "cashAndCashEquivalents": 20000000000,
                # No shortTermDebt field
            }],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # (100B - 20B) - (80B - 0) = 80B - 80B = 0B
        ncwc = extractor.latest_working_capital()
        assert ncwc == 0
    
    def test_working_capital_history_uses_non_cash(self):
        """
        Historical working capital should also use NCWC formula.
        """
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [
                {  # Year 2 (most recent)
                    "totalCurrentAssets": 200000000000,
                    "totalCurrentLiabilities": 150000000000,
                    "cashAndCashEquivalents": 50000000000,
                    "shortTermDebt": 20000000000,
                },
                {  # Year 1 (older)
                    "totalCurrentAssets": 180000000000,
                    "totalCurrentLiabilities": 140000000000,
                    "cashAndCashEquivalents": 40000000000,
                    "shortTermDebt": 15000000000,
                },
            ],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # History is oldest first
        # Year 1: (180B - 40B) - (140B - 15B) = 140B - 125B = 15B
        # Year 2: (200B - 50B) - (150B - 20B) = 150B - 130B = 20B
        
        history = extractor.working_capital_history()
        assert len(history) == 2
        assert history[0] == 15000000000, "Year 1 NCWC should be 15B"
        assert history[1] == 20000000000, "Year 2 NCWC should be 20B"


class TestDilutedShares:
    """
    Regression tests for Fully Diluted Shares Outstanding (FDSO).
    
    Bug: DataExtractor used Basic Shares Outstanding from income statement.
    
    Professional DCF requires Fully Diluted Shares Outstanding because:
    - Stock options, RSUs, convertible securities will dilute shareholders
    - Using basic shares OVERVALUES the company by ignoring dilution
    - This affects intrinsic value per share calculation
    """
    
    def test_diluted_shares_extracted(self):
        """
        Diluted shares should be extracted from income statement.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "weightedAverageShsOut": 15000000000,  # 15B basic
                "weightedAverageShsOutDil": 15500000000,  # 15.5B diluted
            }],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        diluted = extractor.diluted_shares_outstanding()
        assert diluted == 15500000000, (
            f"Diluted shares should be 15.5B, got {diluted}. "
            "Must extract weightedAverageShsOutDil from income statement."
        )
    
    def test_shares_outstanding_prefers_diluted(self):
        """
        shares_outstanding() should prefer diluted over basic.
        
        Professional valuation ALWAYS uses diluted shares to account
        for future dilution from options, RSUs, and convertibles.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "weightedAverageShsOut": 15000000000,  # 15B basic
                "weightedAverageShsOutDil": 15500000000,  # 15.5B diluted
            }],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        shares = extractor.shares_outstanding()
        assert shares == 15500000000, (
            f"shares_outstanding() should return diluted (15.5B), got {shares}. "
            "Diluted shares must be preferred over basic for DCF."
        )
    
    def test_shares_outstanding_falls_back_to_basic(self):
        """
        When diluted shares not available, fall back to basic.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "weightedAverageShsOut": 15000000000,  # Only basic available
            }],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        shares = extractor.shares_outstanding()
        assert shares == 15000000000, (
            "Should fall back to basic shares when diluted not available."
        )
    
    def test_diluted_shares_handles_missing_data(self):
        """
        Returns None when diluted shares not available.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "weightedAverageShsOut": 15000000000,  # Only basic
            }],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        diluted = extractor.diluted_shares_outstanding()
        assert diluted is None, "Should return None when diluted shares missing."
    
    def test_shares_outstanding_uses_profile_as_last_resort(self):
        """
        When neither diluted nor basic in income statement, use profile.
        """
        data = {
            "profile": {"sharesOutstanding": 14000000000},
            "income_statement": [{}],  # No share data
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        shares = extractor.shares_outstanding()
        assert shares == 14000000000, (
            "Should fall back to profile shares when income statement missing both."
        )
    
    def test_diluted_shares_impact_on_valuation(self):
        """
        Demonstrate the valuation impact of using diluted vs basic.
        
        With 3.3% more diluted shares, per-share value decreases by ~3.2%.
        This is the error we're fixing.
        """
        equity_value = 3_000_000_000_000  # $3T equity value
        basic_shares = 15_000_000_000
        diluted_shares = 15_500_000_000  # 3.3% more shares
        
        per_share_basic = equity_value / basic_shares  # $200
        per_share_diluted = equity_value / diluted_shares  # $193.55
        
        overvaluation_pct = (per_share_basic - per_share_diluted) / per_share_diluted * 100
        
        assert overvaluation_pct > 3.0, (
            f"Using basic shares overvalues by {overvaluation_pct:.1f}%. "
            "This demonstrates why diluted shares are required."
        )
    
    def test_shares_outstanding_type_returns_diluted(self):
        """
        shares_outstanding_type() should return 'diluted' when diluted shares available.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "weightedAverageShsOut": 15000000000,
                "weightedAverageShsOutDil": 15500000000,
            }],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        shares_type = extractor.shares_outstanding_type()
        assert shares_type == "diluted", (
            f"Expected 'diluted' when diluted shares available, got '{shares_type}'"
        )
    
    def test_shares_outstanding_type_returns_basic(self):
        """
        shares_outstanding_type() should return 'basic' when only basic shares available.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "weightedAverageShsOut": 15000000000,
                # No diluted shares
            }],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        shares_type = extractor.shares_outstanding_type()
        assert shares_type == "basic", (
            f"Expected 'basic' when only basic shares available, got '{shares_type}'"
        )
    
    def test_shares_outstanding_type_returns_profile(self):
        """
        shares_outstanding_type() should return 'profile' when using profile fallback.
        
        This is the bug we're fixing: previously this was mislabeled as 'basic'.
        """
        data = {
            "profile": {"sharesOutstanding": 14000000000},
            "income_statement": [{}],  # No share data in income statement
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        shares_type = extractor.shares_outstanding_type()
        assert shares_type == "profile", (
            f"Expected 'profile' when using profile fallback, got '{shares_type}'. "
            "Must correctly label data source for transparency."
        )


class TestTaxRateAveraging:
    """
    Regression tests for tax rate averaging.
    
    Bug: DataExtractor.tax_rate() used only the latest year's effective tax rate.
    
    Problem: Effective tax rates are notoriously volatile due to one-time items
    (e.g., R&D credits, foreign tax adjustments, deferred tax benefits).
    Using a single year can badly distort FCF projections over 10 years.
    
    Solution: Use 3-year average tax rate for stability, with fallback to
    latest year if less history is available.
    """
    
    def test_tax_rate_uses_3_year_average(self):
        """
        tax_rate() should average multiple years to smooth out volatility.
        """
        data = {
            "profile": {},
            "income_statement": [
                # Most recent year
                {"incomeTaxExpense": 22000000, "incomeBeforeTax": 100000000},  # 22%
                # Prior year
                {"incomeTaxExpense": 20000000, "incomeBeforeTax": 100000000},  # 20%
                # Two years ago
                {"incomeTaxExpense": 24000000, "incomeBeforeTax": 100000000},  # 24%
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Single year would give 22%
        # 3-year average: (22% + 20% + 24%) / 3 = 22%
        tax_rate = extractor.tax_rate()
        
        assert tax_rate is not None
        assert abs(tax_rate - 0.22) < 0.01, (
            f"Expected 3-year average ~22%, got {tax_rate:.2%}. "
            "Tax rate should use multi-year average."
        )
    
    def test_tax_rate_excludes_negative_rates(self):
        """
        Negative tax rates (tax benefits) should be excluded as outliers.
        """
        data = {
            "profile": {},
            "income_statement": [
                # Most recent: Tax benefit (negative) due to one-time R&D credit
                {"incomeTaxExpense": -5000000, "incomeBeforeTax": 100000000},  # -5%
                # Prior year: Normal
                {"incomeTaxExpense": 20000000, "incomeBeforeTax": 100000000},  # 20%
                # Two years ago: Normal
                {"incomeTaxExpense": 25000000, "incomeBeforeTax": 100000000},  # 25%
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Negative rate should be excluded
        # Average of valid years: (20% + 25%) / 2 = 22.5%
        tax_rate = extractor.tax_rate()
        
        assert tax_rate is not None
        assert abs(tax_rate - 0.225) < 0.01, (
            f"Expected ~22.5% (excluding negative rate), got {tax_rate:.2%}. "
            "Negative tax rates should be excluded from average."
        )
    
    def test_tax_rate_excludes_extreme_outliers(self):
        """
        Should exclude years with extreme/negative tax rates from average.
        """
        data = {
            "profile": {},
            "income_statement": [
                # Extreme outlier: 80% due to one-time charge
                {"incomeTaxExpense": 80000000, "incomeBeforeTax": 100000000},  # 80%
                {"incomeTaxExpense": 22000000, "incomeBeforeTax": 100000000},  # 22%
                {"incomeTaxExpense": 23000000, "incomeBeforeTax": 100000000},  # 23%
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Including outlier: (80% + 22% + 23%) / 3 = 41.67% (unrealistic)
        # Excluding outlier: (22% + 23%) / 2 = 22.5% (realistic)
        tax_rate = extractor.tax_rate()
        
        # Should be in reasonable range, not ~41%
        assert tax_rate is not None
        assert 0.15 < tax_rate < 0.35, (
            f"Tax rate {tax_rate:.2%} seems unrealistic. "
            "Should exclude extreme outliers from average."
        )
    
    def test_tax_rate_falls_back_to_latest_if_only_one_year(self):
        """
        With only one year of data, use that year.
        """
        data = {
            "profile": {},
            "income_statement": [
                {"incomeTaxExpense": 25000000, "incomeBeforeTax": 100000000},
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        tax_rate = extractor.tax_rate()
        assert tax_rate == pytest.approx(0.25, rel=0.01)
    
    def test_tax_rate_handles_loss_years(self):
        """
        Years with negative income before tax should be excluded from average.
        """
        data = {
            "profile": {},
            "income_statement": [
                {"incomeTaxExpense": 25000000, "incomeBeforeTax": 100000000},  # 25%
                {"incomeTaxExpense": -10000000, "incomeBeforeTax": -50000000},  # Loss year
                {"incomeTaxExpense": 20000000, "incomeBeforeTax": 100000000},  # 20%
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Should only average profitable years: (25% + 20%) / 2 = 22.5%
        tax_rate = extractor.tax_rate()
        assert tax_rate == pytest.approx(0.225, rel=0.01), (
            "Should exclude loss years from tax rate average"
        )

