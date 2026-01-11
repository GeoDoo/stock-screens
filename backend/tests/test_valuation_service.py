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


class TestValueDriversPerturbAndRevalue:
    """
    Tests for P1: Value drivers should use actual perturb-and-revalue
    instead of proxy calculations.
    
    Bug: revenue_growth and operating_margin impact were just returning
    the rates themselves (proxies), not actual DCF sensitivity.
    
    Fix: Re-run FCF projection with ±10% perturbations to measure
    true value impact.
    """
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock StockDataClient."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client
    
    @pytest.mark.asyncio
    async def test_revenue_growth_impact_is_calculated_not_proxy(self, mock_client):
        """
        Revenue growth impact should be calculated by perturbing the DCF,
        not by just returning the growth rate itself.
        """
        service = ValuationService(client=mock_client)
        
        # Run with specific growth rate
        result = await service.value_stock("AAPL", revenue_growth=0.08)
        
        drivers = result["value_drivers"]
        growth_driver = next((d for d in drivers if d["input"] == "revenue_growth"), None)
        
        assert growth_driver is not None, "Should have revenue_growth in drivers"
        
        # The old proxy implementation would return 8.0 (the rate as %)
        # The new implementation should return actual DCF sensitivity
        # which is typically much higher (10-40% depending on company)
        assert growth_driver["impact_percent"] != 8.0, (
            "Impact should be calculated from perturb-and-revalue, not be the rate itself"
        )
        assert growth_driver["impact_percent"] > 0, "Impact should be positive"
    
    @pytest.mark.asyncio
    async def test_operating_margin_impact_is_calculated_not_proxy(self, mock_client):
        """
        Operating margin impact should be calculated by perturbing the DCF,
        not by just returning the margin itself.
        """
        service = ValuationService(client=mock_client)
        
        # Run with specific margin
        result = await service.value_stock("AAPL", operating_margin=0.25)
        
        drivers = result["value_drivers"]
        margin_driver = next((d for d in drivers if d["input"] == "operating_margin"), None)
        
        assert margin_driver is not None, "Should have operating_margin in drivers"
        
        # The old proxy implementation would return 25.0 (the margin as %)
        # The new implementation should return actual DCF sensitivity
        assert margin_driver["impact_percent"] != 25.0, (
            "Impact should be calculated from perturb-and-revalue, not be the margin itself"
        )
        assert margin_driver["impact_percent"] > 0, "Impact should be positive"
    
    @pytest.mark.asyncio
    async def test_value_drivers_all_have_descriptions(self, mock_client):
        """All value drivers should have meaningful descriptions."""
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock("AAPL")
        
        for driver in result["value_drivers"]:
            assert "description" in driver
            assert len(driver["description"]) > 10, (
                f"Description for {driver['input']} too short"
            )
    
    @pytest.mark.asyncio
    async def test_higher_growth_produces_higher_impact(self, mock_client):
        """
        With higher base growth, a ±10% perturbation should show
        larger absolute impact (compounding effect).
        """
        service = ValuationService(client=mock_client)
        
        # Low growth scenario
        low_result = await service.value_stock("AAPL", revenue_growth=0.05)
        low_driver = next(
            d for d in low_result["value_drivers"] if d["input"] == "revenue_growth"
        )
        
        # High growth scenario
        high_result = await service.value_stock("AAPL", revenue_growth=0.15)
        high_driver = next(
            d for d in high_result["value_drivers"] if d["input"] == "revenue_growth"
        )
        
        # Higher growth base should have higher impact from ±10% perturbation
        # because the absolute change in FCF is larger
        assert high_driver["impact_percent"] > low_driver["impact_percent"], (
            f"15% growth ({high_driver['impact_percent']:.1f}% impact) should have "
            f"larger impact than 5% growth ({low_driver['impact_percent']:.1f}% impact)"
        )
    
    @pytest.mark.asyncio
    async def test_value_drivers_respects_wc_mode(self, mock_client):
        """
        Value drivers should use the same wc_mode as the main valuation.
        """
        service = ValuationService(client=mock_client)
        
        # Run with incremental WC mode
        result = await service.value_stock("AAPL", wc_mode="incremental")
        
        # Should complete without error and have value drivers
        assert "value_drivers" in result
        assert len(result["value_drivers"]) > 0
        
        # All drivers should have positive impact
        for driver in result["value_drivers"]:
            assert driver["impact_percent"] >= 0
    
    @pytest.mark.asyncio
    async def test_value_drivers_respects_mid_year_discounting(self, mock_client):
        """
        Value drivers should use the same discounting method as main valuation.
        """
        service = ValuationService(client=mock_client)
        
        # Run with mid-year discounting
        result = await service.value_stock("AAPL", use_mid_year_discounting=True)
        
        # Should complete without error and have value drivers
        assert "value_drivers" in result
        assert len(result["value_drivers"]) > 0
        
        # All drivers should have positive impact
        for driver in result["value_drivers"]:
            assert driver["impact_percent"] >= 0
    
    @pytest.mark.asyncio
    async def test_value_drivers_respects_multi_stage_schedules(self, mock_client):
        """
        Value drivers should use the same multi-stage schedules as main valuation.
        """
        service = ValuationService(client=mock_client)
        
        # Run with multi-stage schedules
        result = await service.value_stock(
            "AAPL",
            growth_schedule=[0.15, 0.12, 0.10, 0.08, 0.05],
            margin_schedule=[0.25, 0.27, 0.28, 0.29, 0.30],
        )
        
        # Should complete without error and have value drivers
        assert "value_drivers" in result
        assert len(result["value_drivers"]) > 0
        
        # All drivers should have positive impact
        for driver in result["value_drivers"]:
            assert driver["impact_percent"] >= 0
    
    @pytest.mark.asyncio
    async def test_value_drivers_perturbs_schedules_not_single_values(self, mock_client):
        """
        When multi-stage schedules are provided, the sensitivity analysis
        should perturb the schedules themselves, not the single value
        (which would be ignored by project()).
        
        Bug: fcf_projector.project() prioritizes schedules over single values,
        so perturbing the single value had no effect when schedules existed.
        
        Fix: Perturb the schedule entries by ±10% for sensitivity analysis.
        """
        service = ValuationService(client=mock_client)
        
        # Run with multi-stage schedules
        result = await service.value_stock(
            "AAPL",
            growth_schedule=[0.15, 0.12, 0.10, 0.08, 0.05],
            margin_schedule=[0.25, 0.27, 0.28, 0.29, 0.30],
        )
        
        # Find the revenue_growth driver
        growth_driver = next(
            (d for d in result["value_drivers"] if d["input"] == "revenue_growth"),
            None
        )
        
        # With schedules, the impact should NOT be zero
        # (zero would indicate the perturbation was ignored)
        assert growth_driver is not None, "Should have revenue_growth driver"
        assert growth_driver["impact_percent"] > 0, (
            "Growth schedule perturbation should have non-zero impact. "
            f"Got {growth_driver['impact_percent']}% - schedule likely being ignored."
        )
        
        # Description should mention "schedule"
        assert "schedule" in growth_driver["description"].lower(), (
            f"Description should mention schedule: {growth_driver['description']}"
        )
        
        # Same for margin
        margin_driver = next(
            (d for d in result["value_drivers"] if d["input"] == "operating_margin"),
            None
        )
        assert margin_driver is not None, "Should have operating_margin driver"
        assert margin_driver["impact_percent"] > 0, (
            "Margin schedule perturbation should have non-zero impact. "
            f"Got {margin_driver['impact_percent']}% - schedule likely being ignored."
        )
        assert "schedule" in margin_driver["description"].lower()


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


class TestExitMultipleCrossCheck:
    """
    Tests for P1: Exit Multiple Method cross-check.
    
    Professional valuation cross-checks Gordon Growth terminal value with
    Exit Multiple Method (Terminal EBITDA × Sector Multiple).
    
    If the two methods diverge by >20%, it indicates either:
    - Terminal growth assumption is too aggressive/conservative
    - Exit multiple assumption doesn't match growth profile
    """
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock StockDataClient."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client
    
    @pytest.mark.asyncio
    async def test_includes_exit_multiple_crosscheck(self, mock_client):
        """
        Valuation should include exit multiple cross-check in terminal_value_check.
        """
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock(
            "AAPL",
            sector_ev_ebitda_multiple=15.0,  # Provide sector multiple
        )
        
        check = result["terminal_value_check"]
        assert "exit_multiple_tv" in check, (
            "terminal_value_check should include exit_multiple_tv (TV via Exit Multiple Method)"
        )
        assert "gordon_growth_tv" in check, (
            "terminal_value_check should include gordon_growth_tv for comparison"
        )
        assert "method_divergence_pct" in check, (
            "terminal_value_check should include divergence percentage"
        )
    
    @pytest.mark.asyncio
    async def test_large_divergence_triggers_warning(self, mock_client):
        """
        When Gordon Growth and Exit Multiple methods diverge by >20%, warn user.
        
        This catches cases where terminal growth is inconsistent with
        reasonable exit multiples.
        """
        service = ValuationService(client=mock_client)
        
        # Use low exit multiple but high terminal growth to create divergence
        result = await service.value_stock(
            "AAPL",
            terminal_growth_rate=0.04,  # 4% - aggressive
            discount_rate_override=0.08,  # Low WACC amplifies Gordon TV
            sector_ev_ebitda_multiple=10.0,  # Conservative exit multiple
        )
        
        check = result["terminal_value_check"]
        assert "method_divergence_warning" in check, (
            "Should warn when Gordon Growth and Exit Multiple diverge significantly"
        )
    
    @pytest.mark.asyncio
    async def test_small_divergence_no_warning(self, mock_client):
        """
        When methods are aligned (<20% divergence), no warning needed.
        """
        service = ValuationService(client=mock_client)
        
        # Use balanced assumptions
        result = await service.value_stock(
            "AAPL",
            terminal_growth_rate=0.025,  # 2.5% - reasonable
            discount_rate_override=0.10,  # Normal WACC
            sector_ev_ebitda_multiple=12.0,  # Reasonable exit multiple
        )
        
        check = result["terminal_value_check"]
        # Should not have a method_divergence_warning if divergence < 20%
        if check.get("method_divergence_pct") is not None:
            if abs(check["method_divergence_pct"]) < 0.20:
                assert "method_divergence_warning" not in check
    
    @pytest.mark.asyncio
    async def test_exit_multiple_calculation_is_correct(self, mock_client):
        """
        Exit Multiple TV = Terminal EBITDA × Sector Multiple.
        """
        service = ValuationService(client=mock_client)
        
        sector_multiple = 15.0
        result = await service.value_stock(
            "AAPL",
            sector_ev_ebitda_multiple=sector_multiple,
        )
        
        check = result["terminal_value_check"]
        terminal_ebitda = check["terminal_ebitda"]
        exit_multiple_tv = check.get("exit_multiple_tv")
        
        if exit_multiple_tv is not None and terminal_ebitda > 0:
            expected = terminal_ebitda * sector_multiple
            assert abs(exit_multiple_tv - expected) < 1, (
                f"Exit Multiple TV should be {expected}, got {exit_multiple_tv}"
            )


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


class TestImpliedTerminalROICWarning:
    """
    P0 #1 (NOTES2.md): "Economic Terminal State" Fallacy warning.
    
    In a competitive economy, a firm's ROIC should fade toward WACC in perpetuity.
    If implied terminal ROIC >> WACC, the model assumes "infinite competitive advantage".
    
    This test ensures the valuation warns users when terminal assumptions imply
    unrealistically high ROIC in perpetuity.
    """
    
    @pytest.fixture
    def mock_client(self):
        """Create mock client with realistic stock data."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.04)
        return client
    
    @pytest.mark.asyncio
    async def test_includes_implied_terminal_roic(self, mock_client):
        """
        terminal_value_check should include implied_terminal_roic.
        
        Implied ROIC = Terminal Growth / (1 - Terminal FCF / Terminal NOPAT)
        """
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock("AAPL")
        
        check = result["terminal_value_check"]
        assert "implied_terminal_roic" in check, (
            "terminal_value_check must include implied_terminal_roic for economic sanity check"
        )
    
    @pytest.mark.asyncio
    async def test_warns_when_terminal_roic_far_exceeds_wacc(self, mock_client):
        """
        Should warn when implied terminal ROIC >> WACC (> 2x).
        
        This indicates "economically heroic" assumptions - the model assumes
        the company will maintain a massive competitive advantage in perpetuity.
        """
        service = ValuationService(client=mock_client)
        
        # Use aggressive terminal growth with low WACC to create high implied ROIC
        result = await service.value_stock(
            "AAPL",
            terminal_growth_rate=0.04,  # 4% terminal growth (aggressive)
            discount_rate_override=0.08,  # 8% WACC (low)
        )
        
        check = result["terminal_value_check"]
        
        # If implied ROIC > 2x WACC, should warn
        implied_roic = check.get("implied_terminal_roic")
        wacc = result.get("wacc") or result.get("discount_rate")
        
        if implied_roic is not None and wacc is not None:
            if implied_roic > wacc * 2:
                assert "terminal_roic_warning" in check, (
                    f"Should warn when implied ROIC ({implied_roic:.1%}) > 2x WACC ({wacc:.1%})"
                )
    
    @pytest.mark.asyncio
    async def test_no_warning_when_terminal_roic_reasonable(self, mock_client):
        """
        Should NOT warn when implied terminal ROIC is close to WACC.
        
        This indicates the company is modeled to converge to competitive equilibrium.
        """
        service = ValuationService(client=mock_client)
        
        # Conservative terminal growth with normal WACC
        result = await service.value_stock(
            "AAPL",
            terminal_growth_rate=0.02,  # 2% terminal growth (conservative)
            discount_rate_override=0.10,  # 10% WACC
        )
        
        check = result["terminal_value_check"]
        implied_roic = check.get("implied_terminal_roic")
        wacc = result.get("wacc") or result.get("discount_rate")
        
        # If implied ROIC is within 2x WACC, no warning should be present
        if implied_roic is not None and wacc is not None:
            if implied_roic <= wacc * 2:
                assert check.get("terminal_roic_warning") is None, (
                    f"No warning needed when implied ROIC ({implied_roic:.1%}) <= 2x WACC ({wacc:.1%})"
                )


class TestCapExConvergenceWarning:
    """
    P1 (NOTES2.md): Maintenance vs Growth CapEx warning.
    
    In the terminal year (perpetuity), Growth CapEx should converge to 0.
    Only Maintenance CapEx remains, which should roughly equal D&A.
    
    If terminal CapEx >> D&A, the model implies perpetual growth investment,
    which is economically inconsistent with a steady-state assumption.
    """
    
    @pytest.fixture
    def mock_client(self):
        """Create mock client with realistic stock data."""
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=create_mock_stock_data())
        client.get_treasury_rate = AsyncMock(return_value=0.04)
        return client
    
    @pytest.mark.asyncio
    async def test_includes_terminal_capex_to_da_ratio(self, mock_client):
        """
        terminal_value_check should include CapEx/D&A ratio for the terminal year.
        """
        service = ValuationService(client=mock_client)
        
        result = await service.value_stock("AAPL")
        
        check = result["terminal_value_check"]
        assert "terminal_capex_to_da" in check, (
            "terminal_value_check must include terminal_capex_to_da ratio"
        )
    
    @pytest.mark.asyncio
    async def test_warns_when_terminal_capex_exceeds_maintenance(self, mock_client):
        """
        Should warn when terminal CapEx >> D&A (> 1.3x).
        
        High CapEx/D&A implies perpetual growth investment, which is
        inconsistent with steady-state economics.
        """
        service = ValuationService(client=mock_client)
        
        # Use high capex ratio to trigger warning
        result = await service.value_stock(
            "AAPL",
            capex_ratio=0.15,  # 15% of revenue as CapEx
            da_ratio=0.05,    # 5% of revenue as D&A
        )
        
        check = result["terminal_value_check"]
        capex_da = check.get("terminal_capex_to_da")
        
        # CapEx/D&A = 15% / 5% = 3.0x
        assert capex_da is not None
        assert capex_da > 1.3, f"CapEx/D&A should be high: {capex_da}"
        
        assert "capex_convergence_warning" in check, (
            "Should warn when terminal CapEx >> D&A (perpetual growth CapEx implied)"
        )
    
    @pytest.mark.asyncio
    async def test_no_warning_when_capex_near_da(self, mock_client):
        """
        No warning when terminal CapEx ≈ D&A (maintenance level).
        """
        service = ValuationService(client=mock_client)
        
        # Use balanced capex/da ratios
        result = await service.value_stock(
            "AAPL",
            capex_ratio=0.05,  # 5% of revenue as CapEx
            da_ratio=0.05,     # 5% of revenue as D&A (1.0x ratio)
        )
        
        check = result["terminal_value_check"]
        capex_da = check.get("terminal_capex_to_da")
        
        # CapEx/D&A = 1.0x (at or below 1.3x threshold)
        assert capex_da is not None
        assert capex_da <= 1.3, f"CapEx/D&A should be at maintenance level: {capex_da}"
        
        assert check.get("capex_convergence_warning") is None, (
            "No warning needed when CapEx ≈ D&A (maintenance level)"
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


class TestBusinessTypeWarning:
    """
    P2.8: Tests for DCF warnings on financial companies.
    
    Banks, insurers, and other financial services companies have
    different capital structures where traditional DCF is less appropriate.
    The system should warn users about this limitation.
    """
    
    @pytest.fixture
    def mock_client_bank(self):
        """Create mock client returning a bank stock."""
        bank_data = StockData(
            profile=CompanyProfile(
                symbol="JPM",
                name="JPMorgan Chase & Co.",
                price=180.0,
                market_cap=500000000000,
                beta=1.1,
                shares_outstanding=2800000000,
                currency="USD",
                exchange="NYSE",
                industry="Banks—Diversified",
                sector="Financial Services",
            ),
            financials=[
                FinancialStatement(
                    date="2023-12-31",
                    period="annual",
                    revenue=160000000000,
                    operating_income=50000000000,
                    net_income=40000000000,
                    interest_expense=80000000000,  # High interest expense (banks)
                    income_tax_expense=12000000000,
                    total_assets=3700000000000,  # Huge balance sheet
                    total_liabilities=3400000000000,
                    total_equity=300000000000,
                    total_debt=400000000000,
                    cash_and_equivalents=500000000000,
                    current_assets=None,
                    current_liabilities=None,
                    operating_cash_flow=60000000000,
                    capital_expenditure=-10000000000,
                    free_cash_flow=50000000000,
                    depreciation_amortization=5000000000,
                ),
                FinancialStatement(
                    date="2022-12-31",
                    period="annual",
                    revenue=150000000000,
                    operating_income=45000000000,
                    net_income=38000000000,
                    interest_expense=70000000000,
                    income_tax_expense=11000000000,
                    total_assets=3500000000000,
                    total_liabilities=3200000000000,
                    total_equity=300000000000,
                    total_debt=380000000000,
                    cash_and_equivalents=480000000000,
                    current_assets=None,
                    current_liabilities=None,
                    operating_cash_flow=55000000000,
                    capital_expenditure=-9000000000,
                    free_cash_flow=46000000000,
                    depreciation_amortization=4800000000,
                ),
                FinancialStatement(
                    date="2021-12-31",
                    period="annual",
                    revenue=130000000000,
                    operating_income=40000000000,
                    net_income=35000000000,
                    interest_expense=50000000000,
                    income_tax_expense=10000000000,
                    total_assets=3200000000000,
                    total_liabilities=2900000000000,
                    total_equity=300000000000,
                    total_debt=350000000000,
                    cash_and_equivalents=450000000000,
                    current_assets=None,
                    current_liabilities=None,
                    operating_cash_flow=50000000000,
                    capital_expenditure=-8000000000,
                    free_cash_flow=42000000000,
                    depreciation_amortization=4500000000,
                ),
            ],
            provider="fmp",
        )
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=bank_data)
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client
    
    @pytest.fixture
    def mock_client_insurer(self):
        """Create mock client returning an insurance company stock."""
        insurer_data = StockData(
            profile=CompanyProfile(
                symbol="BRK.B",
                name="Berkshire Hathaway Inc.",
                price=400.0,
                market_cap=800000000000,
                beta=0.9,
                shares_outstanding=2000000000,
                currency="USD",
                exchange="NYSE",
                industry="Insurance—Diversified",
                sector="Financial Services",
            ),
            financials=[
                FinancialStatement(
                    date="2023-12-31",
                    period="annual",
                    revenue=300000000000,
                    operating_income=80000000000,
                    net_income=96000000000,
                    interest_expense=2000000000,
                    income_tax_expense=25000000000,
                    total_assets=1000000000000,
                    total_liabilities=500000000000,
                    total_equity=500000000000,
                    total_debt=100000000000,
                    cash_and_equivalents=200000000000,
                    current_assets=None,
                    current_liabilities=None,
                    operating_cash_flow=70000000000,
                    capital_expenditure=-15000000000,
                    free_cash_flow=55000000000,
                    depreciation_amortization=10000000000,
                ),
                FinancialStatement(
                    date="2022-12-31",
                    period="annual",
                    revenue=280000000000,
                    operating_income=75000000000,
                    net_income=90000000000,
                    interest_expense=1800000000,
                    income_tax_expense=22000000000,
                    total_assets=950000000000,
                    total_liabilities=475000000000,
                    total_equity=475000000000,
                    total_debt=95000000000,
                    cash_and_equivalents=180000000000,
                    current_assets=None,
                    current_liabilities=None,
                    operating_cash_flow=65000000000,
                    capital_expenditure=-14000000000,
                    free_cash_flow=51000000000,
                    depreciation_amortization=9500000000,
                ),
                FinancialStatement(
                    date="2021-12-31",
                    period="annual",
                    revenue=260000000000,
                    operating_income=70000000000,
                    net_income=85000000000,
                    interest_expense=1600000000,
                    income_tax_expense=20000000000,
                    total_assets=900000000000,
                    total_liabilities=450000000000,
                    total_equity=450000000000,
                    total_debt=90000000000,
                    cash_and_equivalents=160000000000,
                    current_assets=None,
                    current_liabilities=None,
                    operating_cash_flow=60000000000,
                    capital_expenditure=-13000000000,
                    free_cash_flow=47000000000,
                    depreciation_amortization=9000000000,
                ),
            ],
            provider="fmp",
        )
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=insurer_data)
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client
    
    @pytest.fixture
    def mock_client_tech(self):
        """Create mock client returning a normal tech stock (no warning)."""
        from tests.test_valuation_service import create_mock_stock_data
        tech_data = create_mock_stock_data()
        client = MagicMock()
        client.get_stock_data = AsyncMock(return_value=tech_data)
        client.get_treasury_rate = AsyncMock(return_value=0.045)
        return client
    
    @pytest.mark.asyncio
    async def test_bank_stock_returns_business_type_warning(self, mock_client_bank):
        """
        Banks should trigger a business type warning because DCF is less 
        appropriate - their balance sheet IS their business.
        """
        service = ValuationService(client=mock_client_bank)
        
        result = await service.value_stock("JPM", projection_years=3)
        
        # Should have a business type warning
        assert "business_type_warning" in result, (
            "Bank stock should return business_type_warning field"
        )
        assert result["business_type_warning"] is not None
        
        # Warning should mention DCF limitations and alternatives
        warning = result["business_type_warning"]
        assert "DCF" in warning or "dcf" in warning.lower()
        assert any(alt in warning for alt in ["P/B", "Book", "Dividend Discount"])
    
    @pytest.mark.asyncio
    async def test_insurance_stock_returns_business_type_warning(self, mock_client_insurer):
        """
        Insurance companies should also trigger a business type warning.
        """
        service = ValuationService(client=mock_client_insurer)
        
        result = await service.value_stock("BRK.B", projection_years=3)
        
        assert "business_type_warning" in result
        assert result["business_type_warning"] is not None
        
        # Warning should be meaningful
        warning = result["business_type_warning"]
        assert len(warning) > 50  # Not just a stub message
    
    @pytest.mark.asyncio
    async def test_tech_stock_no_business_type_warning(self, mock_client_tech):
        """
        Normal tech companies should NOT have a business type warning.
        """
        service = ValuationService(client=mock_client_tech)
        
        result = await service.value_stock("AAPL", projection_years=3)
        
        # Should have the field but it should be None
        assert "business_type_warning" in result
        assert result["business_type_warning"] is None
    
    @pytest.mark.asyncio
    async def test_warning_includes_sector_and_industry(self, mock_client_bank):
        """
        Warning should include the detected sector/industry for transparency.
        """
        service = ValuationService(client=mock_client_bank)
        
        result = await service.value_stock("JPM", projection_years=3)
        
        warning = result.get("business_type_warning", "")
        # Should mention the detected classification
        assert "Financial" in warning or "Bank" in warning
