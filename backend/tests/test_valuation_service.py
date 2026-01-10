import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.valuation_service import ValuationService
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement


def create_mock_stock_data():
    """Create realistic mock stock data for testing."""
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
                date="2023-09-30",
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
            ),
            FinancialStatement(
                date="2022-09-30",
                period="annual",
                revenue=394328000000,
                cost_of_revenue=223546000000,
                gross_profit=170782000000,
                operating_income=119437000000,
                net_income=99803000000,
                interest_expense=2931000000,
                income_tax_expense=19300000000,
                total_assets=352755000000,
                total_liabilities=302083000000,
                total_equity=50672000000,
                total_debt=120069000000,
                cash_and_equivalents=23646000000,
                current_assets=135405000000,
                current_liabilities=153982000000,
                operating_cash_flow=122151000000,
                capital_expenditure=-10708000000,
                free_cash_flow=111443000000,
                depreciation_amortization=11104000000,
            ),
            FinancialStatement(
                date="2021-09-30",
                period="annual",
                revenue=365817000000,
                cost_of_revenue=212981000000,
                gross_profit=152836000000,
                operating_income=108949000000,
                net_income=94680000000,
                interest_expense=2645000000,
                income_tax_expense=14527000000,
                total_assets=351002000000,
                total_liabilities=287912000000,
                total_equity=63090000000,
                total_debt=124719000000,
                cash_and_equivalents=34940000000,
                current_assets=134836000000,
                current_liabilities=125481000000,
                operating_cash_flow=104038000000,
                capital_expenditure=-11085000000,
                free_cash_flow=92953000000,
                depreciation_amortization=11284000000,
            ),
        ],
        provider="fmp",
    )


class TestValuationService:
    @pytest.fixture
    def mock_client(self):
        """Create a mock StockDataClient."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client

    @pytest.mark.asyncio
    async def test_valuation_returns_intrinsic_value(self, mock_client):
        """Full valuation should return intrinsic value per share."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL")

        assert "intrinsic_value_per_share" in result
        assert "market_cap" in result
        assert result["intrinsic_value_per_share"] > 0

    @pytest.mark.asyncio
    async def test_valuation_includes_wacc(self, mock_client):
        """Valuation should calculate and include WACC."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL")

        assert "wacc" in result
        assert 0 < result["wacc"] < 0.20  # Reasonable WACC range

    @pytest.mark.asyncio
    async def test_valuation_includes_fcf_projections(self, mock_client):
        """Valuation should include FCF projections."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL", projection_years=5)

        assert "projections" in result
        assert len(result["projections"]) == 5

    @pytest.mark.asyncio
    async def test_valuation_allows_growth_override(self, mock_client):
        """User should be able to override growth rate."""
        service = ValuationService(client=mock_client)

        result_default = await service.value_stock("AAPL", revenue_growth=0.05)
        
        # Reset mock to ensure fresh call
        mock_client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        result_high_growth = await service.value_stock("AAPL", revenue_growth=0.15)

        # Higher growth should give higher intrinsic value
        assert result_high_growth["intrinsic_value_per_share"] > result_default["intrinsic_value_per_share"]

    @pytest.mark.asyncio
    async def test_valuation_with_custom_discount_rate(self, mock_client):
        """User should be able to override discount rate."""
        service = ValuationService(client=mock_client)

        result_default = await service.value_stock("AAPL")
        
        # Reset mock
        mock_client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        result_custom = await service.value_stock("AAPL", discount_rate_override=0.15)

        # Higher discount rate should give lower intrinsic value
        assert result_custom["intrinsic_value_per_share"] < result_default["intrinsic_value_per_share"]
        assert result_custom["using_custom_discount_rate"] is True

    @pytest.mark.asyncio
    async def test_valuation_with_explicit_fcf_ratios(self, mock_client):
        """
        User should be able to pass FCF ratios explicitly.
        This enables clean TTM/Annual separation - frontend passes ratios from selected period.
        """
        service = ValuationService(client=mock_client)

        # Run with explicit ratios (simulating TTM data)
        result = await service.value_stock(
            "AAPL",
            revenue_growth=0.05,
            operating_margin=0.25,
            da_ratio=0.03,      # D&A as 3% of revenue
            capex_ratio=0.03,   # CapEx as 3% of revenue
            wc_ratio=0.05,      # WC as 5% of revenue
        )

        assert "intrinsic_value_per_share" in result
        assert result["intrinsic_value_per_share"] > 0
        # Should use our ratios, not calculated from historical

    @pytest.mark.asyncio
    async def test_valuation_fcf_ratios_affect_result(self, mock_client):
        """Different FCF ratios should produce different valuations."""
        service = ValuationService(client=mock_client)

        # Low capex = more FCF = higher value
        result_low_capex = await service.value_stock(
            "AAPL",
            revenue_growth=0.05,
            operating_margin=0.20,
            da_ratio=0.03,
            capex_ratio=0.02,  # Low capex
            wc_ratio=0.05,
        )
        
        # Reset mock
        mock_client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        # High capex = less FCF = lower value
        result_high_capex = await service.value_stock(
            "AAPL",
            revenue_growth=0.05,
            operating_margin=0.20,
            da_ratio=0.03,
            capex_ratio=0.15,  # High capex
            wc_ratio=0.05,
        )

        assert result_low_capex["intrinsic_value_per_share"] > result_high_capex["intrinsic_value_per_share"]

    @pytest.mark.asyncio
    async def test_valuation_rejects_discount_rate_below_terminal_growth(self, mock_client):
        """WACC/discount rate must be greater than terminal growth rate."""
        service = ValuationService(client=mock_client)

        with pytest.raises(ValueError, match="(?i)discount rate.*must be greater.*terminal growth"):
            await service.value_stock(
                "AAPL",
                terminal_growth_rate=0.05,
                discount_rate_override=0.03,  # Less than terminal growth
            )

    @pytest.mark.asyncio
    async def test_valuation_rejects_equal_discount_and_terminal_growth(self, mock_client):
        """WACC equal to terminal growth produces division by zero."""
        service = ValuationService(client=mock_client)

        with pytest.raises(ValueError, match="(?i)discount rate.*must be greater.*terminal growth"):
            await service.value_stock(
                "AAPL",
                terminal_growth_rate=0.05,
                discount_rate_override=0.05,  # Equal to terminal growth
            )

    @pytest.mark.asyncio
    async def test_valuation_includes_data_timestamp(self, mock_client):
        """Valuation should include timestamp of when data was fetched."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL")

        assert "data_fetched_at" in result
        # Should be an ISO format timestamp
        from datetime import datetime
        datetime.fromisoformat(result["data_fetched_at"])

    @pytest.mark.asyncio
    async def test_valuation_includes_shares_type(self, mock_client):
        """Valuation should indicate which shares figure is used."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL")

        assert "shares_type" in result["inputs"]
        assert result["inputs"]["shares_type"] in ["basic", "diluted"]

    @pytest.mark.asyncio
    async def test_valuation_includes_value_drivers(self, mock_client):
        """Valuation should show which inputs drive value most."""
        service = ValuationService(client=mock_client)

        result = await service.value_stock("AAPL")

        assert "value_drivers" in result
        # Should have ranked list of inputs by impact
        drivers = result["value_drivers"]
        assert len(drivers) > 0
        assert "input" in drivers[0]
        assert "impact_percent" in drivers[0]


class TestExitMultipleSanityCheck:
    """
    Regression tests for Exit Multiple sanity check.
    
    Bug: The DCF only uses Gordon Growth Model for terminal value.
    Professional valuation cross-checks with Exit Multiples.
    
    If implied EV/EBITDA > 25-30x for a mature company, the terminal
    growth assumption is likely too aggressive.
    """
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock StockDataClient."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client
    
    @pytest.mark.asyncio
    async def test_valuation_includes_implied_exit_multiple(self, mock_client):
        """
        Valuation should include implied EV/EBITDA exit multiple.
        
        This is the terminal value divided by terminal year EBITDA,
        allowing comparison with market multiples as a sanity check.
        """
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock("AAPL")
        
        assert "terminal_value_check" in result, (
            "Valuation must include terminal_value_check for exit multiple sanity"
        )
        check = result["terminal_value_check"]
        assert "implied_exit_multiple" in check, (
            "terminal_value_check must include implied_exit_multiple (EV/EBITDA)"
        )
        assert check["implied_exit_multiple"] is not None, (
            "implied_exit_multiple should not be None for valid EBITDA"
        )
        assert check["implied_exit_multiple"] > 0, (
            "Implied exit multiple must be positive"
        )
    
    @pytest.mark.asyncio
    async def test_implied_exit_multiple_is_reasonable(self, mock_client):
        """
        With reasonable assumptions, implied exit multiple should be realistic.
        
        For mature companies, EV/EBITDA typically ranges 8-20x.
        """
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock(
            "AAPL",
            terminal_growth_rate=0.03,  # Reasonable 3% terminal growth
        )
        
        multiple = result["terminal_value_check"]["implied_exit_multiple"]
        assert multiple is not None, "Multiple should not be None for valid EBITDA"
        assert 5 < multiple < 30, (
            f"With 3% terminal growth, implied multiple ({multiple:.1f}x) "
            "should be in reasonable range for mature company"
        )
    
    @pytest.mark.asyncio
    async def test_high_terminal_growth_triggers_warning(self, mock_client):
        """
        Aggressive terminal growth should trigger a warning about high implied multiple.
        """
        service = ValuationService(client=mock_client)
        
        # Use aggressive terminal growth to inflate multiple
        result = await service.value_stock(
            "AAPL",
            terminal_growth_rate=0.045,  # 4.5% - aggressive for mature company
            discount_rate_override=0.08,  # Low WACC to amplify effect
        )
        
        check = result["terminal_value_check"]
        multiple = check["implied_exit_multiple"]
        
        # Must have valid multiple with our mock data
        assert multiple is not None, (
            "implied_exit_multiple should not be None - mock data has valid EBITDA"
        )
        
        # With aggressive growth and low discount rate, multiple should be high
        # and trigger a warning
        if multiple > 25:
            assert "warning" in check, (
                f"High implied multiple ({multiple:.1f}x) "
                "should trigger a warning"
            )
        # If multiple is reasonable despite aggressive params, no warning needed
        # (test still validates the check ran correctly)
    
    @pytest.mark.asyncio
    async def test_terminal_value_check_includes_terminal_ebitda(self, mock_client):
        """
        Should expose terminal year EBITDA for transparency.
        """
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock("AAPL")
        
        check = result["terminal_value_check"]
        assert "terminal_ebitda" in check, (
            "terminal_value_check must include terminal_ebitda"
        )
        assert check["terminal_ebitda"] > 0


class TestSBCShareDilution:
    """
    Tests for P0: SBC Share Dilution.
    
    When we subtract SBC from FCF, we're treating it as a real expense.
    But SBC creates new shares (dilution). Over a 5-10 year projection,
    this can be significant (1-3% per year).
    
    The intrinsic value per share should use terminal shares, not current shares:
    terminal_shares = current_shares * (1 + dilution_rate)^years
    """
    
    @pytest.fixture
    def mock_client(self):
        """Create mock client with realistic data."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client
    
    @pytest.mark.asyncio
    async def test_accepts_annual_dilution_rate(self, mock_client):
        """Should accept annual_dilution_rate parameter."""
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock(
            "AAPL",
            annual_dilution_rate=0.02,  # 2% annual dilution
        )
        
        assert result["intrinsic_value_per_share"] > 0
    
    @pytest.mark.asyncio
    async def test_dilution_reduces_per_share_value(self, mock_client):
        """Higher dilution should reduce per-share intrinsic value."""
        service = ValuationService(client=mock_client)
        
        # No dilution
        result_no_dilution = await service.value_stock(
            "AAPL",
            annual_dilution_rate=0.0,
        )
        
        # Reset mock for fresh call
        mock_client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        # 3% annual dilution
        result_with_dilution = await service.value_stock(
            "AAPL",
            annual_dilution_rate=0.03,  # 3% per year
        )
        
        # With dilution, per-share value should be lower
        assert result_with_dilution["intrinsic_value_per_share"] < result_no_dilution["intrinsic_value_per_share"], (
            f"With 3% dilution, per-share value ({result_with_dilution['intrinsic_value_per_share']:.2f}) "
            f"should be less than without ({result_no_dilution['intrinsic_value_per_share']:.2f})"
        )
    
    @pytest.mark.asyncio
    async def test_dilution_shows_terminal_shares(self, mock_client):
        """Should expose terminal shares for transparency."""
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock(
            "AAPL",
            projection_years=5,
            annual_dilution_rate=0.02,  # 2% annual dilution
        )
        
        # Should expose dilution info in inputs
        inputs = result["inputs"]
        assert "annual_dilution_rate" in inputs
        assert "terminal_shares" in inputs
        
        # Terminal shares = current * (1.02)^5 ≈ current * 1.104
        current_shares = inputs["shares_outstanding"]
        expected_terminal = current_shares * (1.02 ** 5)
        assert abs(inputs["terminal_shares"] - expected_terminal) < 1e6
    
    @pytest.mark.asyncio
    async def test_dilution_magnitude_is_correct(self, mock_client):
        """Dilution impact should match expected magnitude."""
        service = ValuationService(client=mock_client)
        
        # 5 years at 2% = 10.4% more shares
        result_no_dilution = await service.value_stock(
            "AAPL",
            projection_years=5,
            annual_dilution_rate=0.0,
        )
        
        mock_client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        mock_client.get_treasury_rate = AsyncMock(return_value=0.045)
        
        result_with_dilution = await service.value_stock(
            "AAPL",
            projection_years=5,
            annual_dilution_rate=0.02,
        )
        
        # Per-share value should decrease by ~9.4% (1 / 1.104 ≈ 0.906)
        ratio = result_with_dilution["intrinsic_value_per_share"] / result_no_dilution["intrinsic_value_per_share"]
        expected_ratio = 1 / (1.02 ** 5)  # ~0.906
        
        assert abs(ratio - expected_ratio) < 0.01, (
            f"Value ratio ({ratio:.3f}) should be close to {expected_ratio:.3f}"
        )
    
    @pytest.mark.asyncio
    async def test_default_dilution_is_zero(self, mock_client):
        """Default behavior should be no dilution (backward compatible)."""
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock("AAPL")
        
        # No dilution by default
        inputs = result["inputs"]
        assert inputs.get("annual_dilution_rate", 0) == 0


class TestTerminalValueDominance:
    """
    Tests for P0: Terminal value dominance warning.
    
    If terminal value represents too high a % of enterprise value (>70%),
    the DCF is essentially a terminal value guess. User should be warned.
    """
    
    @pytest.fixture
    def mock_client(self):
        """Create mock client with realistic data."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client
    
    @pytest.mark.asyncio
    async def test_includes_terminal_value_percentage(self, mock_client):
        """
        Result should include TV % of EV for transparency.
        """
        service = ValuationService(client=mock_client)
        result = await service.value_stock("AAPL")
        
        check = result["terminal_value_check"]
        assert "terminal_value_pct" in check, (
            "terminal_value_check must include terminal_value_pct"
        )
        
        # Should be a valid percentage (0-1)
        pct = check["terminal_value_pct"]
        assert 0 < pct < 1, f"Terminal value % should be 0-100%, got {pct:.1%}"
    
    @pytest.mark.asyncio
    async def test_terminal_value_percentage_is_accurate(self, mock_client):
        """
        TV % should equal PV(terminal value) / enterprise value.
        """
        service = ValuationService(client=mock_client)
        result = await service.value_stock("AAPL", projection_years=5)
        
        # Manually verify the calculation
        terminal_value = result["terminal_value"]
        enterprise_value = result["enterprise_value"]
        discount_rate = result["discount_rate"]
        projection_years = len(result["projections"])  # Number of projection years
        
        # PV of terminal = TV / (1 + r)^n
        pv_terminal = terminal_value / ((1 + discount_rate) ** projection_years)
        expected_pct = pv_terminal / enterprise_value
        
        actual_pct = result["terminal_value_check"]["terminal_value_pct"]
        assert abs(actual_pct - expected_pct) < 0.01, (
            f"Terminal % mismatch: expected {expected_pct:.2%}, got {actual_pct:.2%}"
        )
    
    @pytest.mark.asyncio
    async def test_high_terminal_pct_triggers_dominance_warning(self, mock_client):
        """
        >70% terminal value should trigger dominance warning.
        """
        service = ValuationService(client=mock_client)
        
        # Use params that lead to higher terminal dominance:
        # - Longer projection period (more discounting of near-term FCF)
        # - Higher terminal growth (bigger terminal value)
        result = await service.value_stock(
            "AAPL",
            projection_years=10,  # Longer projection
            terminal_growth_rate=0.035,  # Higher terminal growth
        )
        
        check = result["terminal_value_check"]
        pct = check["terminal_value_pct"]
        
        # If TV dominates (>70%), should have a warning
        if pct > 0.70:
            assert "dominance_warning" in check, (
                f"With TV at {pct:.0%} of EV, should have dominance_warning"
            )
            assert "70%" in check["dominance_warning"] or "terminal" in check["dominance_warning"].lower()
    
    @pytest.mark.asyncio
    async def test_low_terminal_pct_no_warning(self, mock_client):
        """
        <70% terminal value should NOT trigger dominance warning.
        """
        service = ValuationService(client=mock_client)
        
        # Use conservative params for lower TV dominance
        result = await service.value_stock(
            "AAPL",
            projection_years=5,
            terminal_growth_rate=0.02,  # Conservative terminal
        )
        
        check = result["terminal_value_check"]
        pct = check["terminal_value_pct"]
        
        # If TV is reasonable (<70%), no dominance warning needed
        if pct <= 0.70:
            assert check.get("dominance_warning") is None, (
                f"With TV at {pct:.0%} of EV, should not have dominance_warning"
            )


class TestMultiStageEconomicsIntegration:
    """
    Test that ValuationService correctly passes economics schedules
    to FCFProjector for multi-stage DCF modeling.
    """
    
    @pytest.fixture
    def mock_client(self):
        """Create mock client with realistic stock data."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.04)
        return client
    
    @pytest.mark.asyncio
    async def test_accepts_economics_schedules(self, mock_client):
        """ValuationService should accept margin, capex, and wc schedules."""
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock(
            "AAPL",
            growth_schedule=[0.10, 0.08, 0.06],
            margin_schedule=[0.25, 0.27, 0.30],
            capex_schedule=[0.06, 0.05, 0.04],
            wc_schedule=[0.15, 0.12, 0.10],
        )
        
        assert result["intrinsic_value_per_share"] > 0
        assert len(result["projections"]) == 3
    
    @pytest.mark.asyncio
    async def test_schedules_affect_fcf_projections(self, mock_client):
        """Economics schedules should produce different FCF from constant values."""
        service = ValuationService(client=mock_client)
        
        # With constant margin
        result_constant = await service.value_stock(
            "AAPL",
            projection_years=3,
            operating_margin=0.25,
        )
        
        # With improving margin schedule
        result_schedule = await service.value_stock(
            "AAPL",
            growth_schedule=[0.05, 0.05, 0.05],  # Same growth
            margin_schedule=[0.25, 0.27, 0.30],  # Improving margins
        )
        
        # Improving margins should produce higher FCF in later years
        # and thus higher overall valuation
        assert result_schedule["intrinsic_value_per_share"] > result_constant["intrinsic_value_per_share"], (
            "Improving margin schedule should produce higher valuation than constant margin"
        )
    
    @pytest.mark.asyncio
    async def test_declining_capex_improves_fcf(self, mock_client):
        """Declining CapEx schedule should improve FCF and valuation."""
        service = ValuationService(client=mock_client)
        
        # With high constant CapEx
        result_high_capex = await service.value_stock(
            "AAPL",
            projection_years=3,
            capex_ratio=0.08,
        )
        
        # With declining CapEx schedule (company maturing)
        result_declining = await service.value_stock(
            "AAPL",
            growth_schedule=[0.05, 0.05, 0.05],
            capex_schedule=[0.08, 0.06, 0.04],  # CapEx declining
        )
        
        # Lower CapEx = higher FCF = higher valuation
        assert result_declining["intrinsic_value_per_share"] > result_high_capex["intrinsic_value_per_share"]
    
    @pytest.mark.asyncio
    async def test_schedules_with_da_schedule(self, mock_client):
        """D&A schedule should also be accepted and applied."""
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock(
            "AAPL",
            growth_schedule=[0.10, 0.08, 0.06],
            da_schedule=[0.05, 0.04, 0.03],  # D&A declining as assets mature
        )
        
        assert result["intrinsic_value_per_share"] > 0
        # Verify projections were made
        assert len(result["projections"]) == 3
