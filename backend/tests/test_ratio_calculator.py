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

