"""
Tests for ComparableAnalyzer service.

Focus on EBITDA wiring regression test - ensuring D&A is read from 
cash_flow, not income_statement.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.comparable_analyzer import ComparableAnalyzer, CompanyMetrics


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
