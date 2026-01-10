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


class TestSyntheticCreditRating:
    """
    Tests for synthetic credit rating based on Interest Coverage Ratio.
    
    Problem: Current cost of debt uses a fixed fallback spread (DEFAULT_CREDIT_SPREAD).
    This treats Apple (AAA credit) the same as a distressed company (CCC credit).
    
    Solution: Calculate synthetic credit rating from Interest Coverage Ratio (ICR),
    then map to appropriate credit spread. This is standard practice in professional DCF.
    
    ICR = EBIT / Interest Expense
    
    Higher ICR → Better credit → Lower spread
    Lower ICR → Worse credit → Higher spread
    """
    
    def test_interest_coverage_ratio_calculated(self):
        """
        DataExtractor should calculate Interest Coverage Ratio.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,  # $100B EBIT
                "interestExpense": 5_000_000_000,    # $5B interest
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        icr = extractor.interest_coverage_ratio()
        # ICR = 100B / 5B = 20x
        assert icr == pytest.approx(20.0, rel=0.01)
    
    def test_synthetic_rating_from_high_icr(self):
        """
        High ICR (>10x) should map to AAA/AA credit rating.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,
                "interestExpense": 5_000_000_000,  # ICR = 20x
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        rating = extractor.synthetic_credit_rating()
        assert rating in ["AAA", "AA"], f"ICR of 20x should be AAA/AA, got {rating}"
    
    def test_synthetic_rating_from_medium_icr(self):
        """
        Medium ICR (3-6x) should map to investment grade (BBB range).
        """
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,
                "interestExpense": 25_000_000_000,  # ICR = 4x
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        rating = extractor.synthetic_credit_rating()
        # ICR of 4x should be in BBB range (investment grade)
        assert rating.startswith("BBB") or rating.startswith("A"), (
            f"ICR of 4x should be investment grade (BBB+/BBB/BBB-/A-), got {rating}"
        )
    
    def test_synthetic_rating_from_low_icr(self):
        """
        Low ICR (<1x) should map to high yield / distressed.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 4_000_000_000,
                "interestExpense": 10_000_000_000,  # ICR = 0.4x (can't cover interest!)
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        rating = extractor.synthetic_credit_rating()
        # ICR < 0.5x should be CCC or worse
        assert rating in ["CCC", "CC", "C", "D"], f"ICR of 0.4x should be CCC or worse, got {rating}"
    
    def test_cost_of_debt_uses_synthetic_spread(self):
        """
        Cost of debt should use credit spread from synthetic rating.
        
        AAA spread (~0.5%) vs CCC spread (~10%+) makes a huge difference in WACC.
        """
        # High credit quality company (like Apple)
        high_quality = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,
                "interestExpense": 5_000_000_000,  # ICR = 20x → AAA
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        
        # Low credit quality company
        low_quality = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 10_000_000_000,
                "interestExpense": 10_000_000_000,  # ICR = 1x → CCC
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        
        high_extractor = DataExtractor(high_quality)
        low_extractor = DataExtractor(low_quality)
        
        high_cod = high_extractor.cost_of_debt()
        low_cod = low_extractor.cost_of_debt()
        
        # Low quality should have SIGNIFICANTLY higher cost of debt
        assert low_cod > high_cod + 0.03, (
            f"CCC cost of debt ({low_cod:.2%}) should be at least 3% higher "
            f"than AAA ({high_cod:.2%})"
        )
    
    def test_cost_of_debt_spread_reasonable_for_investment_grade(self):
        """
        Investment grade (A-) cost of debt should be reasonable (~5-7%).
        
        Note: cost_of_debt uses max(synthetic_rate, historical_rate) to be
        conservative. So we need interest/debt to be low enough.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 50_000_000_000,
                "interestExpense": 5_000_000_000,  # ICR = 10x → AA, interest/debt = 5%
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        cod = extractor.cost_of_debt()
        # Risk-free (~4%) + AA spread (~0.8%) = ~4.8% (but historical is 5%)
        # Should use max(synthetic, historical) = ~5%
        assert 0.04 < cod < 0.08, (
            f"Investment grade cost of debt should be 4-8%, got {cod:.2%}"
        )
    
    def test_negative_icr_returns_distressed_rating(self):
        """
        Negative EBIT (losing money) should return distressed rating.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": -10_000_000_000,  # Negative EBIT
                "interestExpense": 5_000_000_000,
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        rating = extractor.synthetic_credit_rating()
        assert rating in ["CCC", "CC", "C", "D"], f"Negative EBIT should be distressed, got {rating}"
    
    def test_missing_interest_expense_uses_fallback(self):
        """
        When interest expense missing, should use conservative fallback.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,
                # No interestExpense!
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # ICR can't be calculated, should return None
        icr = extractor.interest_coverage_ratio()
        assert icr is None
        
        # But cost of debt should still work (using fallback)
        cod = extractor.cost_of_debt()
        assert cod is not None
        assert cod > 0


class TestLTMDataMerging:
    """
    Tests for Last Twelve Months (LTM) data merging.
    
    From Gemini review: Professional valuation uses LTM data, not just
    the last annual report (which can be 9+ months stale).
    
    Flow items (revenue, income, cash flow): Sum last 4 quarters OR use TTM record
    Balance sheet items: Use most recent (already point-in-time)
    """
    
    def test_prefers_ttm_revenue_over_annual(self):
        """
        When TTM data is available, should prefer it over annual.
        """
        data = {
            "profile": {},
            "income_statement": [
                {"period": "TTM", "revenue": 400_000_000_000},  # TTM record
                {"period": "FY", "revenue": 380_000_000_000},  # Last annual
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Should use TTM revenue (400B), not annual (380B)
        assert extractor.latest_revenue() == 400_000_000_000
    
    def test_falls_back_to_annual_when_no_ttm(self):
        """
        When no TTM record, should use annual data as before.
        """
        data = {
            "profile": {},
            "income_statement": [
                {"period": "FY", "revenue": 380_000_000_000},
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        assert extractor.latest_revenue() == 380_000_000_000
    
    def test_prefers_ttm_for_flow_items(self):
        """
        TTM should be preferred for all flow items (income, cash flow).
        """
        data = {
            "profile": {},
            "income_statement": [
                {"period": "TTM", "revenue": 400_000, "operatingIncome": 80_000, "netIncome": 60_000},
                {"period": "FY", "revenue": 350_000, "operatingIncome": 70_000, "netIncome": 50_000},
            ],
            "balance_sheet": [],
            "cash_flow": [
                {"period": "TTM", "freeCashFlow": 55_000},
                {"period": "FY", "freeCashFlow": 45_000},
            ],
        }
        extractor = DataExtractor(data)
        
        assert extractor.latest_revenue() == 400_000
        assert extractor.free_cash_flow() == 55_000
    
    def test_balance_sheet_uses_latest_always(self):
        """
        Balance sheet is point-in-time, so use most recent regardless of period.
        """
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [
                {"totalAssets": 500_000_000_000, "totalDebt": 100_000_000_000},
            ],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        assert extractor.total_debt() == 100_000_000_000
    
    def test_data_freshness_indicator(self):
        """
        Should expose whether LTM/TTM data was used.
        """
        data_with_ttm = {
            "profile": {},
            "income_statement": [
                {"period": "TTM", "revenue": 400_000_000_000},
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        
        data_annual_only = {
            "profile": {},
            "income_statement": [
                {"period": "FY", "revenue": 380_000_000_000},
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        
        extractor_ttm = DataExtractor(data_with_ttm)
        extractor_annual = DataExtractor(data_annual_only)
        
        assert extractor_ttm.is_using_ltm() is True
        assert extractor_annual.is_using_ltm() is False
    
    def test_ttm_tax_rate_calculation(self):
        """
        Tax rate should also use TTM data when available.
        """
        data = {
            "profile": {},
            "income_statement": [
                {"period": "TTM", "incomeTaxExpense": 25_000, "incomeBeforeTax": 100_000},  # 25%
                {"period": "FY", "incomeTaxExpense": 20_000, "incomeBeforeTax": 100_000},  # 20%
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Should use TTM tax rate (25%), not annual (20%)
        tax_rate = extractor.tax_rate()
        assert 0.24 <= tax_rate <= 0.26, f"Expected ~25%, got {tax_rate:.2%}"


class TestRiskFreeRateConsistency:
    """
    Tests for P0 bug: cost_of_debt uses hardcoded DEFAULT_TREASURY_RATE 
    while cost_of_equity uses fetched risk_free_rate.
    
    This creates inconsistent capital market assumptions in WACC:
    - CoE: Rf_fetched + beta * MRP  (using e.g. 4.2% fetched rate)
    - CoD: Rf_hardcoded + spread   (using 4.5% hardcoded)
    
    Fix: cost_of_debt() should accept optional risk_free_rate parameter.
    """
    
    def test_cost_of_debt_uses_passed_risk_free_rate(self):
        """
        When risk_free_rate is provided, cost_of_debt should use it
        instead of DEFAULT_TREASURY_RATE.
        """
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,
                "interestExpense": 5_000_000_000,  # ICR = 20x → AAA (~0.63% spread)
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Use a distinctly different risk-free rate (3.8%)
        custom_rf = 0.038
        cod = extractor.cost_of_debt(risk_free_rate=custom_rf)
        
        # AAA spread is ~0.63%, so synthetic = 3.8% + 0.63% = 4.43%
        # Historical = 5B / 100B = 5%
        # max(4.43%, 5%) = 5%
        expected = max(custom_rf + 0.0063, 0.05)  # AAA spread + max with historical
        
        assert cod is not None
        assert abs(cod - expected) < 0.005, (
            f"With Rf={custom_rf:.2%}, expected ~{expected:.2%}, got {cod:.2%}"
        )
    
    def test_cost_of_debt_defaults_to_constant_when_not_passed(self):
        """
        When risk_free_rate is NOT provided, cost_of_debt should fall back
        to DEFAULT_TREASURY_RATE for backward compatibility.
        """
        from app.constants import DEFAULT_TREASURY_RATE
        
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,
                "interestExpense": 5_000_000_000,  # ICR = 20x → AAA
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Call without parameter
        cod_default = extractor.cost_of_debt()
        
        # Call with explicit default
        cod_explicit = extractor.cost_of_debt(risk_free_rate=DEFAULT_TREASURY_RATE)
        
        # Should produce identical results
        assert cod_default == cod_explicit, (
            f"Default ({cod_default:.4f}) should equal explicit DEFAULT_TREASURY_RATE ({cod_explicit:.4f})"
        )
    
    def test_cost_of_debt_reflects_rate_changes(self):
        """
        Different risk_free_rates should produce different cost_of_debt
        (when synthetic rate dominates).
        """
        # Low historical rate so synthetic dominates
        data = {
            "profile": {},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,
                "interestExpense": 2_000_000_000,  # ICR = 50x → AAA, historical = 2%
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        cod_low_rf = extractor.cost_of_debt(risk_free_rate=0.03)   # 3%
        cod_high_rf = extractor.cost_of_debt(risk_free_rate=0.05)  # 5%
        
        # Higher risk-free rate should produce higher cost of debt
        assert cod_high_rf > cod_low_rf, (
            f"CoD with 5% Rf ({cod_high_rf:.2%}) should be > CoD with 3% Rf ({cod_low_rf:.2%})"
        )
        
        # The difference should be approximately 2% (the Rf difference)
        diff = cod_high_rf - cod_low_rf
        assert 0.015 < diff < 0.025, f"Difference should be ~2%, got {diff:.2%}"
    
    def test_wacc_uses_consistent_risk_free_rate(self):
        """
        Integration test: WACC calculation should use the same risk-free
        rate for both cost of equity and cost of debt.
        """
        from app.services.wacc_calculator import WACCCalculator
        
        data = {
            "profile": {"marketCap": 2_000_000_000_000, "beta": 1.1},
            "income_statement": [{
                "operatingIncome": 100_000_000_000,
                "interestExpense": 5_000_000_000,  # ICR = 20x → AAA
            }],
            "balance_sheet": [{"totalDebt": 100_000_000_000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        # Use consistent risk-free rate
        risk_free_rate = 0.042  # 4.2%
        
        # Get cost of debt with the SAME risk-free rate
        cost_of_debt = extractor.cost_of_debt(risk_free_rate=risk_free_rate)
        
        # Now calculate WACC
        wacc_calc = WACCCalculator(
            risk_free_rate=risk_free_rate,  # Same rate!
            beta=extractor.beta(),
            market_risk_premium=0.06,
            cost_of_debt=cost_of_debt,
            tax_rate=0.21,
            market_cap=extractor.market_cap(),
            total_debt=extractor.total_debt(),
        )
        
        wacc = wacc_calc.calculate()
        
        # WACC should be reasonable (7-12% for most companies)
        assert 0.07 < wacc < 0.12, f"WACC should be 7-12%, got {wacc:.2%}"
        
        # Verify cost of equity uses our risk-free rate
        expected_coe = risk_free_rate + 1.1 * 0.06  # Rf + beta * MRP
        assert abs(wacc_calc.cost_of_equity() - expected_coe) < 0.001


class TestTTMFYMixingGuard:
    """
    Tests for ensuring history series don't mix TTM and annual data.
    
    The issue: If a provider returns [TTM, FY2024, FY2023, ...], CAGR 
    calculations become invalid because TTM overlaps with FY2024.
    History series should only include annual data for valid CAGR/ratios.
    """
    
    def test_revenue_history_excludes_ttm(self):
        """Revenue history should not include TTM records."""
        data = {
            "profile": {},
            "income_statement": [
                {"period": "TTM", "revenue": 400_000_000_000},    # TTM - should be excluded
                {"period": "FY", "revenue": 380_000_000_000},     # FY2024
                {"period": "FY", "revenue": 350_000_000_000},     # FY2023
                {"period": "FY", "revenue": 320_000_000_000},     # FY2022
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        history = extractor.revenue_history()
        
        # Should have 3 values (FY only), not 4
        assert len(history) == 3, f"Expected 3 annual values, got {len(history)}"
        # Oldest first: 320B, 350B, 380B
        assert history == [320_000_000_000, 350_000_000_000, 380_000_000_000]
    
    def test_ebit_history_excludes_ltm(self):
        """EBIT history should not include LTM records."""
        data = {
            "profile": {},
            "income_statement": [
                {"period": "LTM", "operatingIncome": 50_000_000_000},  # LTM - exclude
                {"period": "annual", "operatingIncome": 48_000_000_000},
                {"period": "annual", "operatingIncome": 45_000_000_000},
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        history = extractor.ebit_history()
        
        assert len(history) == 2, f"Expected 2 annual values, got {len(history)}"
        assert history == [45_000_000_000, 48_000_000_000]
    
    def test_da_history_excludes_ttm(self):
        """D&A history should exclude TTM from cash flow statements."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [
                {"period": "ttm", "depreciationAndAmortization": 12_000_000_000},  # ttm - exclude
                {"period": "FY", "depreciationAndAmortization": 11_500_000_000},
                {"period": "FY", "depreciationAndAmortization": 11_000_000_000},
            ],
        }
        extractor = DataExtractor(data)
        
        history = extractor.da_history()
        
        assert len(history) == 2
        assert history == [11_000_000_000, 11_500_000_000]
    
    def test_capex_history_excludes_ttm(self):
        """CapEx history should exclude TTM."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [
                {"period": "TTM", "capitalExpenditure": -11_000_000_000},  # TTM - exclude
                {"period": "FY", "capitalExpenditure": -10_500_000_000},
                {"period": "FY", "capitalExpenditure": -10_000_000_000},
            ],
        }
        extractor = DataExtractor(data)
        
        history = extractor.capex_history()
        
        assert len(history) == 2
        # CapEx is abs() converted
        assert history == [10_000_000_000, 10_500_000_000]
    
    def test_working_capital_history_excludes_ttm(self):
        """Working capital history should exclude TTM from balance sheets."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [
                {
                    "period": "TTM",
                    "totalCurrentAssets": 150_000_000_000,
                    "cashAndCashEquivalents": 50_000_000_000,
                    "totalCurrentLiabilities": 100_000_000_000,
                    "shortTermDebt": 10_000_000_000,
                },
                {
                    "period": "FY",
                    "totalCurrentAssets": 145_000_000_000,
                    "cashAndCashEquivalents": 48_000_000_000,
                    "totalCurrentLiabilities": 95_000_000_000,
                    "shortTermDebt": 9_000_000_000,
                },
                {
                    "period": "FY",
                    "totalCurrentAssets": 140_000_000_000,
                    "cashAndCashEquivalents": 45_000_000_000,
                    "totalCurrentLiabilities": 90_000_000_000,
                    "shortTermDebt": 8_000_000_000,
                },
            ],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        history = extractor.working_capital_history()
        
        # Should have 2 values (FY only)
        assert len(history) == 2, f"Expected 2 annual WC values, got {len(history)}"
    
    def test_history_without_period_field_treats_as_annual(self):
        """Records without 'period' field should be treated as annual."""
        data = {
            "profile": {},
            "income_statement": [
                {"revenue": 400_000_000_000},  # No period - treat as annual
                {"revenue": 380_000_000_000},
                {"revenue": 350_000_000_000},
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        history = extractor.revenue_history()
        
        # All should be included
        assert len(history) == 3
        assert history == [350_000_000_000, 380_000_000_000, 400_000_000_000]
    
    def test_cagr_not_distorted_by_ttm_exclusion(self):
        """CAGR calculation should use only annual data."""
        from app.services.fcf_projector import FCFProjector
        
        # With TTM included, CAGR would be different (TTM overlaps FY2024)
        data = {
            "profile": {},
            "income_statement": [
                {"period": "TTM", "revenue": 420_000_000_000},    # Should be excluded
                {"period": "FY", "revenue": 400_000_000_000},     # FY2024
                {"period": "FY", "revenue": 350_000_000_000},     # FY2023
                {"period": "FY", "revenue": 300_000_000_000},     # FY2022
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        history = extractor.revenue_history()
        
        # Create projector with the (filtered) history
        projector = FCFProjector(
            historical_revenue=history,
            historical_ebit=[30, 35, 40],  # dummy
            historical_da=[5, 5, 5],
            historical_capex=[10, 10, 10],
            historical_working_capital=[20, 22, 24],
        )
        
        cagr = projector.revenue_cagr()
        
        # 3 years of data: 300B → 400B
        # CAGR = (400/300)^(1/2) - 1 = 15.47%
        expected_cagr = (400 / 300) ** (1/2) - 1
        assert abs(cagr - expected_cagr) < 0.001, (
            f"CAGR should be ~{expected_cagr:.2%} using annual data only, got {cagr:.2%}"
        )
    
    def test_quarterly_data_also_excluded(self):
        """Quarterly data (Q1, Q2, etc.) should also be excluded from history."""
        data = {
            "profile": {},
            "income_statement": [
                {"period": "Q4", "revenue": 110_000_000_000},   # Quarterly - exclude
                {"period": "Q3", "revenue": 100_000_000_000},   # Quarterly - exclude
                {"period": "FY", "revenue": 400_000_000_000},   # Annual - include
                {"period": "FY", "revenue": 380_000_000_000},   # Annual - include
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        
        history = extractor.revenue_history()
        
        # Should only have 2 annual values
        assert len(history) == 2
        assert history == [380_000_000_000, 400_000_000_000]
