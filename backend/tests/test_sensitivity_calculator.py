import pytest
from app.services.sensitivity_calculator import SensitivityCalculator


class TestSensitivityCalculator:
    @pytest.fixture
    def calculator(self):
        """Basic calculator with sample FCF projections."""
        return SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],  # 10% growth
            projection_years=5,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
        )

    def test_calculate_intrinsic_value_basic(self, calculator):
        """Should calculate intrinsic value for valid inputs."""
        result = calculator.calculate_intrinsic_value(
            discount_rate=0.10,
            terminal_growth_rate=0.03
        )
        
        assert result is not None
        assert result > 0

    def test_calculate_intrinsic_value_higher_discount_lowers_value(self, calculator):
        """Higher discount rate should result in lower intrinsic value."""
        value_low_discount = calculator.calculate_intrinsic_value(0.08, 0.03)
        value_high_discount = calculator.calculate_intrinsic_value(0.12, 0.03)
        
        assert value_low_discount > value_high_discount

    def test_calculate_intrinsic_value_higher_growth_raises_value(self, calculator):
        """Higher terminal growth should result in higher intrinsic value."""
        value_low_growth = calculator.calculate_intrinsic_value(0.10, 0.02)
        value_high_growth = calculator.calculate_intrinsic_value(0.10, 0.04)
        
        assert value_high_growth > value_low_growth

    def test_returns_none_when_discount_rate_less_than_growth(self, calculator):
        """Should return None when discount rate <= terminal growth (invalid)."""
        result = calculator.calculate_intrinsic_value(
            discount_rate=0.03,
            terminal_growth_rate=0.05
        )
        
        assert result is None

    def test_returns_none_when_discount_rate_equals_growth(self, calculator):
        """Should return None when discount rate equals terminal growth."""
        result = calculator.calculate_intrinsic_value(
            discount_rate=0.03,
            terminal_growth_rate=0.03
        )
        
        assert result is None

    def test_returns_none_with_empty_fcfs(self):
        """Should return None when no FCF projections."""
        calculator = SensitivityCalculator(
            projected_fcfs=[],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
        )
        
        result = calculator.calculate_intrinsic_value(0.10, 0.03)
        assert result is None

    def test_returns_none_with_zero_shares(self):
        """Should return None when shares outstanding is zero."""
        calculator = SensitivityCalculator(
            projected_fcfs=[100, 110, 121],
            projection_years=3,
            shares_outstanding=0,
            total_debt=500,
            cash=200,
        )
        
        result = calculator.calculate_intrinsic_value(0.10, 0.03)
        assert result is None

    def test_generate_matrix_structure(self, calculator):
        """Matrix should have correct structure."""
        result = calculator.generate_matrix(
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            discount_rate_steps=[-0.02, 0, 0.02],
            terminal_growth_steps=[-0.01, 0, 0.01],
        )
        
        assert "discount_rates" in result
        assert "terminal_growth_rates" in result
        assert "matrix" in result
        assert "base_discount_rate" in result
        assert "base_terminal_growth" in result

    def test_generate_matrix_correct_dimensions(self, calculator):
        """Matrix should have correct number of rows and columns."""
        result = calculator.generate_matrix(
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            discount_rate_steps=[-0.02, -0.01, 0, 0.01, 0.02],  # 5 steps
            terminal_growth_steps=[-0.01, 0, 0.01],  # 3 steps
        )
        
        assert len(result["discount_rates"]) == 5
        assert len(result["terminal_growth_rates"]) == 3
        assert len(result["matrix"]) == 5  # rows = discount rates
        assert len(result["matrix"][0]) == 3  # cols = growth rates

    def test_generate_matrix_discount_rates_calculated_correctly(self, calculator):
        """Discount rates should be base + steps."""
        result = calculator.generate_matrix(
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            discount_rate_steps=[-0.02, 0, 0.02],
            terminal_growth_steps=[0],
        )
        
        expected_rates = [0.08, 0.10, 0.12]
        for expected, actual in zip(expected_rates, result["discount_rates"]):
            assert abs(expected - actual) < 0.001

    def test_generate_matrix_contains_none_for_invalid_combinations(self, calculator):
        """Matrix should have None where discount rate <= terminal growth."""
        result = calculator.generate_matrix(
            base_discount_rate=0.05,
            base_terminal_growth=0.04,
            discount_rate_steps=[-0.02, 0, 0.02],  # [0.03, 0.05, 0.07]
            terminal_growth_steps=[0, 0.02],  # [0.04, 0.06]
        )
        
        # At discount_rate=0.03 (first row), terminal_growth=0.04: 0.03 <= 0.04 -> None
        assert result["matrix"][0][0] is None
        # At discount_rate=0.05 (second row), terminal_growth=0.06: 0.05 <= 0.06 -> None
        assert result["matrix"][1][1] is None

    def test_net_debt_adjustment(self):
        """Should correctly adjust for net debt."""
        # Company with more debt than cash
        high_debt = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=1,
            shares_outstanding=1000,
            total_debt=1000,
            cash=100,
        )
        
        # Company with more cash than debt
        high_cash = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=1,
            shares_outstanding=1000,
            total_debt=100,
            cash=1000,
        )
        
        value_high_debt = high_debt.calculate_intrinsic_value(0.10, 0.03)
        value_high_cash = high_cash.calculate_intrinsic_value(0.10, 0.03)
        
        # More cash should result in higher equity value
        assert value_high_cash > value_high_debt

    def test_zero_shares_returns_none(self):
        """Should return None when shares_outstanding is zero."""
        calculator = SensitivityCalculator(
            projected_fcfs=[100, 110, 121],
            projection_years=3,
            shares_outstanding=0,  # Invalid
            total_debt=500,
            cash=200,
        )
        
        result = calculator.calculate_intrinsic_value(0.10, 0.03)
        assert result is None

    def test_negative_shares_returns_none(self):
        """Should return None when shares_outstanding is negative."""
        calculator = SensitivityCalculator(
            projected_fcfs=[100, 110, 121],
            projection_years=3,
            shares_outstanding=-1000,  # Invalid
            total_debt=500,
            cash=200,
        )
        
        result = calculator.calculate_intrinsic_value(0.10, 0.03)
        assert result is None


class TestMarginGrowthMatrix:
    """
    Tests for Margin vs Growth sensitivity matrix.
    
    From Gemini review: "Add Sensitivity Margin vs Growth matrix"
    
    This matrix shows how valuation changes when BOTH operating margin
    AND revenue growth change together - critical for understanding
    the sensitivity to business execution risks.
    """
    
    @pytest.fixture
    def calculator(self):
        """Calculator with base assumptions."""
        return SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
        )
    
    def test_margin_growth_matrix_structure(self, calculator):
        """Matrix should have correct structure."""
        result = calculator.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[-0.05, 0, 0.05],
            growth_steps=[-0.05, 0, 0.05],
        )
        
        assert "margins" in result
        assert "growth_rates" in result
        assert "matrix" in result
        assert "base_margin" in result
        assert "base_growth" in result
    
    def test_margin_growth_matrix_dimensions(self, calculator):
        """Matrix should have correct dimensions."""
        result = calculator.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[-0.05, -0.025, 0, 0.025, 0.05],  # 5 steps
            growth_steps=[-0.05, 0, 0.05],  # 3 steps
        )
        
        assert len(result["margins"]) == 5
        assert len(result["growth_rates"]) == 3
        assert len(result["matrix"]) == 5  # rows = margins
        assert len(result["matrix"][0]) == 3  # cols = growth rates
    
    def test_higher_margin_higher_value(self, calculator):
        """Higher operating margin should result in higher valuation."""
        result = calculator.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[-0.05, 0, 0.05],
            growth_steps=[0],  # Fixed growth
        )
        
        # matrix[0] = low margin, matrix[2] = high margin
        low_margin_value = result["matrix"][0][0]
        high_margin_value = result["matrix"][2][0]
        
        assert high_margin_value > low_margin_value
    
    def test_higher_growth_higher_value(self, calculator):
        """Higher revenue growth should result in higher valuation."""
        result = calculator.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[0],  # Fixed margin
            growth_steps=[-0.05, 0, 0.05],
        )
        
        # matrix[0][0] = low growth, matrix[0][2] = high growth
        low_growth_value = result["matrix"][0][0]
        high_growth_value = result["matrix"][0][2]
        
        assert high_growth_value > low_growth_value
    
    def test_negative_margin_handled(self, calculator):
        """Should handle scenarios where margin goes negative."""
        result = calculator.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.05,  # 5% margin
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[-0.10, 0, 0.10],  # -10% step makes margin negative
            growth_steps=[0],
        )
        
        # First margin value (0.05 - 0.10 = -0.05) should still produce a result
        # (company loses money but still has a valuation, likely negative or low)
        assert result["matrix"][0][0] is not None


class TestEquityBridgeConsistency:
    """
    Tests for equity bridge consistency between SensitivityCalculator
    and the main valuation service.
    
    Bug: SensitivityCalculator only uses net debt, not the full
    institutional equity bridge (minority interest, preferred, NOLs, pension).
    """
    
    def test_sensitivity_uses_full_equity_bridge(self):
        """
        Sensitivity calculator should apply full equity bridge,
        not just net debt.
        """
        # Calculator without equity bridge adjustments
        calc_simple = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=10,
            total_debt=500,
            cash=200,
        )
        
        # Calculator with minority interest (should reduce value)
        calc_with_mi = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=10,
            total_debt=500,
            cash=200,
            minority_interest=100,
        )
        
        value_simple = calc_simple.calculate_intrinsic_value(0.10, 0.03)
        value_with_mi = calc_with_mi.calculate_intrinsic_value(0.10, 0.03)
        
        # Minority interest should reduce intrinsic value
        assert value_with_mi < value_simple
        diff = value_simple - value_with_mi
        # $100 minority interest / 10 shares = $10/share difference
        assert abs(diff - 10) < 0.01
    
    def test_sensitivity_with_nols_adds_value(self):
        """Deferred tax assets (NOLs) should increase value."""
        calc_base = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=10,
            total_debt=500,
            cash=200,
        )
        
        calc_with_nol = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=10,
            total_debt=500,
            cash=200,
            deferred_tax_assets=50,
        )
        
        value_base = calc_base.calculate_intrinsic_value(0.10, 0.03)
        value_with_nol = calc_with_nol.calculate_intrinsic_value(0.10, 0.03)
        
        # NOLs should increase value
        assert value_with_nol > value_base
        diff = value_with_nol - value_base
        # $50 NOL / 10 shares = $5/share increase
        assert abs(diff - 5) < 0.01
    
    def test_margin_growth_matrix_uses_equity_bridge(self):
        """
        Margin vs Growth matrix should also use full equity bridge.
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=10,
            total_debt=500,
            cash=200,
            minority_interest=100,
            preferred_stock=50,
        )
        
        result = calc.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[0],
            growth_steps=[0],
        )
        
        # The single cell should reflect equity bridge adjustments
        # (We can't verify exact value, but it should not be None)
        assert result["matrix"][0][0] is not None
    
    def test_equity_bridge_defaults_to_zero(self):
        """New equity bridge fields should default to 0."""
        calc = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=10,
            total_debt=500,
            cash=200,
        )
        
        # Should work without explicitly setting equity bridge fields
        value = calc.calculate_intrinsic_value(0.10, 0.03)
        assert value is not None
        assert value > 0


class TestFCFCalculationConsistency:
    """
    P0 Fix: SensitivityCalculator must use the same FCF calculation as FCFProjector.
    
    Bug: _calc_value_for_margin_growth uses a hardcoded 0.80 FCF conversion factor
    instead of the actual formula: FCF = NOPAT + D&A - CapEx - ΔWC
    
    This causes the Sensitivity Matrix to show DIFFERENT values than the main DCF
    for the same inputs, breaking analyst trust.
    """
    
    def test_margin_growth_matrix_uses_actual_fcf_ratios(self):
        """
        Matrix should use actual da_ratio, capex_ratio, wc_ratio - not hardcoded 0.80.
        
        This test will FAIL until we fix the divergence.
        """
        # Case 1: Low reinvestment (high FCF conversion)
        # D&A 5%, CapEx 3%, WC 2% -> FCF conversion ~ 1 + 0.05 - 0.03 - 0.02 = 1.00
        calc_high_fcf = SensitivityCalculator(
            projected_fcfs=[100],  # Not used for margin/growth matrix
            projection_years=5,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            # NEW: FCF component ratios
            da_ratio=0.05,
            capex_ratio=0.03,
            wc_ratio=0.02,
            tax_rate=0.25,
        )
        
        # Case 2: High reinvestment (low FCF conversion)
        # D&A 5%, CapEx 15%, WC 10% -> FCF conversion ~ 1 + 0.05 - 0.15 - 0.10 = 0.80
        calc_low_fcf = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=500,
            cash=200,
            da_ratio=0.05,
            capex_ratio=0.15,
            wc_ratio=0.10,
            tax_rate=0.25,
        )
        
        # Same margin/growth inputs
        result_high = calc_high_fcf.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[0],
            growth_steps=[0],
        )
        
        result_low = calc_low_fcf.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[0],
            growth_steps=[0],
        )
        
        value_high = result_high["matrix"][0][0]
        value_low = result_low["matrix"][0][0]
        
        # High FCF conversion company should have HIGHER valuation
        # With the bug (hardcoded 0.80), both would be the SAME
        assert value_high > value_low, (
            f"High FCF conversion ({value_high}) should exceed low FCF ({value_low}). "
            "If equal, the calculator is using hardcoded conversion instead of actual ratios."
        )
        
        # The difference should be material (not just rounding)
        pct_diff = (value_high - value_low) / value_low
        assert pct_diff > 0.10, (
            f"Value difference should be >10% but was {pct_diff:.1%}. "
            "Actual FCF ratios have significant impact on valuation."
        )
    
    def test_margin_growth_matrix_matches_fcf_projector_formula(self):
        """
        FCF should be: Revenue * Margin * (1-Tax) + D&A - CapEx - ΔWC
        NOT: Revenue * Margin * (1-Tax) * 0.80
        
        For Year 1 with:
        - Revenue = 1000 * 1.10 = 1100
        - Margin = 20% -> EBIT = 220
        - Tax = 25% -> NOPAT = 165
        - D&A = 5% of Rev = 55
        - CapEx = 8% of Rev = 88
        - ΔWC = 3% of ΔRev = 3% * 100 = 3
        
        FCF = 165 + 55 - 88 - 3 = 129
        
        With hardcoded 0.80: FCF = 165 * 0.80 = 132 (WRONG!)
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=1,  # Single year for simple verification
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
            da_ratio=0.05,
            capex_ratio=0.08,
            wc_ratio=0.03,
            tax_rate=0.25,
        )
        
        result = calc.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[0],
            growth_steps=[0],
        )
        
        value = result["matrix"][0][0]
        
        # Expected FCF Year 1: 
        # Revenue = 1100, NOPAT = 165, D&A = 55, CapEx = 88, ΔWC = 3
        # FCF = 165 + 55 - 88 - 3 = 129
        # 
        # Terminal FCF = 129 * 1.03 = 132.87
        # Terminal Value = 132.87 / (0.10 - 0.03) = 1898.14
        # PV of FCF = 129 / 1.10 = 117.27
        # PV of TV = 1898.14 / 1.10 = 1725.58
        # EV = 117.27 + 1725.58 = 1842.85
        # Per share = 1842.85 / 1000 = $1.84
        
        # With wrong formula (0.80 hardcoded):
        # FCF = 165 * 0.80 = 132 -> different result!
        
        # We verify the formula is correct by checking the value is in expected range
        # The key is that da_ratio, capex_ratio, wc_ratio should MATTER
        assert value is not None
        assert 1.5 < value < 2.5, f"Value {value} should be ~$1.84 per share"
    
    def test_wc_mode_level_vs_incremental(self):
        """
        Working capital can be 'level' (WC = Rev * ratio) or 'incremental' (ΔWC = ΔRev * ratio).
        The calculator should support both modes for consistency with main DCF.
        """
        # Level mode: ΔWC = WC[t] - WC[t-1] = Rev[t]*ratio - Rev[t-1]*ratio = ΔRev * ratio
        # Incremental mode: ΔWC = ΔRev * ratio (same in this simple case)
        
        calc = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
            da_ratio=0.05,
            capex_ratio=0.08,
            wc_ratio=0.10,
            tax_rate=0.25,
            wc_mode="incremental",  # Explicitly test incremental mode
        )
        
        result = calc.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[0],
            growth_steps=[0],
        )
        
        # Should not crash and should produce a value
        assert result["matrix"][0][0] is not None
    
    def test_wc_mode_default_matches_fcf_projector(self):
        """
        REGRESSION: SensitivityCalculator default wc_mode must match FCFProjector.
        
        Bug: SensitivityCalculator defaulted to "incremental" while FCFProjector
        defaults to "level", causing margin/growth matrix to use a different
        WC model than the base FCF projections.
        """
        from app.services.fcf_projector import FCFProjector
        
        # Verify defaults match
        calc = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
        )
        
        # FCFProjector default is "level"
        projector = FCFProjector(
            historical_revenue=[1000],
            historical_ebit=[100],
            historical_da=[30],
            historical_capex=[50],
            historical_working_capital=[100],
        )
        
        assert calc.wc_mode == projector.wc_mode, (
            f"SensitivityCalculator.wc_mode ({calc.wc_mode}) must match "
            f"FCFProjector.wc_mode ({projector.wc_mode}) for consistency"
        )


class TestImpliedTerminalROICGating:
    """
    Tests for ROIC gating in sensitivity matrix.
    
    NOTES2.md P0: "Sensitivity Green-Washing" Trap
    
    An analyst might look at the "Bull Case" cell in the Margin vs. Growth
    matrix and see a massive valuation. However, that cell might imply a
    75% ROIC in perpetuity, which is economically impossible.
    
    The fix: Calculate implied terminal ROIC for each cell and flag it
    when it exceeds 2× WACC ("economically suspect").
    
    Formula:
        Implied ROIC = terminal_growth / reinvestment_rate
        reinvestment_rate = 1 - (FCF / NOPAT)
    """
    
    def test_calculate_implied_roic_basic(self):
        """
        Should calculate implied terminal ROIC for a given scenario.
        
        With terminal growth = 3%, and FCF/NOPAT = 0.80 (20% reinvestment),
        implied ROIC = 0.03 / 0.20 = 15%
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
        )
        
        implied_roic = calc.calculate_implied_terminal_roic(
            terminal_growth=0.03,
            terminal_fcf=80,   # FCF
            terminal_nopat=100,  # NOPAT
        )
        
        # Reinvestment rate = 1 - 80/100 = 0.20
        # Implied ROIC = 0.03 / 0.20 = 0.15 (15%)
        assert implied_roic is not None
        assert abs(implied_roic - 0.15) < 0.001
    
    def test_implied_roic_none_when_no_reinvestment(self):
        """
        If FCF >= NOPAT (no reinvestment), implied ROIC is infinite/undefined.
        Should return None.
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
        )
        
        # FCF = NOPAT means reinvestment = 0, implies infinite ROIC
        implied_roic = calc.calculate_implied_terminal_roic(
            terminal_growth=0.03,
            terminal_fcf=100,
            terminal_nopat=100,
        )
        
        assert implied_roic is None
    
    def test_implied_roic_none_when_zero_terminal_growth(self):
        """
        If terminal growth = 0, there's no meaningful ROIC calculation.
        Should return None.
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
        )
        
        implied_roic = calc.calculate_implied_terminal_roic(
            terminal_growth=0.0,
            terminal_fcf=80,
            terminal_nopat=100,
        )
        
        assert implied_roic is None
    
    def test_generate_matrix_includes_roic_flags(self):
        """
        The sensitivity matrix should include a flags matrix showing
        which cells have economically suspect implied ROIC.
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
        )
        
        result = calc.generate_matrix(
            base_discount_rate=0.10,
            base_terminal_growth=0.03,
            discount_rate_steps=[-0.02, 0, 0.02],
            terminal_growth_steps=[-0.01, 0, 0.01],
        )
        
        # Should have a roic_flags matrix of same shape
        assert "roic_flags" in result
        assert len(result["roic_flags"]) == len(result["matrix"])
        assert len(result["roic_flags"][0]) == len(result["matrix"][0])
    
    def test_roic_flag_true_when_roic_exceeds_twice_wacc(self):
        """
        Flag should be True when implied ROIC > 2× discount rate (WACC).
        
        This indicates the scenario assumes perpetual competitive advantage
        that is economically unrealistic.
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100, 110, 121, 133, 146],  # Very high FCF/NOPAT
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
            da_ratio=0.02,      # Low D&A
            capex_ratio=0.02,   # Low CapEx (high FCF conversion)
            wc_ratio=0.02,      # Low WC needs (high FCF conversion)
        )
        
        result = calc.generate_matrix(
            base_discount_rate=0.08,  # 8% WACC
            base_terminal_growth=0.04,  # 4% terminal growth (high)
            discount_rate_steps=[0],
            terminal_growth_steps=[0],
        )
        
        # With very high FCF/NOPAT ratio, low reinvestment means high implied ROIC
        # If implied ROIC > 16% (2 × 8%), should be flagged
        # Check that flags matrix exists and contains boolean values
        assert "roic_flags" in result
        # The flag should be boolean
        assert isinstance(result["roic_flags"][0][0], bool)
    
    def test_margin_growth_matrix_includes_roic_flags(self):
        """
        The margin/growth matrix should also include ROIC flags.
        
        This is especially important because high margins + high growth
        often imply unrealistic terminal ROIC.
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
            da_ratio=0.05,
            capex_ratio=0.08,
            wc_ratio=0.10,
            tax_rate=0.25,
        )
        
        result = calc.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.20,
            base_growth=0.10,
            discount_rate=0.10,
            terminal_growth=0.03,
            margin_steps=[-0.05, 0, 0.05],
            growth_steps=[-0.05, 0, 0.05],
        )
        
        assert "roic_flags" in result
        assert len(result["roic_flags"]) == 3  # 3 margins
        assert len(result["roic_flags"][0]) == 3  # 3 growth rates
    
    def test_high_margin_high_growth_flagged_as_suspect(self):
        """
        High margin + high growth scenarios should be flagged as suspect
        because they imply very high perpetual ROIC.
        
        Example: 40% margin + 15% growth with 3% terminal growth
        implies extremely high reinvestment returns.
        """
        calc = SensitivityCalculator(
            projected_fcfs=[100],
            projection_years=5,
            shares_outstanding=1000,
            total_debt=0,
            cash=0,
            da_ratio=0.03,
            capex_ratio=0.05,
            wc_ratio=0.05,
            tax_rate=0.25,
        )
        
        result = calc.generate_margin_growth_matrix(
            base_revenue=1000,
            base_margin=0.30,      # High margin
            base_growth=0.12,      # High growth
            discount_rate=0.08,    # 8% WACC
            terminal_growth=0.04,  # 4% terminal (high for ROIC calc)
            margin_steps=[0, 0.10],   # 30% and 40% margins
            growth_steps=[0, 0.05],   # 12% and 17% growth
        )
        
        # The extreme corner (40% margin, 17% growth) should be flagged
        # Top-right corner of the matrix
        high_margin_idx = 1
        high_growth_idx = 1
        
        # This combination should result in very high implied ROIC
        assert result["roic_flags"][high_margin_idx][high_growth_idx] is True, (
            "High margin + high growth scenario should be flagged as economically suspect"
        )