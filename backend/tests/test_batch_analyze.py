"""Tests for batched analyze endpoint."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement

client = TestClient(app)


def create_mock_stock_data():
    """Create mock stock data for testing."""
    return StockData(
        profile=CompanyProfile(
            symbol="AAPL",
            name="Apple Inc.",
            price=190.0,
            market_cap=3000000000000,
            beta=1.25,
            shares_outstanding=15744231000,
            currency="USD",
            exchange="NASDAQ",
            industry="Consumer Electronics",
            sector="Technology",
        ),
        financials=[
            FinancialStatement(
                date="2024-01-01",
                period="annual",
                revenue=383285000000,
                cost_of_revenue=214137000000,
                gross_profit=169148000000,
                operating_income=114301000000,
                net_income=96995000000,
                interest_expense=3933000000,
                income_tax_expense=16741000000,
                total_assets=352583000000,
                total_liabilities=290437000000,
                total_equity=62146000000,
                total_debt=111088000000,
                cash_and_equivalents=29965000000,
                current_assets=143566000000,
                current_liabilities=145308000000,
                operating_cash_flow=110543000000,
                capital_expenditure=-10959000000,
                free_cash_flow=99584000000,
                depreciation_amortization=11519000000,
                dividends_paid=-15000000000,
            ),
            FinancialStatement(
                date="2023-01-01",
                period="annual",
                revenue=365817000000,
                cost_of_revenue=208000000000,
                gross_profit=157817000000,
                operating_income=108949000000,
                net_income=94680000000,
                interest_expense=2645000000,
                income_tax_expense=14527000000,
                total_assets=330000000000,
                total_liabilities=268000000000,
                total_equity=62000000000,
                total_debt=100000000000,
                cash_and_equivalents=25000000000,
                current_assets=140000000000,
                current_liabilities=140000000000,
                operating_cash_flow=100000000000,
                capital_expenditure=-10000000000,
                free_cash_flow=90000000000,
                depreciation_amortization=11000000000,
                dividends_paid=-14000000000,
            ),
        ],
        provider="fmp",
    )


class TestBatchAnalyzeEndpoint:
    """Tests for the /api/stock/{symbol}/analyze endpoint."""
    
    def test_batch_analyze_returns_all_data(self):
        """Batch analyze should return stock data, ratios, dividends, and historical valuation."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=["MSFT", "GOOGL"])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")

            assert response.status_code == 200
            data = response.json()
            
            # Should have all sections
            assert "stock" in data
            assert "ratios" in data
            assert "dividends" in data
            assert "historical_valuation" in data
            
            # Stock data should be present
            assert data["stock"]["symbol"] == "AAPL"
            assert data["stock"]["company_name"] == "Apple Inc."
    
    def test_batch_analyze_includes_provenance(self):
        """
        P1 Fix: /analyze endpoint should include is_using_ltm and provenance
        for consistency with /stock endpoint.
        
        Bug: Frontend calls /analyze but ProvenanceBadge system had nothing
        to show because these fields were missing.
        """
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=["MSFT", "GOOGL"])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")

            assert response.status_code == 200
            data = response.json()
            
            # P1: Should include provenance fields for transparency
            assert "is_using_ltm" in data["stock"], \
                "Response should include is_using_ltm for data source transparency"
            assert "provenance" in data["stock"], \
                "Response should include provenance for metric source tracking"
            
            # Provenance should have expected structure
            provenance = data["stock"]["provenance"]
            assert provenance is not None
            # Should have tax_rate provenance at minimum
            assert "tax_rate" in provenance
    
    def test_batch_analyze_reduces_api_calls(self):
        """Batch analyze should make fewer API calls than individual endpoints."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=["MSFT", "GOOGL"])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")
            
            assert response.status_code == 200
            
            # Should only call get_stock_data once (not multiple times for each section)
            assert mock_client.get_stock_data.call_count == 1
    
    def test_batch_analyze_includes_rate_limit_stats(self):
        """Batch analyze should include rate limit statistics."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=[])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")

            assert response.status_code == 200
            data = response.json()
            
            assert "rate_limit" in data
            assert "used" in data["rate_limit"]
            assert "remaining" in data["rate_limit"]


class TestDividendCalculation:
    """REGRESSION: Tests for correct per-share dividend calculation."""
    
    def test_dividends_are_per_share_not_total(self):
        """
        REGRESSION TEST: dividends should be per-share (e.g. $0.95), not total company (e.g. $15B).
        
        Bug: batch endpoint used fin.dividends_paid (total) directly instead of dividing
        by shares_outstanding to get per-share amount.
        """
        mock_stock_data = create_mock_stock_data()
        # Mock data has: dividends_paid = $15B, shares = 15.7B
        # Per-share should be ~$0.95, NOT $15B
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=[])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")

            assert response.status_code == 200
            data = response.json()
            
            dividends = data["dividends"]
            assert dividends["has_dividends"] is True
            
            # Current annual dividend should be reasonable per-share value
            # Mock has ~$15B total / 15.7B shares = ~$0.95/share
            annual_div = dividends["current_annual_dividend"]
            assert annual_div is not None
            assert annual_div < 100, f"Dividend ${annual_div} looks like total not per-share!"
            assert annual_div > 0.1, f"Dividend ${annual_div} seems too low"
            
            # Yield should be reasonable (0.5-5% typical)
            current_yield = dividends["current_yield"]
            if current_yield is not None:
                assert current_yield < 0.5, f"Yield {current_yield*100}% is unreasonable - data not per-share!"
                assert current_yield > 0.001, f"Yield {current_yield*100}% seems too low"
    
    def test_dividend_payments_are_per_share(self):
        """Individual dividend payments should be per-share amounts."""
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        mock_client.get_peer_symbols = AsyncMock(return_value=[])
        mock_client.get_company_metrics = AsyncMock(return_value={})

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            response = client.get("/api/stock/AAPL/analyze?provider=fmp")
            data = response.json()
            
            payments = data["dividends"].get("payments", [])
            for payment in payments:
                # Per-share dividends are typically $0.20-$5.00 range
                # Total company dividends are billions
                assert payment["amount"] < 100, f"Payment ${payment['amount']} looks like total not per-share!"


class TestRateLimitEndpoint:
    """Tests for the /api/rate-limits endpoint."""
    
    def test_get_rate_limits(self):
        """Should return current rate limit stats for all providers."""
        response = client.get("/api/rate-limits")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fmp" in data
        assert "yahoo" in data
        assert "massive" in data
        
        # Each should have stats
        assert "used" in data["fmp"]
        assert "limit" in data["fmp"]
        assert "remaining" in data["fmp"]
    
    def test_reset_rate_limits(self):
        """Should be able to reset rate limit counts."""
        # First, make some calls to increment
        mock_stock_data = create_mock_stock_data()
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)

        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client):
            client.get("/api/stock/AAPL?provider=fmp")
        
        # Reset
        response = client.post("/api/rate-limits/reset")
        assert response.status_code == 200
        
        # Check counts are reset
        response = client.get("/api/rate-limits")
        data = response.json()
        assert data["fmp"]["used"] == 0




class TestAsyncSafety:
    """
    Regression tests for async-safety in batch_analyze.
    
    Bug: batch_analyze was marked async but called blocking yfinance 
    methods directly, which could block the event loop.
    
    Fix: All blocking I/O is now wrapped with run_in_executor().
    """
    
    def test_yahoo_provider_has_async_ttm_method(self):
        """
        YahooProvider should have an async get_ttm_financials method.
        
        This ensures the blocking yfinance call is run in a thread pool.
        """
        from app.services.yahoo_provider import YahooProvider
        import asyncio
        
        yahoo = YahooProvider()
        
        # Method should exist and be a coroutine function
        assert hasattr(yahoo, 'get_ttm_financials')
        assert asyncio.iscoroutinefunction(yahoo.get_ttm_financials)
    
    def test_yahoo_provider_has_async_dividends_method(self):
        """
        YahooProvider should have an async get_dividends method.
        
        This ensures the blocking yfinance dividend call is run in a thread pool.
        """
        from app.services.yahoo_provider import YahooProvider
        import asyncio
        
        yahoo = YahooProvider()
        
        # Method should exist and be a coroutine function
        assert hasattr(yahoo, 'get_dividends')
        assert asyncio.iscoroutinefunction(yahoo.get_dividends)


class TestTTMRevenueGrowth:
    """
    P0 Fix: TTM hints must calculate true YoY TTM revenue growth,
    not copy the stale annual CAGR.
    
    Bug: hints_ttm["revenue_growth"] was simply copying hints_annual["revenue_growth"]
    which uses historical CAGR (3-5 year average). This is wrong for TTM mode
    where users expect current trailing growth.
    
    Fix: Calculate TTM revenue growth as (TTM_revenue / prior_year_revenue) - 1
    """
    
    def test_ttm_hints_revenue_growth_differs_from_annual(self):
        """
        TTM revenue growth should be calculated independently,
        not copied from annual hints.
        
        Example: Company with:
        - Historical CAGR: 10% (from 3-5 year average)
        - TTM Revenue: 110B
        - Prior Year Revenue: 100B
        - True TTM Growth: 10%
        
        If historical CAGR was 15%, TTM hints should show 10%, not 15%.
        """
        # Mock data with different historical vs current growth
        mock_stock_data = create_mock_stock_data()
        
        # Override financials to show 15% historical CAGR but 5% TTM growth
        mock_stock_data.financials = [
            FinancialStatement(
                date="2024-01-01", period="annual",
                revenue=100_000_000_000,  # Current year: 100B
                operating_income=15_000_000_000,
                net_income=10_000_000_000,
                total_assets=200_000_000_000,
                total_liabilities=100_000_000_000,
                total_equity=100_000_000_000,
            ),
            FinancialStatement(
                date="2023-01-01", period="annual",
                revenue=87_000_000_000,  # Prior year: 87B (~15% CAGR)
                operating_income=13_000_000_000,
                net_income=9_000_000_000,
                total_assets=180_000_000_000,
                total_liabilities=90_000_000_000,
                total_equity=90_000_000_000,
            ),
            FinancialStatement(
                date="2022-01-01", period="annual",
                revenue=75_600_000_000,  # 75.6B
                operating_income=11_000_000_000,
                net_income=8_000_000_000,
                total_assets=160_000_000_000,
                total_liabilities=80_000_000_000,
                total_equity=80_000_000_000,
            ),
        ]
        
        # TTM shows only 5% growth (105B vs 100B prior year)
        mock_ttm = FinancialStatement(
            date="TTM",
            period="ttm",
            revenue=105_000_000_000,  # 105B (5% growth vs 100B prior)
            gross_profit=40_000_000_000,
            operating_income=16_000_000_000,
            net_income=11_000_000_000,
            depreciation_amortization=5_000_000_000,
            capital_expenditure=-8_000_000_000,
            total_assets=210_000_000_000,
            total_liabilities=105_000_000_000,
            total_equity=105_000_000_000,
            total_debt=50_000_000_000,
            cash_and_equivalents=20_000_000_000,
            current_assets=60_000_000_000,
            current_liabilities=40_000_000_000,
        )
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        mock_yahoo = MagicMock()
        mock_yahoo.get_ttm_financials = AsyncMock(return_value=mock_ttm)
        mock_yahoo.get_dividends = AsyncMock(return_value=[])
        
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.YahooProvider", return_value=mock_yahoo):
            response = client.get("/api/stock/TEST/analyze?provider=yahoo")
        
        assert response.status_code == 200
        data = response.json()
        stock = data["stock"]
        
        annual_growth = stock["hints_annual"]["revenue_growth"]
        ttm_growth = stock["hints_ttm"]["revenue_growth"]
        
        # Annual CAGR should be ~15% (100/75.6)^(1/2) - 1
        assert annual_growth is not None
        assert 0.10 < annual_growth < 0.20, f"Annual CAGR should be ~15%, got {annual_growth:.1%}"
        
        # TTM growth should be ~5% (105/100 - 1)
        assert ttm_growth is not None
        assert 0.03 < ttm_growth < 0.07, f"TTM growth should be ~5%, got {ttm_growth:.1%}"
        
        # Key assertion: they should NOT be the same
        assert abs(ttm_growth - annual_growth) > 0.05, (
            f"TTM growth ({ttm_growth:.1%}) should differ from annual CAGR ({annual_growth:.1%}). "
            "Bug: TTM hints are copying annual hints instead of calculating true TTM growth."
        )
    
    def test_ttm_revenue_growth_uses_prior_year_revenue(self):
        """
        TTM revenue growth = (TTM_revenue / prior_year_revenue) - 1
        
        Not CAGR, not average, just simple YoY comparison.
        """
        mock_stock_data = create_mock_stock_data()
        
        # Set up clear numbers for easy verification
        # Prior year: 100B, TTM: 120B -> 20% growth
        mock_stock_data.financials = [
            FinancialStatement(
                date="2024-01-01", period="annual",
                revenue=100_000_000_000,  # 100B
                operating_income=15_000_000_000,
                net_income=10_000_000_000,
                total_assets=200_000_000_000,
                total_liabilities=100_000_000_000,
                total_equity=100_000_000_000,
            ),
        ]
        
        mock_ttm = FinancialStatement(
            date="TTM",
            period="ttm",
            revenue=120_000_000_000,  # 120B (20% growth)
            gross_profit=48_000_000_000,
            operating_income=18_000_000_000,
            net_income=12_000_000_000,
            depreciation_amortization=5_000_000_000,
            capital_expenditure=-10_000_000_000,
            total_assets=240_000_000_000,
            total_liabilities=120_000_000_000,
            total_equity=120_000_000_000,
            total_debt=60_000_000_000,
            cash_and_equivalents=30_000_000_000,
            current_assets=72_000_000_000,
            current_liabilities=48_000_000_000,
        )
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        mock_yahoo = MagicMock()
        mock_yahoo.get_ttm_financials = AsyncMock(return_value=mock_ttm)
        mock_yahoo.get_dividends = AsyncMock(return_value=[])
        
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.YahooProvider", return_value=mock_yahoo):
            response = client.get("/api/stock/TEST/analyze?provider=yahoo")
        
        assert response.status_code == 200
        data = response.json()
        stock = data["stock"]
        
        ttm_growth = stock["hints_ttm"]["revenue_growth"]
        
        # Should be exactly 20% = (120 - 100) / 100
        assert ttm_growth is not None
        expected = 0.20
        assert abs(ttm_growth - expected) < 0.01, (
            f"TTM growth should be {expected:.0%} (120B/100B - 1), got {ttm_growth:.1%}"
        )


class TestTTMWorkingCapitalFormula:
    """
    P0 Fix: TTM working capital must use OPERATING WC formula,
    not gross WC that includes cash and short-term debt.
    
    Bug: TTM WC = current_assets - current_liabilities (WRONG - includes cash/debt)
    Fix: TTM WC = (current_assets - cash) - (current_liabilities - short_term_debt)
    
    This is critical because:
    - Cash-rich companies (AAPL: $50B cash) show ~5x inflated WC needs
    - WC ratio drives FCF projections
    - Can cause 10-15% valuation error
    """
    
    def test_ttm_wc_excludes_cash_and_debt(self):
        """
        TTM WC should use OPERATING working capital formula:
        WC = (Current Assets - Cash) - (Current Liabilities - Short-term Debt)
        
        Example:
        - Current Assets: 150B (including 50B cash)
        - Current Liabilities: 100B (including 10B short-term debt)
        - Gross WC: 150 - 100 = 50B (WRONG)
        - Operating WC: (150-50) - (100-10) = 100 - 90 = 10B (CORRECT)
        """
        mock_stock_data = create_mock_stock_data()
        
        # Set up financials with known values
        mock_stock_data.financials = [
            FinancialStatement(
                date="2024-01-01", period="annual",
                revenue=400_000_000_000,  # 400B
                operating_income=60_000_000_000,
                net_income=40_000_000_000,
                total_assets=500_000_000_000,
                total_liabilities=250_000_000_000,
                total_equity=250_000_000_000,
                current_assets=150_000_000_000,  # 150B
                current_liabilities=100_000_000_000,  # 100B
                cash_and_equivalents=50_000_000_000,  # 50B cash
                total_debt=60_000_000_000,
            ),
        ]
        
        # TTM with same structure - 50B cash, 10B short-term debt
        mock_ttm = FinancialStatement(
            date="TTM",
            period="ttm",
            revenue=420_000_000_000,  # 420B
            gross_profit=180_000_000_000,
            operating_income=63_000_000_000,
            net_income=42_000_000_000,
            depreciation_amortization=15_000_000_000,
            capital_expenditure=-20_000_000_000,
            total_assets=520_000_000_000,
            total_liabilities=260_000_000_000,
            total_equity=260_000_000_000,
            current_assets=150_000_000_000,  # 150B (includes 50B cash)
            current_liabilities=100_000_000_000,  # 100B (includes 10B short-term debt)
            cash_and_equivalents=50_000_000_000,  # 50B cash
            total_debt=60_000_000_000,
            short_term_debt=10_000_000_000,  # 10B short-term debt
        )
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        mock_yahoo = MagicMock()
        mock_yahoo.get_ttm_financials = AsyncMock(return_value=mock_ttm)
        mock_yahoo.get_dividends = AsyncMock(return_value=[])
        
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.YahooProvider", return_value=mock_yahoo):
            response = client.get("/api/stock/TEST/analyze?provider=yahoo")
        
        assert response.status_code == 200
        data = response.json()
        stock = data["stock"]
        
        ttm_wc_ratio = stock["hints_ttm"]["wc_ratio"]
        
        # Expected OPERATING WC:
        # Non-cash current assets = 150B - 50B = 100B
        # Operating current liabilities = 100B - 10B = 90B
        # Operating WC = 100B - 90B = 10B
        # WC ratio = 10B / 420B = 2.38%
        expected_wc = 10_000_000_000  # 10B
        expected_ratio = expected_wc / 420_000_000_000  # ~2.38%
        
        # If bug exists (gross WC): 50B / 420B = 11.9%
        # Correct (operating WC): 10B / 420B = 2.38%
        
        assert ttm_wc_ratio is not None
        assert abs(ttm_wc_ratio - expected_ratio) < 0.01, (
            f"TTM WC ratio should be ~{expected_ratio:.1%} (operating WC), "
            f"got {ttm_wc_ratio:.1%}. "
            "Bug: TTM is using gross WC (includes cash/debt) instead of operating WC."
        )
    
    def test_ttm_wc_handles_missing_short_term_debt(self):
        """
        If short_term_debt is None, should default to 0 (not fail).
        
        Some providers don't break out short-term debt separately.
        In this case, we can't exclude it, so we do our best.
        """
        mock_stock_data = create_mock_stock_data()
        mock_stock_data.financials = [
            FinancialStatement(
                date="2024-01-01", period="annual",
                revenue=100_000_000_000,
                operating_income=15_000_000_000,
                net_income=10_000_000_000,
                total_assets=200_000_000_000,
                total_liabilities=100_000_000_000,
                total_equity=100_000_000_000,
                current_assets=50_000_000_000,
                current_liabilities=30_000_000_000,
                cash_and_equivalents=10_000_000_000,
            ),
        ]
        
        # TTM with no short_term_debt field
        mock_ttm = FinancialStatement(
            date="TTM",
            period="ttm",
            revenue=110_000_000_000,
            gross_profit=44_000_000_000,
            operating_income=16_500_000_000,
            net_income=11_000_000_000,
            depreciation_amortization=5_000_000_000,
            capital_expenditure=-8_000_000_000,
            total_assets=220_000_000_000,
            total_liabilities=110_000_000_000,
            total_equity=110_000_000_000,
            current_assets=55_000_000_000,
            current_liabilities=33_000_000_000,
            cash_and_equivalents=12_000_000_000,
            total_debt=40_000_000_000,
            short_term_debt=None,  # Not available from provider
        )
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        mock_yahoo = MagicMock()
        mock_yahoo.get_ttm_financials = AsyncMock(return_value=mock_ttm)
        mock_yahoo.get_dividends = AsyncMock(return_value=[])
        
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.YahooProvider", return_value=mock_yahoo):
            response = client.get("/api/stock/TEST/analyze?provider=yahoo")
        
        assert response.status_code == 200
        data = response.json()
        stock = data["stock"]
        
        ttm_wc_ratio = stock["hints_ttm"]["wc_ratio"]
        
        # With missing short_term_debt (treated as 0):
        # Non-cash CA = 55B - 12B = 43B
        # Operating CL = 33B - 0 = 33B
        # Operating WC = 43B - 33B = 10B
        # Ratio = 10B / 110B = 9.1%
        expected_wc = 10_000_000_000
        expected_ratio = expected_wc / 110_000_000_000
        
        assert ttm_wc_ratio is not None
        assert abs(ttm_wc_ratio - expected_ratio) < 0.02, (
            f"TTM WC ratio should be ~{expected_ratio:.1%}, got {ttm_wc_ratio:.1%}"
        )
    
    def test_ttm_wc_ratio_returns_zero_not_none_when_wc_is_zero(self):
        """
        When operating WC is exactly zero, wc_ratio should be 0.0, not None.
        
        Bug: The condition `if ttm_wc` treats 0 as falsy, skipping the calculation.
        Fix: Use `if ttm_wc is not None` instead.
        
        This is a valid scenario:
        - Current Assets (excl cash) = 100B
        - Current Liabilities (excl STD) = 100B
        - Operating WC = 0 (balanced)
        - WC ratio = 0.0 (not None!)
        """
        mock_stock_data = create_mock_stock_data()
        mock_stock_data.financials = [
            FinancialStatement(
                date="2024-01-01", period="annual",
                revenue=100_000_000_000,
                operating_income=15_000_000_000,
                net_income=10_000_000_000,
                total_assets=200_000_000_000,
                total_liabilities=100_000_000_000,
                total_equity=100_000_000_000,
            ),
        ]
        
        # TTM where operating WC is exactly zero
        # Non-cash CA = 100B - 20B = 80B
        # Operating CL = 90B - 10B = 80B
        # Operating WC = 80B - 80B = 0
        mock_ttm = FinancialStatement(
            date="TTM",
            period="ttm",
            revenue=110_000_000_000,
            gross_profit=44_000_000_000,
            operating_income=16_500_000_000,
            net_income=11_000_000_000,
            depreciation_amortization=5_000_000_000,
            capital_expenditure=-8_000_000_000,
            total_assets=220_000_000_000,
            total_liabilities=110_000_000_000,
            total_equity=110_000_000_000,
            current_assets=100_000_000_000,  # 100B
            current_liabilities=90_000_000_000,  # 90B
            cash_and_equivalents=20_000_000_000,  # 20B cash
            total_debt=40_000_000_000,
            short_term_debt=10_000_000_000,  # 10B STD
        )
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        mock_yahoo = MagicMock()
        mock_yahoo.get_ttm_financials = AsyncMock(return_value=mock_ttm)
        mock_yahoo.get_dividends = AsyncMock(return_value=[])
        
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.YahooProvider", return_value=mock_yahoo):
            response = client.get("/api/stock/TEST/analyze?provider=yahoo")
        
        assert response.status_code == 200
        data = response.json()
        stock = data["stock"]
        
        ttm_wc_ratio = stock["hints_ttm"]["wc_ratio"]
        
        # WC = (100B - 20B) - (90B - 10B) = 80B - 80B = 0
        # Ratio should be 0.0, NOT None
        assert ttm_wc_ratio is not None, (
            "WC ratio should be 0.0 when WC is zero, not None. "
            "Bug: `if ttm_wc` treats 0 as falsy."
        )
        assert ttm_wc_ratio == 0.0, f"WC ratio should be exactly 0.0, got {ttm_wc_ratio}"


class TestTTMRatiosCashFlow:
    """
    P0 Fix: TTM ratios must include cash_flow data for accurate calculations.
    
    Bug: ttm_data passed to RatioCalculator only has income_statement + balance_sheet,
    missing cash_flow. This causes:
    - D&A defaults to 0 → EBITDA understated (EBITDA = EBIT + 0)
    - FCF/SBC fields missing → SBC-adjusted metrics are null/wrong
    
    Fix: Add cash_flow section to ttm_data with D&A, CapEx, OCF, FCF, SBC.
    """
    
    def test_ttm_sbc_metrics_not_null_when_sbc_available(self):
        """
        When TTM financials include stock_based_compensation,
        the SBC metrics should be calculated, not null.
        
        Bug: ttm_data doesn't include cash_flow → sbc fields are null
        """
        mock_stock_data = create_mock_stock_data()
        mock_stock_data.financials = [
            FinancialStatement(
                date="2024-01-01", period="annual",
                revenue=100_000_000_000,
                operating_income=15_000_000_000,
                net_income=10_000_000_000,
                total_assets=200_000_000_000,
                total_liabilities=100_000_000_000,
                total_equity=100_000_000_000,
                operating_cash_flow=20_000_000_000,
                free_cash_flow=15_000_000_000,
                stock_based_compensation=2_000_000_000,  # 2B SBC
            ),
        ]
        
        # TTM with SBC data
        mock_ttm = FinancialStatement(
            date="TTM",
            period="ttm",
            revenue=110_000_000_000,  # 110B
            gross_profit=44_000_000_000,
            operating_income=16_500_000_000,
            net_income=11_000_000_000,
            depreciation_amortization=5_000_000_000,
            capital_expenditure=-8_000_000_000,
            operating_cash_flow=22_000_000_000,  # 22B OCF
            free_cash_flow=16_000_000_000,  # 16B FCF
            stock_based_compensation=2_500_000_000,  # 2.5B SBC (high!)
            total_assets=220_000_000_000,
            total_liabilities=110_000_000_000,
            total_equity=110_000_000_000,
            current_assets=55_000_000_000,
            current_liabilities=33_000_000_000,
            cash_and_equivalents=12_000_000_000,
            total_debt=40_000_000_000,
        )
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        mock_yahoo = MagicMock()
        mock_yahoo.get_ttm_financials = AsyncMock(return_value=mock_ttm)
        mock_yahoo.get_dividends = AsyncMock(return_value=[])
        
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.YahooProvider", return_value=mock_yahoo):
            response = client.get("/api/stock/TEST/analyze?provider=yahoo")
        
        assert response.status_code == 200
        data = response.json()
        ratios = data["ratios"]["ttm"]
        
        # SBC metrics should be calculated, not null
        assert ratios["sbc"]["sbc_percent_revenue"] is not None, (
            "SBC % revenue should be calculated when SBC data is available. "
            "Bug: ttm_data is missing cash_flow section."
        )
        
        # SBC / Revenue = 2.5B / 110B = 2.27%
        expected_sbc_pct = 2_500_000_000 / 110_000_000_000
        assert abs(ratios["sbc"]["sbc_percent_revenue"] - expected_sbc_pct) < 0.01, (
            f"SBC % revenue should be ~{expected_sbc_pct:.1%}, "
            f"got {ratios['sbc']['sbc_percent_revenue']:.1%}"
        )
    
    def test_ttm_fcf_adjusted_calculated_when_fcf_and_sbc_available(self):
        """
        FCF adjusted = FCF - SBC
        
        When both FCF and SBC are in TTM financials, fcf_adjusted should
        be calculated, not null.
        """
        mock_stock_data = create_mock_stock_data()
        mock_stock_data.financials = [
            FinancialStatement(
                date="2024-01-01", period="annual",
                revenue=100_000_000_000,
                operating_income=15_000_000_000,
                net_income=10_000_000_000,
                total_assets=200_000_000_000,
                total_liabilities=100_000_000_000,
                total_equity=100_000_000_000,
            ),
        ]
        
        mock_ttm = FinancialStatement(
            date="TTM",
            period="ttm",
            revenue=110_000_000_000,
            gross_profit=44_000_000_000,
            operating_income=16_500_000_000,
            net_income=11_000_000_000,
            depreciation_amortization=5_000_000_000,
            capital_expenditure=-8_000_000_000,
            operating_cash_flow=22_000_000_000,
            free_cash_flow=16_000_000_000,  # 16B FCF
            stock_based_compensation=3_000_000_000,  # 3B SBC
            total_assets=220_000_000_000,
            total_liabilities=110_000_000_000,
            total_equity=110_000_000_000,
            current_assets=55_000_000_000,
            current_liabilities=33_000_000_000,
            cash_and_equivalents=12_000_000_000,
            total_debt=40_000_000_000,
        )
        
        mock_client = MagicMock()
        mock_client.get_stock_data = AsyncMock(return_value=mock_stock_data)
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        mock_yahoo = MagicMock()
        mock_yahoo.get_ttm_financials = AsyncMock(return_value=mock_ttm)
        mock_yahoo.get_dividends = AsyncMock(return_value=[])
        
        with patch("app.routers.stock.get_client_for_provider", return_value=mock_client), \
             patch("app.routers.stock.YahooProvider", return_value=mock_yahoo):
            response = client.get("/api/stock/TEST/analyze?provider=yahoo")
        
        assert response.status_code == 200
        data = response.json()
        ratios = data["ratios"]["ttm"]
        
        # FCF adjusted = FCF - SBC = 16B - 3B = 13B
        expected_fcf_adjusted = 16_000_000_000 - 3_000_000_000
        
        assert ratios["sbc"]["fcf_adjusted"] is not None, (
            "FCF adjusted should be calculated when FCF and SBC are available. "
            "Bug: ttm_data is missing cash_flow section."
        )
        assert abs(ratios["sbc"]["fcf_adjusted"] - expected_fcf_adjusted) < 1_000_000, (
            f"FCF adjusted should be ~{expected_fcf_adjusted/1e9:.1f}B, "
            f"got {ratios['sbc']['fcf_adjusted']/1e9:.1f}B"
        )
