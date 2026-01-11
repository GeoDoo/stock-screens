import pytest
from app.services.scenario_calculator import ScenarioCalculator, Scenario


class TestScenarioCalculator:
    @pytest.fixture
    def calculator(self):
        """Basic calculator with sample historical data."""
        return ScenarioCalculator(
            historical_revenue=[100, 110, 121],  # ~10% growth
            historical_ebit=[20, 22, 24.2],  # ~20% margin
            historical_da=[5, 5.5, 6],
            historical_capex=[-8, -8.8, -9.6],  # Stored as negative (outflows)
            historical_working_capital=[10, 11, 12.1],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=50,   # Reduced debt for realistic equity value
            cash=100,        # More cash
            base_wacc=0.10,
            projection_years=5,
            current_price=50,
        )

    def test_run_scenario_returns_result(self, calculator):
        """Should return ScenarioResult with all fields."""
        scenario = Scenario(
            name="Test",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,
            probability=0.5,
            description="Test scenario"
        )
        
        result = calculator.run_scenario(scenario)
        
        assert result.name == "Test"
        assert result.intrinsic_value > 0
        assert result.enterprise_value > 0
        assert result.equity_value > 0
        assert result.probability == 0.5
        assert result.revenue_growth == 0.08
        assert result.operating_margin == 0.20
        assert result.terminal_growth == 0.03

    def test_higher_growth_means_higher_value(self, calculator):
        """Higher revenue growth should result in higher intrinsic value."""
        low_growth = Scenario(name="Low", revenue_growth=0.02, operating_margin=0.20, terminal_growth=0.03)
        high_growth = Scenario(name="High", revenue_growth=0.15, operating_margin=0.20, terminal_growth=0.03)
        
        low_result = calculator.run_scenario(low_growth)
        high_result = calculator.run_scenario(high_growth)
        
        assert high_result.intrinsic_value > low_result.intrinsic_value

    def test_higher_margin_means_higher_value(self, calculator):
        """Higher operating margin should result in higher intrinsic value."""
        low_margin = Scenario(name="Low", revenue_growth=0.08, operating_margin=0.10, terminal_growth=0.03)
        high_margin = Scenario(name="High", revenue_growth=0.08, operating_margin=0.30, terminal_growth=0.03)
        
        low_result = calculator.run_scenario(low_margin)
        high_result = calculator.run_scenario(high_margin)
        
        assert high_result.intrinsic_value > low_result.intrinsic_value

    def test_custom_discount_rate_overrides_wacc(self, calculator):
        """Scenario discount_rate should override base WACC."""
        wacc_scenario = Scenario(
            name="WACC", revenue_growth=0.08, operating_margin=0.20, terminal_growth=0.03,
            discount_rate=None  # Use WACC
        )
        custom_scenario = Scenario(
            name="Custom", revenue_growth=0.08, operating_margin=0.20, terminal_growth=0.03,
            discount_rate=0.15  # Higher discount rate
        )
        
        wacc_result = calculator.run_scenario(wacc_scenario)
        custom_result = calculator.run_scenario(custom_scenario)
        
        # Higher discount rate should give lower value
        assert wacc_result.discount_rate == 0.10  # base WACC
        assert custom_result.discount_rate == 0.15
        assert wacc_result.intrinsic_value > custom_result.intrinsic_value

    def test_run_analysis_returns_all_scenarios(self, calculator):
        """Should run all scenarios and return results."""
        scenarios = [
            Scenario(name="Bear", revenue_growth=0.02, operating_margin=0.15, terminal_growth=0.02, probability=0.25),
            Scenario(name="Base", revenue_growth=0.08, operating_margin=0.20, terminal_growth=0.025, probability=0.50),
            Scenario(name="Bull", revenue_growth=0.15, operating_margin=0.25, terminal_growth=0.03, probability=0.25),
        ]
        
        result = calculator.run_analysis(scenarios)
        
        assert len(result.scenarios) == 3
        assert result.scenarios[0].name == "Bear"
        assert result.scenarios[1].name == "Base"
        assert result.scenarios[2].name == "Bull"

    def test_probability_weighted_value_calculated(self, calculator):
        """Should calculate weighted average when probabilities sum to 1."""
        scenarios = [
            Scenario(name="Bear", revenue_growth=0.02, operating_margin=0.15, terminal_growth=0.02, probability=0.25),
            Scenario(name="Base", revenue_growth=0.08, operating_margin=0.20, terminal_growth=0.025, probability=0.50),
            Scenario(name="Bull", revenue_growth=0.15, operating_margin=0.25, terminal_growth=0.03, probability=0.25),
        ]
        
        result = calculator.run_analysis(scenarios)
        
        assert result.probability_weighted_value is not None
        
        # Manually calculate expected weighted value
        expected = sum(s.intrinsic_value * s.probability for s in result.scenarios)
        assert abs(result.probability_weighted_value - expected) < 0.01

    def test_normalizes_when_probabilities_dont_sum_to_one(self, calculator):
        """Should normalize probabilities and still compute weighted value."""
        scenarios = [
            Scenario(name="A", revenue_growth=0.05, operating_margin=0.20, terminal_growth=0.03, probability=0.3),
            Scenario(name="B", revenue_growth=0.10, operating_margin=0.20, terminal_growth=0.03, probability=0.3),
            # Sum = 0.6, not 1.0 - should normalize
        ]
        
        result = calculator.run_analysis(scenarios)
        
        # Now normalizes instead of returning None
        assert result.probability_weighted_value is not None
        assert result.probabilities_normalized is True
        # Each should be normalized to 0.5
        assert result.scenarios[0].probability == pytest.approx(0.5, rel=0.01)
        assert result.scenarios[1].probability == pytest.approx(0.5, rel=0.01)

    def test_upside_range_calculated(self, calculator):
        """Should calculate upside range vs current price."""
        scenarios = [
            Scenario(name="Bear", revenue_growth=0.02, operating_margin=0.15, terminal_growth=0.02, probability=0.25),
            Scenario(name="Bull", revenue_growth=0.15, operating_margin=0.25, terminal_growth=0.03, probability=0.75),
        ]
        
        result = calculator.run_analysis(scenarios)
        
        # Should have min and max upside
        min_upside, max_upside = result.upside_range
        assert min_upside < max_upside
        # Bear case should be below current price or lower upside
        # Bull case should be above

    def test_get_default_scenarios_adjusts_to_historicals(self, calculator):
        """Default scenarios should be based on historical performance."""
        hints = {"revenue_growth": 0.10, "operating_margin": 0.25}
        
        scenarios = calculator.get_default_scenarios(hints)
        
        assert len(scenarios) == 3
        
        # Bear should be lower than historical
        bear = scenarios[0]
        assert bear.revenue_growth < hints["revenue_growth"]
        assert bear.operating_margin < hints["operating_margin"]
        
        # Bull should be higher than historical
        bull = scenarios[2]
        assert bull.revenue_growth > hints["revenue_growth"]

    def test_projections_included_in_result(self, calculator):
        """Scenario result should include FCF projections."""
        scenario = Scenario(name="Test", revenue_growth=0.08, operating_margin=0.20, terminal_growth=0.03)
        
        result = calculator.run_scenario(scenario)
        
        assert len(result.projections) == 5  # projection_years
        assert "revenue" in result.projections[0]
        assert "fcf" in result.projections[0]

    def test_explicit_fcf_ratios_used(self):
        """
        Explicit FCF ratios should override historical averages.
        This enables clean TTM/Annual separation.
        """
        # Calculator with HIGH historical capex
        calc_high_capex = ScenarioCalculator(
            historical_revenue=[100, 110, 121],
            historical_ebit=[20, 22, 24.2],
            historical_da=[5, 5.5, 6],
            historical_capex=[-20, -22, -24],  # High capex (~20% of revenue)
            historical_working_capital=[10, 11, 12.1],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
            # NO explicit ratios - uses historical
        )
        
        # Calculator with LOW explicit capex_ratio (override)
        calc_low_capex = ScenarioCalculator(
            historical_revenue=[100, 110, 121],
            historical_ebit=[20, 22, 24.2],
            historical_da=[5, 5.5, 6],
            historical_capex=[-20, -22, -24],  # Same high historical capex
            historical_working_capital=[10, 11, 12.1],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
            # Explicit LOW capex_ratio
            da_ratio=0.05,
            capex_ratio=0.02,  # Low capex
            wc_ratio=0.05,
        )
        
        scenario = Scenario(
            name="Test",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,
        )
        
        result_high = calc_high_capex.run_scenario(scenario)
        result_low = calc_low_capex.run_scenario(scenario)
        
        # Lower capex = higher FCF = higher intrinsic value
        assert result_low.intrinsic_value > result_high.intrinsic_value

    def test_different_fcf_ratios_produce_different_values(self):
        """Sanity check: changing WC ratio affects valuation."""
        # Low WC ratio
        calc_low_wc = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
            da_ratio=0.05,
            capex_ratio=0.05,
            wc_ratio=0.05,  # Low WC ratio
        )
        
        # High WC ratio (absorbs more cash)
        calc_high_wc = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
            da_ratio=0.05,
            capex_ratio=0.05,
            wc_ratio=0.30,  # High WC ratio
        )
        
        scenario = Scenario(
            name="Test",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,
        )
        
        result_low = calc_low_wc.run_scenario(scenario)
        result_high = calc_high_wc.run_scenario(scenario)
        
        # Lower WC = less cash absorbed = higher value
        assert result_low.intrinsic_value > result_high.intrinsic_value

    def test_default_scenarios_use_provided_hints(self, calculator):
        """Default scenarios should use provided hints, enabling TTM/Annual separation."""
        # Provide reasonable TTM hints (vs crazy annual data)
        ttm_hints = {
            "revenue_growth": 0.10,     # 10% growth
            "operating_margin": 0.15,   # 15% margin (not -1349%!)
        }
        
        scenarios = calculator.get_default_scenarios(ttm_hints)
        
        assert len(scenarios) == 3  # Bear, Base, Bull
        
        # All scenarios should have REASONABLE margins (derived from hints)
        for scenario in scenarios:
            # Margins should be between 0 and 40% for reasonable scenarios
            assert -0.5 < scenario.operating_margin < 0.5, \
                f"{scenario.name} has unreasonable margin: {scenario.operating_margin}"
            # Growth should be reasonable
            assert -0.2 < scenario.revenue_growth < 0.5, \
                f"{scenario.name} has unreasonable growth: {scenario.revenue_growth}"




class TestDiscountRateTerminalGrowthGuard:
    """
    Regression tests for r > g enforcement.
    
    Bug: ScenarioCalculator.run_scenario() did not guard against
    discount_rate <= terminal_growth, which causes division by zero
    or negative terminal values (nonsense results).
    
    The main valuation path enforces this; scenarios must too.
    """
    
    @pytest.fixture
    def calculator(self):
        """Basic calculator with sample historical data."""
        return ScenarioCalculator(
            historical_revenue=[100, 110, 121],
            historical_ebit=[20, 22, 24.2],
            historical_da=[5, 5.5, 6],
            historical_capex=[-8, -8.8, -9.6],
            historical_working_capital=[10, 11, 12.1],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=50,
            cash=100,
            base_wacc=0.10,  # 10% WACC
            projection_years=5,
            current_price=50,
        )
    
    def test_rejects_terminal_growth_equal_to_discount_rate(self, calculator):
        """
        Should raise ValueError when terminal_growth == discount_rate.
        
        This would cause division by zero: terminal_value = FCF / (r - g)
        """
        scenario = Scenario(
            name="Invalid",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.10,  # Same as WACC (10%)
        )
        
        with pytest.raises(ValueError, match="discount rate.*greater than.*terminal growth"):
            calculator.run_scenario(scenario)
    
    def test_rejects_terminal_growth_greater_than_discount_rate(self, calculator):
        """
        Should raise ValueError when terminal_growth > discount_rate.
        
        This would produce negative terminal value (nonsense).
        """
        scenario = Scenario(
            name="Invalid",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.15,  # Higher than WACC (10%)
        )
        
        with pytest.raises(ValueError, match="discount rate.*greater than.*terminal growth"):
            calculator.run_scenario(scenario)
    
    def test_accepts_terminal_growth_less_than_discount_rate(self, calculator):
        """
        Should work normally when terminal_growth < discount_rate.
        """
        scenario = Scenario(
            name="Valid",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,  # Less than WACC (10%)
        )
        
        # Should not raise
        result = calculator.run_scenario(scenario)
        assert result.intrinsic_value > 0
    
    def test_uses_scenario_discount_rate_for_validation(self, calculator):
        """
        When scenario has custom discount_rate, that should be used for validation.
        """
        # Scenario with custom discount rate lower than base WACC
        scenario = Scenario(
            name="Low DR",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.08,  # Equal to custom discount rate
            discount_rate=0.08,    # Custom DR lower than base WACC
        )
        
        # Should reject because custom discount_rate == terminal_growth
        with pytest.raises(ValueError, match="discount rate.*greater than.*terminal growth"):
            calculator.run_scenario(scenario)


class TestProbabilityNormalization:
    """
    Tests for automatic probability normalization.
    
    Bug: If user enters Bear(0.2), Base(0.5), Bull(0.2) = 0.9 total,
    the weighted value silently becomes None instead of normalizing.
    
    Solution: Automatically normalize probabilities to sum to 1.0 and
    indicate when normalization was applied.
    """
    
    @pytest.fixture
    def calculator(self):
        return ScenarioCalculator(
            historical_revenue=[100, 110, 121],
            historical_ebit=[20, 22, 24.2],
            historical_da=[5, 5.5, 6],
            historical_capex=[-8, -8.8, -9.6],
            historical_working_capital=[10, 11, 12.1],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=50,
            cash=100,
            base_wacc=0.10,
            projection_years=5,
            current_price=50,
        )
    
    def test_normalizes_probabilities_when_sum_not_one(self, calculator):
        """
        When probabilities don't sum to 1.0, normalize them automatically.
        """
        scenarios = [
            Scenario(name="Bear", revenue_growth=0.02, operating_margin=0.15, 
                     terminal_growth=0.02, probability=0.2),
            Scenario(name="Base", revenue_growth=0.06, operating_margin=0.20, 
                     terminal_growth=0.025, probability=0.5),
            Scenario(name="Bull", revenue_growth=0.10, operating_margin=0.25, 
                     terminal_growth=0.03, probability=0.2),
        ]
        # Sum = 0.9, not 1.0
        
        result = calculator.run_analysis(scenarios)
        
        # Should still compute weighted value (not None)
        assert result.probability_weighted_value is not None, (
            "Weighted value should be computed after normalizing probabilities"
        )
    
    def test_indicates_normalization_was_applied(self, calculator):
        """
        When probabilities are normalized, flag should indicate this.
        """
        scenarios = [
            Scenario(name="Bear", revenue_growth=0.02, operating_margin=0.15, 
                     terminal_growth=0.02, probability=0.2),
            Scenario(name="Base", revenue_growth=0.06, operating_margin=0.20, 
                     terminal_growth=0.025, probability=0.5),
            Scenario(name="Bull", revenue_growth=0.10, operating_margin=0.25, 
                     terminal_growth=0.03, probability=0.2),
        ]
        
        result = calculator.run_analysis(scenarios)
        
        assert result.probabilities_normalized is True, (
            "Should indicate that probabilities were normalized"
        )
    
    def test_no_normalization_when_sum_is_one(self, calculator):
        """
        When probabilities already sum to 1.0, don't flag as normalized.
        """
        scenarios = [
            Scenario(name="Bear", revenue_growth=0.02, operating_margin=0.15, 
                     terminal_growth=0.02, probability=0.25),
            Scenario(name="Base", revenue_growth=0.06, operating_margin=0.20, 
                     terminal_growth=0.025, probability=0.50),
            Scenario(name="Bull", revenue_growth=0.10, operating_margin=0.25, 
                     terminal_growth=0.03, probability=0.25),
        ]
        # Sum = 1.0 exactly
        
        result = calculator.run_analysis(scenarios)
        
        assert result.probabilities_normalized is False
        assert result.probability_weighted_value is not None
    
    def test_normalized_probabilities_in_results(self, calculator):
        """
        ScenarioResult should contain the normalized probability values.
        """
        scenarios = [
            Scenario(name="Bear", revenue_growth=0.02, operating_margin=0.15, 
                     terminal_growth=0.02, probability=0.1),  # 10%
            Scenario(name="Bull", revenue_growth=0.10, operating_margin=0.25, 
                     terminal_growth=0.03, probability=0.1),  # 10%
        ]
        # Sum = 0.2, should normalize to 0.5 each
        
        result = calculator.run_analysis(scenarios)
        
        # After normalization, each should be 0.5
        assert result.scenarios[0].probability == pytest.approx(0.5, rel=0.01)
        assert result.scenarios[1].probability == pytest.approx(0.5, rel=0.01)
    
    def test_zero_total_probability_returns_none(self, calculator):
        """
        If all probabilities are 0, can't normalize - return None for weighted value.
        """
        scenarios = [
            Scenario(name="Bear", revenue_growth=0.02, operating_margin=0.15, 
                     terminal_growth=0.02, probability=0.0),
            Scenario(name="Bull", revenue_growth=0.10, operating_margin=0.25, 
                     terminal_growth=0.03, probability=0.0),
        ]
        
        result = calculator.run_analysis(scenarios)
        
        assert result.probability_weighted_value is None
        assert result.probabilities_normalized is False


class TestEquityBridgeConsistency:
    """
    P1 Fix: ScenarioCalculator should use full equity bridge
    matching the main valuation (ValuationService).
    
    Bug: ScenarioCalculator uses net_debt only:
        equity_value = enterprise_value - (total_debt - cash)
    
    Main valuation uses:
        equity_value = EV - net_debt - MI - preferred + NOLs - pension
    
    This creates "two truths" for the same company.
    """
    
    def test_equity_bridge_includes_minority_interest(self):
        """
        Minority interest should be deducted from equity value.
        
        Companies with subsidiaries have minority interest that
        doesn't belong to common shareholders.
        """
        # Without minority interest
        calc_simple = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
        )
        
        # With minority interest
        calc_with_mi = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
            minority_interest=50,  # 50 units of minority interest
        )
        
        scenario = Scenario(
            name="Test",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,
        )
        
        result_simple = calc_simple.run_scenario(scenario)
        result_with_mi = calc_with_mi.run_scenario(scenario)
        
        # Same EV, but equity value should be lower with minority interest
        assert result_with_mi.equity_value < result_simple.equity_value
        # Difference should be exactly minority_interest (50)
        assert abs(result_simple.equity_value - result_with_mi.equity_value - 50) < 0.01
    
    def test_equity_bridge_includes_preferred_stock(self):
        """
        Preferred stock should be deducted from equity value.
        
        Preferred equity has priority over common equity.
        """
        calc_simple = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
        )
        
        calc_with_preferred = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
            preferred_stock=30,  # 30 units of preferred stock
        )
        
        scenario = Scenario(
            name="Test",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,
        )
        
        result_simple = calc_simple.run_scenario(scenario)
        result_with_preferred = calc_with_preferred.run_scenario(scenario)
        
        # Equity value should be lower with preferred stock
        assert result_with_preferred.equity_value < result_simple.equity_value
        assert abs(result_simple.equity_value - result_with_preferred.equity_value - 30) < 0.01
    
    def test_equity_bridge_adds_deferred_tax_assets(self):
        """
        Deferred tax assets (NOLs) should be ADDED to equity value.
        
        NOLs represent future tax savings that benefit shareholders.
        """
        calc_simple = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
        )
        
        calc_with_nol = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
            deferred_tax_assets=40,  # 40 units of NOLs
        )
        
        scenario = Scenario(
            name="Test",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,
        )
        
        result_simple = calc_simple.run_scenario(scenario)
        result_with_nol = calc_with_nol.run_scenario(scenario)
        
        # Equity value should be HIGHER with NOLs
        assert result_with_nol.equity_value > result_simple.equity_value
        assert abs(result_with_nol.equity_value - result_simple.equity_value - 40) < 0.01
    
    def test_equity_bridge_deducts_pension_deficit(self):
        """
        Pension deficit should be deducted from equity value.
        
        Underfunded pension obligations are a debt to employees.
        """
        calc_simple = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
        )
        
        calc_with_pension = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            base_wacc=0.10,
            projection_years=5,
            pension_deficit=25,  # 25 units of underfunded pension
        )
        
        scenario = Scenario(
            name="Test",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,
        )
        
        result_simple = calc_simple.run_scenario(scenario)
        result_with_pension = calc_with_pension.run_scenario(scenario)
        
        # Equity value should be lower with pension deficit
        assert result_with_pension.equity_value < result_simple.equity_value
        assert abs(result_simple.equity_value - result_with_pension.equity_value - 25) < 0.01


class TestDilutionInScenarios:
    """
    P1 Fix: ScenarioCalculator should support annual_dilution_rate
    for per-share intrinsic value calculation.
    
    Bug: ScenarioCalculator uses static shares_outstanding.
    Main valuation applies dilution: terminal_shares = shares * (1 + rate)^years
    
    This causes scenarios to overstate per-share value for companies
    with heavy stock-based compensation.
    """
    
    def test_dilution_reduces_per_share_value(self):
        """
        Annual dilution should reduce intrinsic value per share.
        
        Tech companies with 2-3% annual SBC issuance will see
        meaningful dilution over a 10-year projection.
        """
        # Use realistic values that produce positive equity value
        # No dilution
        calc_no_dilution = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=50,   # Lower debt
            cash=100,        # Higher cash
            base_wacc=0.10,
            projection_years=10,
        )
        
        # 3% annual dilution
        calc_with_dilution = ScenarioCalculator(
            historical_revenue=[100],
            historical_ebit=[20],
            historical_da=[5],
            historical_capex=[-8],
            historical_working_capital=[10],
            tax_rate=0.25,
            shares_outstanding=1000,
            total_debt=50,   # Same as above
            cash=100,        # Same as above
            base_wacc=0.10,
            projection_years=10,
            annual_dilution_rate=0.03,  # 3% annual dilution
        )
        
        scenario = Scenario(
            name="Test",
            revenue_growth=0.08,
            operating_margin=0.20,
            terminal_growth=0.03,
        )
        
        result_no_dilution = calc_no_dilution.run_scenario(scenario)
        result_with_dilution = calc_with_dilution.run_scenario(scenario)
        
        # Same equity value (dilution doesn't affect EV)
        assert abs(result_no_dilution.equity_value - result_with_dilution.equity_value) < 0.01
        
        # But per-share value should be lower with dilution
        assert result_with_dilution.intrinsic_value < result_no_dilution.intrinsic_value
        
        # Calculate expected reduction
        # Terminal shares = 1000 * (1.03)^10 = ~1344
        # Value reduction should be ~25%
        reduction = (result_no_dilution.intrinsic_value - result_with_dilution.intrinsic_value) / result_no_dilution.intrinsic_value
        assert 0.20 < reduction < 0.35, f"Dilution reduction {reduction:.1%} seems wrong"
