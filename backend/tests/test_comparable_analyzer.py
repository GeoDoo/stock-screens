"""
Tests for ComparableAnalyzer service.

Focus on EBITDA wiring regression test - ensuring D&A is read from 
cash_flow, not income_statement.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.comparable_analyzer import ComparableAnalyzer, CompanyMetrics, ImpliedValuation


class TestComparableAnalyzerEBITDAWiring:
    """
    Regression tests for EBITDA calculation in ComparableAnalyzer.
    
    Bug: D&A was being read from income_statement (financials), but 
    stock_data_to_legacy() places it in cash_flow. This caused EBITDA
    to equal operating_income (D&A treated as 0), making EV/EBITDA incorrect.
    """

    def test_extract_metrics_reads_da_from_cash_flow(self):
        """
        _extract_metrics should read D&A from cash_flow, not income_statement.
        """
        # Create analyzer with mock client
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Realistic data structure: D&A in cash_flow only (as produced by stock_data_to_legacy)
        data = {
            "profile": {
                "price": 150.0,
                "marketCap": 2400000000000,  # 2.4T
                "sharesOutstanding": 16000000000,
            },
            "income_statement": [
                {
                    "revenue": 400000000000,  # 400B
                    "netIncome": 100000000000,  # 100B
                    "operatingIncome": 120000000000,  # 120B
                    # NOTE: No depreciationAndAmortization here!
                }
            ],
            "balance_sheet": [
                {
                    "totalDebt": 100000000000,  # 100B
                    "cashAndCashEquivalents": 25000000000,  # 25B
                    "totalStockholdersEquity": 60000000000,  # 60B
                }
            ],
            "cash_flow": [
                {
                    # D&A is in cash_flow, as produced by stock_data_to_legacy()
                    "depreciationAndAmortization": 10000000000,  # 10B
                }
            ],
        }
        
        metrics = analyzer._extract_metrics("AAPL", data)
        
        # EBITDA = Operating Income (120B) + D&A (10B) = 130B
        # EV = 2.4T + 100B - 25B = 2.475T
        # EV/EBITDA = 2.475T / 130B = 19.04
        
        # If bug exists: EBITDA = 120B (D&A=0 because read from wrong location)
        # EV/EBITDA would be 2.475T / 120B = 20.625 (WRONG)
        
        assert metrics.ev_to_ebitda == pytest.approx(19.04, rel=0.01), (
            f"EV/EBITDA should be ~19.04 but got {metrics.ev_to_ebitda}. "
            "D&A is being read from income_statement instead of cash_flow."
        )

    def test_extract_metrics_handles_missing_da_gracefully(self):
        """
        If D&A is missing from cash_flow, should still calculate EBITDA 
        (just without D&A component, i.e. EBITDA = operating_income).
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        data = {
            "profile": {
                "price": 100.0,
                "marketCap": 1000000000000,  # 1T
                "sharesOutstanding": 10000000000,
            },
            "income_statement": [
                {
                    "operatingIncome": 50000000000,  # 50B
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
                    # No D&A at all
                }
            ],
        }
        
        metrics = analyzer._extract_metrics("TEST", data)
        
        # EBITDA = 50B + 0 = 50B
        # EV = 1T
        # EV/EBITDA = 1T / 50B = 20
        
        assert metrics.ev_to_ebitda == pytest.approx(20.0, rel=0.01)


class TestEVEBITDAImpliedValuation:
    """
    Regression tests for EV/EBITDA implied price calculation.
    
    Bug: The old code used "ratio of ratios" shortcut:
        implied_price = current_price × (peer_multiple / target_multiple)
    
    This is financially invalid because it assumes Net Debt scales with
    stock price, but debt is a fixed contract. The correct approach:
        1. Implied EV = Peer EV/EBITDA × Target EBITDA
        2. Implied Equity = Implied EV - Target Net Debt
        3. Implied Price = Implied Equity / Shares
    """
    
    def test_ev_ebitda_implied_price_correct_method(self):
        """
        EV/EBITDA implied price should use proper EV-to-equity bridge.
        
        Example with significant leverage:
        - Target: Price $100, EV/EBITDA 10x, EBITDA $100B, Net Debt $500B
        - Peer Median: EV/EBITDA 15x
        
        WRONG (ratio of ratios):
            implied = $100 × (15/10) = $150 (50% upside)
        
        CORRECT (EV bridge):
            Implied EV = 15 × $100B = $1.5T
            Current EV = 10 × $100B = $1.0T
            Current Equity = $1.0T - $500B = $500B
            Implied Equity = $1.5T - $500B = $1.0T (2x, not 1.5x!)
            Implied Price = $100 × ($1.0T / $500B) = $200 (100% upside!)
        
        For leveraged companies, the correct method shows MORE upside
        because debt amplifies equity returns.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Create target with significant leverage
        target = CompanyMetrics(
            symbol="LEVCO",
            name="Leveraged Company",
            price=100.0,
            market_cap=500_000_000_000,  # $500B market cap (equity)
            ev_to_ebitda=10.0,
            # Additional fields needed for proper calculation
            ebitda=100_000_000_000,  # $100B EBITDA
            net_debt=500_000_000_000,  # $500B net debt (EV = 1T)
            shares_outstanding=5_000_000_000,  # 5B shares → $100/share
        )
        
        peer_medians = {
            "ev_to_ebitda": 15.0,  # Peers trade at 15x
        }
        
        valuations = analyzer._calculate_implied_valuations(target, peer_medians)
        
        # Find EV/EBITDA valuation
        ev_ebitda_val = next(
            (v for v in valuations if v.metric_name == "EV/EBITDA"), 
            None
        )
        
        assert ev_ebitda_val is not None, "Should have EV/EBITDA implied valuation"
        
        # Correct calculation:
        # Implied EV = 15x × $100B = $1.5T
        # Implied Equity = $1.5T - $500B = $1.0T
        # Implied Price = $1.0T / 5B shares = $200
        expected_implied_price = 200.0
        
        # Wrong calculation would give: $100 × (15/10) = $150
        wrong_implied_price = 150.0
        
        assert ev_ebitda_val.implied_price == pytest.approx(expected_implied_price, rel=0.01), (
            f"EV/EBITDA implied price should be ${expected_implied_price} "
            f"(correct EV bridge), got ${ev_ebitda_val.implied_price}. "
            f"If got ${wrong_implied_price}, the 'ratio of ratios' bug is present."
        )
        
        # Upside should be 100%, not 50%
        assert ev_ebitda_val.upside_percent == pytest.approx(100.0, rel=1), (
            f"Upside should be ~100% for leveraged company, got {ev_ebitda_val.upside_percent}%"
        )
    
    def test_ev_ebitda_implied_price_no_debt(self):
        """
        With zero net debt, both methods should give same result.
        This validates the math converges in the simple case.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Debt-free company: EV = Equity
        target = CompanyMetrics(
            symbol="NODET",
            name="No Debt Corp",
            price=100.0,
            market_cap=1_000_000_000_000,  # $1T
            ev_to_ebitda=10.0,
            ebitda=100_000_000_000,  # $100B
            net_debt=0,  # No debt!
            shares_outstanding=10_000_000_000,
        )
        
        peer_medians = {"ev_to_ebitda": 15.0}
        
        valuations = analyzer._calculate_implied_valuations(target, peer_medians)
        ev_ebitda_val = next((v for v in valuations if v.metric_name == "EV/EBITDA"), None)
        
        # With no debt: Implied EV = Implied Equity
        # Implied EV = 15 × $100B = $1.5T
        # Implied Price = $1.5T / 10B = $150
        assert ev_ebitda_val.implied_price == pytest.approx(150.0, rel=0.01)
        assert ev_ebitda_val.upside_percent == pytest.approx(50.0, rel=1)
    
    def test_ev_ebitda_with_net_cash(self):
        """
        Companies with net cash (negative net debt) should also work correctly.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Company with net cash: Market cap > EV
        target = CompanyMetrics(
            symbol="CASHCO",
            name="Cash Rich Corp",
            price=100.0,
            market_cap=1_200_000_000_000,  # $1.2T market cap
            ev_to_ebitda=10.0,
            ebitda=100_000_000_000,  # $100B
            net_debt=-200_000_000_000,  # -$200B (net cash)
            shares_outstanding=12_000_000_000,
        )
        
        peer_medians = {"ev_to_ebitda": 15.0}
        
        valuations = analyzer._calculate_implied_valuations(target, peer_medians)
        ev_ebitda_val = next((v for v in valuations if v.metric_name == "EV/EBITDA"), None)
        
        # Implied EV = 15 × $100B = $1.5T
        # Implied Equity = $1.5T - (-$200B) = $1.7T
        # Implied Price = $1.7T / 12B = $141.67
        assert ev_ebitda_val.implied_price == pytest.approx(141.67, rel=0.01)
