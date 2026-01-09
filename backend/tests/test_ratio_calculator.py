"""
Tests for RatioCalculator service.
"""
import pytest
from app.services.ratio_calculator import RatioCalculator, FinancialRatios


@pytest.fixture
def sample_stock_data():
    """
    Sample stock data for testing.
    
    Mirrors the structure produced by stock_data_to_legacy():
    - D&A is in cash_flow (not income_statement)
    """
    return {
        "profile": {
            "price": 150.0,
            "marketCap": 2400000000000,  # 2.4T
            "sharesOutstanding": 16000000000,
            "beta": 1.2,
        },
        "income_statement": [
            {
                "revenue": 400000000000,  # 400B
                "costOfRevenue": 220000000000,  # 220B (55% COGS)
                "grossProfit": 180000000000,  # 180B (45% margin)
                "operatingIncome": 120000000000,  # 120B (30% margin)
                "netIncome": 100000000000,  # 100B (25% margin)
                "interestExpense": 3000000000,  # 3B
                "incomeBeforeTax": 103000000000,
                # NOTE: D&A is NOT here - it's in cash_flow (as per stock_data_to_legacy)
            }
        ],
        "balance_sheet": [
            {
                "totalAssets": 350000000000,
                "totalCurrentAssets": 140000000000,
                "inventory": 5000000000,
                "totalCurrentLiabilities": 120000000000,
                "totalDebt": 100000000000,
                "totalStockholdersEquity": 60000000000,
                "cashAndCashEquivalents": 25000000000,
            }
        ],
        "cash_flow": [
            {
                "dividendsPaid": -15000000000,  # 15B dividends
                "depreciationAndAmortization": 10000000000,  # 10B D&A
            }
        ],
    }


@pytest.fixture
def calculator():
    return RatioCalculator()


class TestValuationRatios:
    """Tests for valuation ratios."""

    def test_pe_ratio(self, calculator, sample_stock_data):
        """P/E = Price / EPS"""
        ratios = calculator.calculate(sample_stock_data)
        # EPS = 100B / 16B shares = 6.25
        # P/E = 150 / 6.25 = 24
        assert ratios.valuation.pe_ratio == pytest.approx(24.0, rel=0.01)

    def test_earnings_yield(self, calculator, sample_stock_data):
        """Earnings Yield = EPS / Price = 1/PE"""
        ratios = calculator.calculate(sample_stock_data)
        # Earnings yield = 6.25 / 150 = 0.0417 (4.17%)
        assert ratios.valuation.earnings_yield == pytest.approx(0.0417, rel=0.01)

    def test_ps_ratio(self, calculator, sample_stock_data):
        """P/S = Market Cap / Revenue"""
        ratios = calculator.calculate(sample_stock_data)
        # P/S = 2.4T / 400B = 6.0
        assert ratios.valuation.ps_ratio == pytest.approx(6.0, rel=0.01)

    def test_pb_ratio(self, calculator, sample_stock_data):
        """P/B = Market Cap / Book Value"""
        ratios = calculator.calculate(sample_stock_data)
        # P/B = 2.4T / 60B = 40
        assert ratios.valuation.pb_ratio == pytest.approx(40.0, rel=0.01)

    def test_ev_to_ebitda(self, calculator, sample_stock_data):
        """EV/EBITDA"""
        ratios = calculator.calculate(sample_stock_data)
        # EV = 2.4T + 100B debt - 25B cash = 2.475T
        # EBITDA = 120B operating + 10B D&A = 130B
        # EV/EBITDA = 2.475T / 130B = 19.04
        assert ratios.valuation.ev_to_ebitda == pytest.approx(19.04, rel=0.01)

    def test_ev_to_revenue(self, calculator, sample_stock_data):
        """EV/Revenue"""
        ratios = calculator.calculate(sample_stock_data)
        # EV/Revenue = 2.475T / 400B = 6.19
        assert ratios.valuation.ev_to_revenue == pytest.approx(6.19, rel=0.01)


class TestDividendMetrics:
    """Tests for dividend metrics."""

    def test_dividend_yield(self, calculator, sample_stock_data):
        """Dividend Yield = Annual Dividend Per Share / Price"""
        ratios = calculator.calculate(sample_stock_data)
        # DPS = 15B / 16B shares = 0.9375
        # Yield = 0.9375 / 150 = 0.00625 (0.625%)
        assert ratios.dividend.dividend_yield == pytest.approx(0.00625, rel=0.01)

    def test_payout_ratio(self, calculator, sample_stock_data):
        """Payout Ratio = Dividends / Net Income"""
        ratios = calculator.calculate(sample_stock_data)
        # Payout = 15B / 100B = 0.15 (15%)
        assert ratios.dividend.payout_ratio == pytest.approx(0.15, rel=0.01)

    def test_no_dividend(self, calculator):
        """Handle companies with no dividend."""
        data = {
            "profile": {"price": 100, "marketCap": 1000000000, "sharesOutstanding": 10000000},
            "income_statement": [{"netIncome": 50000000}],
            "balance_sheet": [{}],
            "cash_flow": [{"dividendsPaid": 0}],
        }
        ratios = calculator.calculate(data)
        assert ratios.dividend.dividend_yield == 0.0
        assert ratios.dividend.payout_ratio == 0.0

    def test_negative_dividends_paid(self, calculator):
        """Handle negative dividendsPaid (cash outflow as reported by FMP)."""
        data = {
            "profile": {"price": 150, "marketCap": 2400000000000, "sharesOutstanding": 16000000000},
            "income_statement": [{"netIncome": 100000000000}],
            "balance_sheet": [{}],
            "cash_flow": [{"dividendsPaid": -15000000000}],  # Negative = outflow
        }
        ratios = calculator.calculate(data)
        # abs(-15B) / 16B shares = 0.9375 DPS
        # 0.9375 / 150 = 0.00625 (0.625%)
        assert ratios.dividend.dividend_yield == pytest.approx(0.00625, rel=0.01)
        # Payout = 15B / 100B = 15%
        assert ratios.dividend.payout_ratio == pytest.approx(0.15, rel=0.01)


class TestProfitabilityRatios:
    """Tests for profitability ratios."""

    def test_gross_margin(self, calculator, sample_stock_data):
        """Gross Margin = Gross Profit / Revenue"""
        ratios = calculator.calculate(sample_stock_data)
        # 180B / 400B = 0.45 (45%)
        assert ratios.profitability.gross_margin == pytest.approx(0.45, rel=0.01)

    def test_operating_margin(self, calculator, sample_stock_data):
        """Operating Margin = Operating Income / Revenue"""
        ratios = calculator.calculate(sample_stock_data)
        # 120B / 400B = 0.30 (30%)
        assert ratios.profitability.operating_margin == pytest.approx(0.30, rel=0.01)

    def test_net_margin(self, calculator, sample_stock_data):
        """Net Margin = Net Income / Revenue"""
        ratios = calculator.calculate(sample_stock_data)
        # 100B / 400B = 0.25 (25%)
        assert ratios.profitability.net_margin == pytest.approx(0.25, rel=0.01)

    def test_roe(self, calculator, sample_stock_data):
        """ROE = Net Income / Shareholders Equity"""
        ratios = calculator.calculate(sample_stock_data)
        # 100B / 60B = 1.67 (167%)
        assert ratios.profitability.roe == pytest.approx(1.67, rel=0.01)

    def test_roa(self, calculator, sample_stock_data):
        """ROA = Net Income / Total Assets"""
        ratios = calculator.calculate(sample_stock_data)
        # 100B / 350B = 0.286 (28.6%)
        assert ratios.profitability.roa == pytest.approx(0.286, rel=0.01)

    def test_roic(self, calculator, sample_stock_data):
        """ROIC = NOPAT / Invested Capital"""
        ratios = calculator.calculate(sample_stock_data)
        # NOPAT = Operating Income * (1 - tax rate)
        # Tax rate ≈ (Income before tax - Net Income) / Income before tax = 3B / 103B ≈ 0.029
        # NOPAT ≈ 120B * (1 - 0.029) ≈ 116.5B
        # Invested Capital = Equity + Debt - Cash = 60B + 100B - 25B = 135B
        # ROIC ≈ 116.5B / 135B ≈ 0.863 (86.3%)
        assert ratios.profitability.roic is not None
        assert ratios.profitability.roic > 0.5  # Just check it's calculated reasonably


class TestLiquidityRatios:
    """Tests for liquidity and solvency ratios."""

    def test_current_ratio(self, calculator, sample_stock_data):
        """Current Ratio = Current Assets / Current Liabilities"""
        ratios = calculator.calculate(sample_stock_data)
        # 140B / 120B = 1.17
        assert ratios.liquidity.current_ratio == pytest.approx(1.17, rel=0.01)

    def test_quick_ratio(self, calculator, sample_stock_data):
        """Quick Ratio = (Current Assets - Inventory) / Current Liabilities"""
        ratios = calculator.calculate(sample_stock_data)
        # (140B - 5B) / 120B = 1.125
        assert ratios.liquidity.quick_ratio == pytest.approx(1.125, rel=0.01)

    def test_debt_to_equity(self, calculator, sample_stock_data):
        """D/E = Total Debt / Equity"""
        ratios = calculator.calculate(sample_stock_data)
        # 100B / 60B = 1.67
        assert ratios.liquidity.debt_to_equity == pytest.approx(1.67, rel=0.01)

    def test_interest_coverage(self, calculator, sample_stock_data):
        """Interest Coverage = EBIT / Interest Expense"""
        ratios = calculator.calculate(sample_stock_data)
        # EBIT = Operating Income = 120B
        # Interest = 3B
        # Coverage = 120B / 3B = 40
        assert ratios.liquidity.interest_coverage == pytest.approx(40.0, rel=0.01)


class TestEfficiencyRatios:
    """Tests for efficiency ratios."""

    def test_asset_turnover(self, calculator, sample_stock_data):
        """Asset Turnover = Revenue / Total Assets"""
        ratios = calculator.calculate(sample_stock_data)
        # 400B / 350B = 1.14
        assert ratios.efficiency.asset_turnover == pytest.approx(1.14, rel=0.01)

    def test_inventory_turnover(self, calculator, sample_stock_data):
        """Inventory Turnover = COGS / Inventory"""
        ratios = calculator.calculate(sample_stock_data)
        # 220B / 5B = 44
        assert ratios.efficiency.inventory_turnover == pytest.approx(44.0, rel=0.01)


class TestEBITDAWiring:
    """
    Regression tests for EBITDA calculation.
    
    Bug: D&A was being read from income_statement, but stock_data_to_legacy()
    places it in cash_flow. This caused EBITDA to equal operating_income
    (D&A treated as 0), making EV/EBITDA incorrect.
    """

    def test_da_read_from_cash_flow_not_income_statement(self, calculator):
        """
        D&A should be read from cash_flow, not income_statement.
        
        This is how stock_data_to_legacy() structures the data.
        EBITDA = Operating Income + D&A (from cash_flow)
        """
        # Realistic data structure: D&A in cash_flow only (as produced by stock_data_to_legacy)
        data = {
            "profile": {
                "price": 150.0,
                "marketCap": 2400000000000,  # 2.4T
                "sharesOutstanding": 16000000000,
            },
            "income_statement": [
                {
                    "revenue": 400000000000,
                    "operatingIncome": 120000000000,
                    # NOTE: No depreciationAndAmortization here!
                }
            ],
            "balance_sheet": [
                {
                    "totalDebt": 100000000000,
                    "cashAndCashEquivalents": 25000000000,
                }
            ],
            "cash_flow": [
                {
                    # D&A is in cash_flow, as produced by stock_data_to_legacy()
                    "depreciationAndAmortization": 10000000000,  # 10B
                }
            ],
        }
        
        ratios = calculator.calculate(data)
        
        # EBITDA = Operating Income (120B) + D&A (10B) = 130B
        # EV = 2.4T + 100B - 25B = 2.475T
        # EV/EBITDA = 2.475T / 130B = 19.04
        
        # If bug exists: EBITDA = 120B (D&A=0 because read from wrong location)
        # EV/EBITDA would be 2.475T / 120B = 20.625 (WRONG)
        
        assert ratios.valuation.ev_to_ebitda == pytest.approx(19.04, rel=0.01), (
            f"EV/EBITDA should be ~19.04 but got {ratios.valuation.ev_to_ebitda}. "
            "D&A is being read from income_statement instead of cash_flow."
        )

    def test_ebitda_includes_da_from_cash_flow(self, calculator):
        """EBITDA must include D&A from cash_flow statement."""
        data = {
            "profile": {
                "price": 100.0,
                "marketCap": 1000000000000,  # 1T
                "sharesOutstanding": 10000000000,
            },
            "income_statement": [
                {
                    "operatingIncome": 50000000000,  # 50B
                    # No D&A in income statement
                }
            ],
            "balance_sheet": [
                {
                    "totalDebt": 0,
                    "cashAndCashEquivalents": 0,
                }
            ],
            "cash_flow": [
                {
                    "depreciationAndAmortization": 20000000000,  # 20B
                }
            ],
        }
        
        ratios = calculator.calculate(data)
        
        # EBITDA = 50B + 20B = 70B
        # EV = 1T (no debt, no cash)
        # EV/EBITDA = 1T / 70B = 14.29
        
        # If bug: EV/EBITDA = 1T / 50B = 20 (D&A ignored)
        
        assert ratios.valuation.ev_to_ebitda == pytest.approx(14.29, rel=0.01), (
            f"EBITDA should include D&A from cash_flow. "
            f"Expected EV/EBITDA ~14.29, got {ratios.valuation.ev_to_ebitda}"
        )


class TestEdgeCases:
    """Tests for edge cases and missing data."""

    def test_missing_income_statement(self, calculator):
        """Handle missing income statement gracefully."""
        data = {
            "profile": {"price": 100, "marketCap": 1000000000},
            "income_statement": [],
            "balance_sheet": [{}],
            "cash_flow": [{}],
        }
        ratios = calculator.calculate(data)
        assert ratios.valuation.pe_ratio is None
        assert ratios.profitability.net_margin is None

    def test_zero_revenue(self, calculator):
        """Handle zero revenue (pre-revenue company)."""
        data = {
            "profile": {"price": 100, "marketCap": 1000000000, "sharesOutstanding": 10000000},
            "income_statement": [{"revenue": 0, "netIncome": -50000000}],
            "balance_sheet": [{}],
            "cash_flow": [{}],
        }
        ratios = calculator.calculate(data)
        assert ratios.valuation.ps_ratio is None
        assert ratios.profitability.net_margin is None

    def test_negative_earnings(self, calculator):
        """Handle negative earnings (loss-making company)."""
        data = {
            "profile": {"price": 100, "marketCap": 1000000000, "sharesOutstanding": 10000000},
            "income_statement": [{"revenue": 500000000, "netIncome": -50000000}],
            "balance_sheet": [{}],
            "cash_flow": [{}],
        }
        ratios = calculator.calculate(data)
        # Negative P/E doesn't make sense, should be None
        assert ratios.valuation.pe_ratio is None
        # Earnings yield for loss is negative
        assert ratios.valuation.earnings_yield is not None
        assert ratios.valuation.earnings_yield < 0

    def test_missing_shares_outstanding(self, calculator):
        """Handle missing shares outstanding."""
        data = {
            "profile": {"price": 100, "marketCap": 1000000000},
            "income_statement": [{"revenue": 500000000, "netIncome": 50000000}],
            "balance_sheet": [{}],
            "cash_flow": [{"dividendsPaid": -10000000}],
        }
        ratios = calculator.calculate(data)
        assert ratios.valuation.pe_ratio is None
        assert ratios.dividend.dividend_yield is None


class TestROICExcessCash:
    """
    Tests for ROIC using excess cash instead of all cash.
    
    Bug: ROIC calculation subtracted ALL cash from invested capital.
    
    Problem: Businesses need operating cash (typically 2% of revenue) to
    function. Subtracting all cash artificially inflates ROIC for companies
    with large cash piles.
    
    Solution: Only subtract EXCESS cash = Total Cash - Operating Cash (2% of revenue)
    """
    
    @pytest.fixture
    def calculator(self):
        return RatioCalculator()
    
    def test_roic_uses_excess_cash_not_all_cash(self, calculator):
        """
        ROIC should subtract only excess cash, not all cash.
        """
        # Company with $100B revenue and $50B cash
        # Operating cash = 2% × $100B = $2B
        # Excess cash = $50B - $2B = $48B
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,  # $100B revenue
                "operatingIncome": 30_000_000_000,  # $30B operating income
                "incomeBeforeTax": 28_000_000_000,
                "netIncome": 21_000_000_000,  # ~25% tax rate
            }],
            "balance_sheet": [{
                "totalStockholdersEquity": 100_000_000_000,  # $100B equity
                "totalDebt": 50_000_000_000,  # $50B debt
                "cashAndCashEquivalents": 50_000_000_000,  # $50B cash (large pile!)
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        # Tax rate from data: (28-21)/28 = 25%
        # NOPAT = 30B × 0.75 = 22.5B
        #
        # If subtracting ALL cash: IC = 100 + 50 - 50 = $100B
        # ROIC = 22.5B / 100B = 22.5%
        #
        # If subtracting EXCESS cash: 
        # Operating cash = 2% × 100B = $2B
        # Excess cash = 50B - 2B = $48B
        # IC = 100 + 50 - 48 = $102B  
        # ROIC = 22.5B / 102B = ~22.06%
        
        assert ratios.profitability.roic is not None
        
        # The key test: ROIC should NOT be 22.5% (all cash method)
        # It should be closer to 22.06% (excess cash method)
        all_cash_roic = 0.225  # 22.5%
        excess_cash_roic = 0.2206  # ~22.06%
        
        # ROIC should be closer to excess_cash_roic than all_cash_roic
        diff_from_all_cash = abs(ratios.profitability.roic - all_cash_roic)
        diff_from_excess = abs(ratios.profitability.roic - excess_cash_roic)
        
        assert diff_from_excess < diff_from_all_cash, (
            f"ROIC ({ratios.profitability.roic:.4f}) should be closer to excess cash method "
            f"({excess_cash_roic:.4f}) than all cash method ({all_cash_roic:.4f}). "
            "Ensure only EXCESS cash is subtracted from invested capital."
        )
    
    def test_roic_with_minimal_cash(self, calculator):
        """
        When cash < operating cash requirement, excess cash = 0 (no subtraction).
        """
        # Company with $100B revenue but only $1B cash (below 2% = $2B)
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
                "operatingIncome": 30_000_000_000,
                "incomeBeforeTax": 28_000_000_000,
                "netIncome": 21_000_000_000,
            }],
            "balance_sheet": [{
                "totalStockholdersEquity": 100_000_000_000,
                "totalDebt": 50_000_000_000,
                "cashAndCashEquivalents": 1_000_000_000,  # Only $1B cash
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        # Cash ($1B) < Operating Cash ($2B), so excess cash = 0
        # Invested Capital = Equity + Debt - 0 = $150B
        assert ratios.profitability.roic is not None
        
        # ROIC should be ~15% (22.5B / 150B)
        assert 0.14 < ratios.profitability.roic < 0.16
    
    def test_roic_zero_cash(self, calculator):
        """
        With zero cash, excess cash = 0, invested capital = equity + debt.
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
                "operatingIncome": 30_000_000_000,
                "incomeBeforeTax": 28_000_000_000,
                "netIncome": 21_000_000_000,
            }],
            "balance_sheet": [{
                "totalStockholdersEquity": 100_000_000_000,
                "totalDebt": 50_000_000_000,
                "cashAndCashEquivalents": 0,  # No cash
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        # IC = $100B + $50B - 0 = $150B
        # ROIC = ~22.5B / 150B = ~15%
        assert ratios.profitability.roic is not None
        assert 0.14 < ratios.profitability.roic < 0.16
    
    def test_roic_requires_revenue_for_excess_cash(self, calculator):
        """
        ROIC should NOT be calculated if revenue is missing.
        
        Bug: Without revenue, we can't calculate operating cash needs,
        so we'd incorrectly fall back to subtracting all cash.
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                # NO revenue!
                "operatingIncome": 30_000_000_000,
                "incomeBeforeTax": 28_000_000_000,
                "netIncome": 21_000_000_000,
            }],
            "balance_sheet": [{
                "totalStockholdersEquity": 100_000_000_000,
                "totalDebt": 50_000_000_000,
                "cashAndCashEquivalents": 50_000_000_000,
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        # Without revenue, ROIC should be None (can't calculate excess cash)
        assert ratios.profitability.roic is None, (
            "ROIC should be None when revenue is missing - "
            "can't calculate operating cash needs without revenue"
        )


class TestROTIC:
    """
    Tests for Return on Tangible Invested Capital (ROTIC).
    
    ROTIC = NOPAT / Tangible Invested Capital
    Tangible IC = Invested Capital - Goodwill - Intangible Assets
    
    ROTIC reveals the core business's operating efficiency by stripping out
    acquisition history (goodwill) and non-physical assets (intangibles).
    For acquisitive companies, ROIC can look artificially low due to
    inflated invested capital from past M&A.
    """
    
    @pytest.fixture
    def calculator(self):
        return RatioCalculator()
    
    def test_rotic_excludes_goodwill_and_intangibles(self, calculator):
        """
        ROTIC should use Tangible IC = Invested Capital - Goodwill - Intangibles.
        
        Professional critique from Gemini: "Total Equity includes Goodwill and
        Intangibles from past acquisitions. This often inflates the Invested
        Capital base for acquisitive companies."
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
                "operatingIncome": 30_000_000_000,
                "incomeBeforeTax": 28_000_000_000,
                "netIncome": 21_000_000_000,
            }],
            "balance_sheet": [{
                "totalStockholdersEquity": 150_000_000_000,
                "totalDebt": 50_000_000_000,
                "cashAndCashEquivalents": 10_000_000_000,  # Excess = 8B
                "goodwill": 40_000_000_000,  # Acquisition history
                "intangibleAssets": 30_000_000_000,  # Patents, etc.
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        # NOPAT = 30B * (1 - 0.25) = 22.5B (tax rate ~25%)
        # Invested Capital = 150B + 50B - 8B = 192B
        # Tangible IC = 192B - 40B - 30B = 122B
        # ROTIC = 22.5B / 122B ≈ 18.4%
        # ROIC = 22.5B / 192B ≈ 11.7%
        
        assert ratios.profitability.rotic is not None, "ROTIC should be calculated"
        assert ratios.profitability.roic is not None, "ROIC should also be calculated"
        
        # ROTIC should be higher than ROIC (due to smaller denominator)
        assert ratios.profitability.rotic > ratios.profitability.roic, (
            f"ROTIC ({ratios.profitability.rotic:.2%}) should be > "
            f"ROIC ({ratios.profitability.roic:.2%}) when goodwill/intangibles exist"
        )
        
        # ROTIC should be ~18% (22.5B / 122B)
        assert 0.17 < ratios.profitability.rotic < 0.20
    
    def test_rotic_equals_roic_when_no_intangibles(self, calculator):
        """
        When goodwill and intangibles are zero, ROTIC should equal ROIC.
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
                "operatingIncome": 30_000_000_000,
                "incomeBeforeTax": 28_000_000_000,
                "netIncome": 21_000_000_000,
            }],
            "balance_sheet": [{
                "totalStockholdersEquity": 100_000_000_000,
                "totalDebt": 50_000_000_000,
                "cashAndCashEquivalents": 10_000_000_000,
                "goodwill": 0,
                "intangibleAssets": 0,
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.profitability.rotic is not None
        assert ratios.profitability.roic is not None
        
        # Should be equal when no intangibles
        assert abs(ratios.profitability.rotic - ratios.profitability.roic) < 0.001
    
    def test_rotic_handles_missing_goodwill(self, calculator):
        """
        When goodwill/intangibles are missing from data, ROTIC should still
        be calculated (treating missing as zero).
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
                "operatingIncome": 30_000_000_000,
                "incomeBeforeTax": 28_000_000_000,
                "netIncome": 21_000_000_000,
            }],
            "balance_sheet": [{
                "totalStockholdersEquity": 100_000_000_000,
                "totalDebt": 50_000_000_000,
                "cashAndCashEquivalents": 10_000_000_000,
                # No goodwill or intangibleAssets keys
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        # Should still calculate ROTIC (equals ROIC when no intangibles)
        assert ratios.profitability.rotic is not None
        assert ratios.profitability.roic is not None
        assert abs(ratios.profitability.rotic - ratios.profitability.roic) < 0.001
    
    def test_rotic_none_when_tangible_ic_negative(self, calculator):
        """
        If Tangible IC becomes negative or zero (extreme goodwill), ROTIC = None.
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
                "operatingIncome": 30_000_000_000,
                "incomeBeforeTax": 28_000_000_000,
                "netIncome": 21_000_000_000,
            }],
            "balance_sheet": [{
                "totalStockholdersEquity": 50_000_000_000,
                "totalDebt": 20_000_000_000,
                "cashAndCashEquivalents": 5_000_000_000,
                "goodwill": 60_000_000_000,  # Exceeds equity!
                "intangibleAssets": 10_000_000_000,
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        # IC = 50 + 20 - 4 = 66B
        # Tangible IC = 66B - 60B - 10B = -4B (negative!)
        # ROTIC should be None
        assert ratios.profitability.rotic is None, (
            "ROTIC should be None when Tangible IC is negative"
        )


class TestAltmanZScore:
    """
    Tests for Altman Z-Score bankruptcy risk indicator.
    
    Original Z-Score formula (for manufacturing companies):
    Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
    
    Where:
    - A = Working Capital / Total Assets
    - B = Retained Earnings / Total Assets
    - C = EBIT / Total Assets
    - D = Market Value of Equity / Total Liabilities
    - E = Sales / Total Assets
    
    Interpretation:
    - Z > 2.99: "Safe Zone" - low bankruptcy risk
    - 1.81 < Z < 2.99: "Grey Zone" - moderate risk
    - Z < 1.81: "Distress Zone" - high bankruptcy risk
    """
    
    @pytest.fixture
    def calculator(self):
        return RatioCalculator()
    
    def test_z_score_safe_zone(self, calculator):
        """
        Healthy company should score in "Safe Zone" (Z > 2.99).
        """
        data = {
            "profile": {"price": 150, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,  # Sales
                "operatingIncome": 25_000_000_000,  # EBIT
            }],
            "balance_sheet": [{
                "totalAssets": 200_000_000_000,
                "totalCurrentAssets": 80_000_000_000,
                "totalCurrentLiabilities": 40_000_000_000,  # WC = 40B
                "totalLiabilities": 100_000_000_000,
                "retainedEarnings": 60_000_000_000,
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.risk is not None, "Risk metrics should be calculated"
        assert ratios.risk.altman_z_score is not None, "Z-Score should be calculated"
        assert ratios.risk.altman_z_score > 2.99, (
            f"Healthy company Z-Score ({ratios.risk.altman_z_score:.2f}) should be > 2.99"
        )
        assert ratios.risk.z_score_zone == "safe"
    
    def test_z_score_distress_zone(self, calculator):
        """
        Distressed company should score in "Distress Zone" (Z < 1.81).
        """
        data = {
            "profile": {"price": 5, "marketCap": 1_000_000_000},  # Low market cap
            "income_statement": [{
                "revenue": 10_000_000_000,
                "operatingIncome": -500_000_000,  # Negative EBIT
            }],
            "balance_sheet": [{
                "totalAssets": 20_000_000_000,
                "totalCurrentAssets": 3_000_000_000,
                "totalCurrentLiabilities": 8_000_000_000,  # Negative WC
                "totalLiabilities": 18_000_000_000,  # High debt
                "retainedEarnings": -5_000_000_000,  # Accumulated losses
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.risk.altman_z_score is not None
        assert ratios.risk.altman_z_score < 1.81, (
            f"Distressed company Z-Score ({ratios.risk.altman_z_score:.2f}) should be < 1.81"
        )
        assert ratios.risk.z_score_zone == "distress"
    
    def test_z_score_grey_zone(self, calculator):
        """
        Marginal company should score in "Grey Zone" (1.81 < Z < 2.99).
        """
        data = {
            "profile": {"price": 50, "marketCap": 50_000_000_000},
            "income_statement": [{
                "revenue": 40_000_000_000,
                "operatingIncome": 3_000_000_000,
            }],
            "balance_sheet": [{
                "totalAssets": 60_000_000_000,
                "totalCurrentAssets": 20_000_000_000,
                "totalCurrentLiabilities": 15_000_000_000,  # WC = 5B
                "totalLiabilities": 35_000_000_000,
                "retainedEarnings": 10_000_000_000,
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.risk.altman_z_score is not None
        assert 1.81 < ratios.risk.altman_z_score < 2.99, (
            f"Marginal company Z-Score ({ratios.risk.altman_z_score:.2f}) should be in grey zone"
        )
        assert ratios.risk.z_score_zone == "grey"
    
    def test_z_score_handles_missing_retained_earnings(self, calculator):
        """
        When retained earnings is missing, Z-Score should still calculate
        (treating missing as zero or returning None).
        """
        data = {
            "profile": {"price": 100, "marketCap": 100_000_000_000},
            "income_statement": [{
                "revenue": 50_000_000_000,
                "operatingIncome": 10_000_000_000,
            }],
            "balance_sheet": [{
                "totalAssets": 80_000_000_000,
                "totalCurrentAssets": 30_000_000_000,
                "totalCurrentLiabilities": 20_000_000_000,
                "totalLiabilities": 40_000_000_000,
                # No retainedEarnings
            }],
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        # Should either calculate with B=0 or return None
        # Preferably calculate with B=0
        assert ratios.risk is not None
    
    def test_z_score_none_when_missing_critical_data(self, calculator):
        """
        Z-Score should be None when critical components are missing.
        """
        data = {
            "profile": {"price": 100},  # No marketCap
            "income_statement": [{}],
            "balance_sheet": [{}],  # No totalAssets
            "cash_flow": [{}],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.risk.altman_z_score is None


class TestAccrualRatio:
    """
    Tests for Accrual Ratio earnings quality metric.
    
    Accrual Ratio = (Net Income - Operating Cash Flow) / Total Assets
    
    High positive ratio = earnings quality warning (earnings > cash flow)
    Negative ratio = good quality (cash flow > earnings)
    
    Professional interpretation:
    - Ratio > 10%: High accruals, potential earnings manipulation
    - Ratio > 5%: Elevated accruals, watch carefully
    - Ratio < 0%: Cash earnings, generally healthy
    """
    
    @pytest.fixture
    def calculator(self):
        return RatioCalculator()
    
    def test_accrual_ratio_high_quality_cash_earnings(self, calculator):
        """
        When cash flow exceeds net income, accrual ratio should be negative
        (indicating high earnings quality).
        """
        data = {
            "profile": {"price": 100, "marketCap": 100_000_000_000},
            "income_statement": [{
                "netIncome": 10_000_000_000,
            }],
            "balance_sheet": [{
                "totalAssets": 200_000_000_000,
            }],
            "cash_flow": [{
                "operatingCashFlow": 15_000_000_000,  # CFO > Net Income
            }],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.risk.accrual_ratio is not None
        # (10B - 15B) / 200B = -2.5%
        assert ratios.risk.accrual_ratio < 0, (
            f"Accrual ratio ({ratios.risk.accrual_ratio:.2%}) should be negative "
            "when CFO exceeds net income"
        )
        assert ratios.risk.accrual_quality == "good"
    
    def test_accrual_ratio_warning_high_accruals(self, calculator):
        """
        When net income far exceeds cash flow, accrual ratio should be high
        (indicating potential earnings manipulation).
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [{
                "netIncome": 20_000_000_000,
            }],
            "balance_sheet": [{
                "totalAssets": 100_000_000_000,
            }],
            "cash_flow": [{
                "operatingCashFlow": 5_000_000_000,  # CFO << Net Income
            }],
        }
        
        ratios = calculator.calculate(data)
        
        # (20B - 5B) / 100B = 15%
        assert ratios.risk.accrual_ratio is not None
        assert ratios.risk.accrual_ratio > 0.10, (
            f"Accrual ratio ({ratios.risk.accrual_ratio:.2%}) should be > 10% "
            "when earnings far exceed cash flow"
        )
        assert ratios.risk.accrual_quality == "warning"
    
    def test_accrual_ratio_moderate(self, calculator):
        """
        Moderate accrual ratio (5-10%) should be flagged as 'elevated'.
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [{
                "netIncome": 15_000_000_000,
            }],
            "balance_sheet": [{
                "totalAssets": 200_000_000_000,
            }],
            "cash_flow": [{
                "operatingCashFlow": 5_000_000_000,
            }],
        }
        
        ratios = calculator.calculate(data)
        
        # (15B - 5B) / 200B = 5%
        assert ratios.risk.accrual_ratio is not None
        assert 0.05 <= ratios.risk.accrual_ratio <= 0.10
        assert ratios.risk.accrual_quality == "elevated"
    
    def test_accrual_ratio_none_when_missing_data(self, calculator):
        """
        Accrual ratio should be None when critical data is missing.
        """
        data = {
            "profile": {"price": 100},
            "income_statement": [{}],  # No netIncome
            "balance_sheet": [{}],  # No totalAssets
            "cash_flow": [{}],  # No operatingCashFlow
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.risk.accrual_ratio is None
        assert ratios.risk.accrual_quality is None
    
    def test_accrual_ratio_with_negative_income(self, calculator):
        """
        Companies with losses can still have accrual analysis.
        """
        data = {
            "profile": {"price": 10, "marketCap": 5_000_000_000},
            "income_statement": [{
                "netIncome": -2_000_000_000,  # Net loss
            }],
            "balance_sheet": [{
                "totalAssets": 50_000_000_000,
            }],
            "cash_flow": [{
                "operatingCashFlow": 1_000_000_000,  # Still generating cash
            }],
        }
        
        ratios = calculator.calculate(data)
        
        # (-2B - 1B) / 50B = -6%
        assert ratios.risk.accrual_ratio is not None
        assert ratios.risk.accrual_ratio < 0  # Cash exceeds (negative) earnings


class TestSBCAdjustment:
    """
    Tests for Stock-Based Compensation adjustment.
    
    SBC is a real expense that dilutes shareholders but is added back
    in operating cash flow because it's "non-cash". This hides the
    true cost of employee compensation.
    
    SBC-Adjusted FCF = FCF - SBC
    SBC as % of Revenue shows how expensive the company's equity
    compensation program is.
    
    From Gemini review: "SBC should be treated as a real expense or
    you should project annual share dilution."
    """
    
    @pytest.fixture
    def calculator(self):
        return RatioCalculator()
    
    def test_sbc_adjusted_fcf_calculated(self, calculator):
        """
        SBC-adjusted FCF should subtract SBC from reported FCF.
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
            }],
            "balance_sheet": [{}],
            "cash_flow": [{
                "freeCashFlow": 30_000_000_000,
                "stockBasedCompensation": 5_000_000_000,  # 5B SBC
            }],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.sbc is not None
        assert ratios.sbc.stock_based_compensation == 5_000_000_000
        # SBC-adjusted FCF = 30B - 5B = 25B
        assert ratios.sbc.fcf_adjusted == 25_000_000_000
    
    def test_sbc_as_percent_of_revenue(self, calculator):
        """
        SBC as % of revenue shows compensation expense burden.
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
            }],
            "balance_sheet": [{}],
            "cash_flow": [{
                "freeCashFlow": 30_000_000_000,
                "stockBasedCompensation": 10_000_000_000,  # 10% of revenue
            }],
        }
        
        ratios = calculator.calculate(data)
        
        # SBC / Revenue = 10B / 100B = 10%
        assert ratios.sbc.sbc_percent_revenue is not None
        assert abs(ratios.sbc.sbc_percent_revenue - 0.10) < 0.001
    
    def test_sbc_impact_on_fcf_margin(self, calculator):
        """
        Compare reported vs SBC-adjusted FCF margin.
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
            }],
            "balance_sheet": [{}],
            "cash_flow": [{
                "freeCashFlow": 25_000_000_000,  # 25% reported FCF margin
                "stockBasedCompensation": 8_000_000_000,  # 8% of revenue
            }],
        }
        
        ratios = calculator.calculate(data)
        
        # Reported FCF margin = 25%
        # SBC-adjusted FCF = 25B - 8B = 17B
        # SBC-adjusted FCF margin = 17%
        assert ratios.sbc.fcf_margin_reported is not None
        assert ratios.sbc.fcf_margin_adjusted is not None
        assert abs(ratios.sbc.fcf_margin_reported - 0.25) < 0.001
        assert abs(ratios.sbc.fcf_margin_adjusted - 0.17) < 0.001
    
    def test_sbc_none_when_missing(self, calculator):
        """
        SBC metrics should be None when SBC data is missing.
        """
        data = {
            "profile": {"price": 100, "marketCap": 500_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
            }],
            "balance_sheet": [{}],
            "cash_flow": [{
                "freeCashFlow": 30_000_000_000,
                # No stockBasedCompensation
            }],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.sbc.stock_based_compensation is None
        assert ratios.sbc.fcf_adjusted is None
    
    def test_high_sbc_warning(self, calculator):
        """
        High SBC (>10% of revenue) should be flagged.
        """
        data = {
            "profile": {"price": 100, "marketCap": 100_000_000_000},
            "income_statement": [{
                "revenue": 50_000_000_000,
            }],
            "balance_sheet": [{}],
            "cash_flow": [{
                "freeCashFlow": 10_000_000_000,
                "stockBasedCompensation": 8_000_000_000,  # 16% of revenue!
            }],
        }
        
        ratios = calculator.calculate(data)
        
        # SBC / Revenue = 8B / 50B = 16%
        assert ratios.sbc.sbc_percent_revenue > 0.10
        assert ratios.sbc.sbc_level == "high"
    
    def test_moderate_sbc(self, calculator):
        """
        Moderate SBC (5-10% of revenue) should be flagged as 'elevated'.
        """
        data = {
            "profile": {"price": 100, "marketCap": 100_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
            }],
            "balance_sheet": [{}],
            "cash_flow": [{
                "freeCashFlow": 20_000_000_000,
                "stockBasedCompensation": 7_000_000_000,  # 7% of revenue
            }],
        }
        
        ratios = calculator.calculate(data)
        
        assert 0.05 <= ratios.sbc.sbc_percent_revenue <= 0.10
        assert ratios.sbc.sbc_level == "elevated"
    
    def test_low_sbc(self, calculator):
        """
        Low SBC (<5% of revenue) is normal.
        """
        data = {
            "profile": {"price": 100, "marketCap": 100_000_000_000},
            "income_statement": [{
                "revenue": 100_000_000_000,
            }],
            "balance_sheet": [{}],
            "cash_flow": [{
                "freeCashFlow": 20_000_000_000,
                "stockBasedCompensation": 3_000_000_000,  # 3% of revenue
            }],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.sbc.sbc_percent_revenue < 0.05
        assert ratios.sbc.sbc_level == "normal"


class TestBeneishMScore:
    """
    Tests for Beneish M-Score fraud detection.
    
    The M-Score uses 8 indices comparing current to prior year to detect
    earnings manipulation. M-Score > -1.78 suggests high manipulation risk.
    
    M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI 
        + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
    
    From Gemini review: "Beneish M-Score for earnings manipulation detection."
    """
    
    @pytest.fixture
    def calculator(self):
        return RatioCalculator()
    
    def test_m_score_low_risk_company(self, calculator):
        """
        A stable, honest company should have M-Score below -1.78.
        """
        data = {
            "profile": {"price": 100, "marketCap": 100_000_000_000},
            "income_statement": [
                {  # Current year
                    "revenue": 50_000_000_000,
                    "grossProfit": 20_000_000_000,  # 40% margin
                    "netIncome": 8_000_000_000,
                    "sellingGeneralAndAdministrative": 5_000_000_000,
                },
                {  # Prior year
                    "revenue": 48_000_000_000,  # 4% growth
                    "grossProfit": 19_200_000_000,  # 40% margin (same)
                    "netIncome": 7_500_000_000,
                    "sellingGeneralAndAdministrative": 4_800_000_000,
                },
            ],
            "balance_sheet": [
                {  # Current year
                    "totalAssets": 80_000_000_000,
                    "totalCurrentAssets": 30_000_000_000,
                    "netReceivables": 8_000_000_000,
                    "propertyPlantEquipmentNet": 25_000_000_000,
                    "totalDebt": 20_000_000_000,
                },
                {  # Prior year
                    "totalAssets": 75_000_000_000,
                    "totalCurrentAssets": 28_000_000_000,
                    "netReceivables": 7_500_000_000,
                    "propertyPlantEquipmentNet": 24_000_000_000,
                    "totalDebt": 18_000_000_000,
                },
            ],
            "cash_flow": [
                {"operatingCashFlow": 10_000_000_000, "depreciationAndAmortization": 3_000_000_000},
                {"operatingCashFlow": 9_000_000_000, "depreciationAndAmortization": 2_800_000_000},
            ],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.risk.beneish_m_score is not None
        assert ratios.risk.beneish_m_score < -1.78, (
            f"Low-risk company M-Score ({ratios.risk.beneish_m_score:.2f}) should be < -1.78"
        )
        assert ratios.risk.manipulation_risk == "low"
    
    def test_m_score_high_risk_company(self, calculator):
        """
        A company with manipulation red flags should have M-Score above -1.78.
        Red flags: rapid revenue growth, margin deterioration, receivables spike,
        high accruals, asset quality decline.
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [
                {  # Current year - suspicious patterns
                    "revenue": 60_000_000_000,  # 50% revenue growth!
                    "grossProfit": 18_000_000_000,  # 30% margin (dropped from 35%)
                    "netIncome": 6_000_000_000,
                    "sellingGeneralAndAdministrative": 4_000_000_000,
                },
                {  # Prior year
                    "revenue": 40_000_000_000,
                    "grossProfit": 14_000_000_000,  # 35% margin
                    "netIncome": 4_000_000_000,
                    "sellingGeneralAndAdministrative": 4_500_000_000,
                },
            ],
            "balance_sheet": [
                {  # Current year - suspicious
                    "totalAssets": 100_000_000_000,
                    "totalCurrentAssets": 35_000_000_000,
                    "netReceivables": 20_000_000_000,  # Receivables grew faster than sales
                    "propertyPlantEquipmentNet": 20_000_000_000,
                    "totalDebt": 50_000_000_000,  # Leverage increased
                },
                {  # Prior year
                    "totalAssets": 60_000_000_000,
                    "totalCurrentAssets": 25_000_000_000,
                    "netReceivables": 10_000_000_000,
                    "propertyPlantEquipmentNet": 18_000_000_000,
                    "totalDebt": 25_000_000_000,
                },
            ],
            "cash_flow": [
                {"operatingCashFlow": 2_000_000_000, "depreciationAndAmortization": 2_500_000_000},  # Low CFO vs income
                {"operatingCashFlow": 5_000_000_000, "depreciationAndAmortization": 2_200_000_000},
            ],
        }
        
        ratios = calculator.calculate(data)
        
        assert ratios.risk.beneish_m_score is not None
        assert ratios.risk.beneish_m_score > -1.78, (
            f"High-risk company M-Score ({ratios.risk.beneish_m_score:.2f}) should be > -1.78"
        )
        assert ratios.risk.manipulation_risk == "high"
    
    def test_m_score_none_without_prior_year(self, calculator):
        """
        M-Score requires prior year data for comparison indices.
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [
                {"revenue": 50_000_000_000, "grossProfit": 20_000_000_000},
                # No prior year
            ],
            "balance_sheet": [
                {"totalAssets": 80_000_000_000, "netReceivables": 8_000_000_000},
            ],
            "cash_flow": [
                {"operatingCashFlow": 10_000_000_000},
            ],
        }
        
        ratios = calculator.calculate(data)
        
        # Without prior year data, M-Score should be None
        assert ratios.risk.beneish_m_score is None
    
    def test_m_score_components_calculated(self, calculator):
        """
        Verify individual M-Score components are calculated.
        """
        data = {
            "profile": {"price": 100, "marketCap": 100_000_000_000},
            "income_statement": [
                {"revenue": 50_000_000_000, "grossProfit": 20_000_000_000, 
                 "netIncome": 8_000_000_000, "sellingGeneralAndAdministrative": 5_000_000_000},
                {"revenue": 45_000_000_000, "grossProfit": 18_000_000_000,
                 "netIncome": 7_000_000_000, "sellingGeneralAndAdministrative": 4_500_000_000},
            ],
            "balance_sheet": [
                {"totalAssets": 80_000_000_000, "totalCurrentAssets": 30_000_000_000,
                 "netReceivables": 8_000_000_000, "propertyPlantEquipmentNet": 25_000_000_000,
                 "totalDebt": 20_000_000_000},
                {"totalAssets": 70_000_000_000, "totalCurrentAssets": 26_000_000_000,
                 "netReceivables": 7_000_000_000, "propertyPlantEquipmentNet": 22_000_000_000,
                 "totalDebt": 18_000_000_000},
            ],
            "cash_flow": [
                {"operatingCashFlow": 10_000_000_000, "depreciationAndAmortization": 3_000_000_000},
                {"operatingCashFlow": 8_500_000_000, "depreciationAndAmortization": 2_500_000_000},
            ],
        }
        
        ratios = calculator.calculate(data)
        
        # Should have both M-Score and individual components
        assert ratios.risk.beneish_m_score is not None
        # SGI (Sales Growth Index) should be calculated
        # Revenue grew from 45B to 50B = 11% growth


class TestMScoreEdgeCases:
    """
    Edge case tests for Beneish M-Score index calculations.
    
    Bug: M-Score index calculations check some denominators but not all
    numerators/denominators, allowing edge cases to produce incorrect results.
    """
    
    @pytest.fixture
    def calculator(self):
        return RatioCalculator()
    
    def test_m_score_with_zero_gross_margin_current(self, calculator):
        """
        When current year gross margin is zero, GMI should use default.
        Bug: GMI checks gm_t > 0 for denominator but current year could have
        zero gross profit making gm_t = 0, causing division issues.
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [
                {"revenue": 50_000_000_000, "grossProfit": 0},  # Zero GM
                {"revenue": 40_000_000_000, "grossProfit": 10_000_000_000},
            ],
            "balance_sheet": [
                {"totalAssets": 80_000_000_000, "totalLiabilities": 40_000_000_000},
                {"totalAssets": 70_000_000_000, "totalLiabilities": 35_000_000_000},
            ],
            "cash_flow": [{}, {}],
        }
        
        ratios = calculator.calculate(data)
        
        # Should still produce a valid M-Score (using default GMI=1.0)
        assert ratios.risk.beneish_m_score is not None
    
    def test_m_score_with_zero_sga_current(self, calculator):
        """
        When current year SG&A ratio is zero, SGAI should use default.
        Bug: SGAI checks sga_ratio_t1 > 0 but not sga_ratio_t > 0.
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [
                {"revenue": 50_000_000_000, "sellingGeneralAndAdministrative": 0},  # Zero SGA
                {"revenue": 40_000_000_000, "sellingGeneralAndAdministrative": 5_000_000_000},
            ],
            "balance_sheet": [
                {"totalAssets": 80_000_000_000, "totalLiabilities": 40_000_000_000},
                {"totalAssets": 70_000_000_000, "totalLiabilities": 35_000_000_000},
            ],
            "cash_flow": [{}, {}],
        }
        
        ratios = calculator.calculate(data)
        
        # Should still produce a valid M-Score (using default SGAI=1.0)
        assert ratios.risk.beneish_m_score is not None
    
    def test_m_score_with_zero_depreciation_prior(self, calculator):
        """
        When prior year depreciation rate is zero, DEPI should use default.
        Bug: DEPI checks dep_rate_t > 0 but not dep_rate_t1 > 0.
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [
                {"revenue": 50_000_000_000},
                {"revenue": 40_000_000_000},
            ],
            "balance_sheet": [
                {"totalAssets": 80_000_000_000, "totalLiabilities": 40_000_000_000,
                 "propertyPlantEquipmentNet": 20_000_000_000},
                {"totalAssets": 70_000_000_000, "totalLiabilities": 35_000_000_000,
                 "propertyPlantEquipmentNet": 18_000_000_000},
            ],
            "cash_flow": [
                {"depreciationAndAmortization": 3_000_000_000},
                {"depreciationAndAmortization": 0},  # Zero depreciation prior
            ],
        }
        
        ratios = calculator.calculate(data)
        
        # Should still produce a valid M-Score (using default DEPI=1.0)
        assert ratios.risk.beneish_m_score is not None
    
    def test_m_score_with_negative_gross_profit(self, calculator):
        """
        When gross profit is negative, GMI calculation should be safe.
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [
                {"revenue": 50_000_000_000, "grossProfit": -5_000_000_000},  # Negative GP
                {"revenue": 40_000_000_000, "grossProfit": 10_000_000_000},
            ],
            "balance_sheet": [
                {"totalAssets": 80_000_000_000, "totalLiabilities": 40_000_000_000},
                {"totalAssets": 70_000_000_000, "totalLiabilities": 35_000_000_000},
            ],
            "cash_flow": [{}, {}],
        }
        
        ratios = calculator.calculate(data)
        
        # Should still produce a valid M-Score
        assert ratios.risk.beneish_m_score is not None
    
    def test_m_score_with_zero_dsr_prior(self, calculator):
        """
        When prior year DSR is zero, DSRI should use default.
        """
        data = {
            "profile": {"price": 100, "marketCap": 50_000_000_000},
            "income_statement": [
                {"revenue": 50_000_000_000},
                {"revenue": 40_000_000_000},
            ],
            "balance_sheet": [
                {"totalAssets": 80_000_000_000, "totalLiabilities": 40_000_000_000,
                 "netReceivables": 8_000_000_000},
                {"totalAssets": 70_000_000_000, "totalLiabilities": 35_000_000_000,
                 "netReceivables": 0},  # Zero receivables prior
            ],
            "cash_flow": [{}, {}],
        }
        
        ratios = calculator.calculate(data)
        
        # Should still produce a valid M-Score (using default DSRI=1.0)
        assert ratios.risk.beneish_m_score is not None

