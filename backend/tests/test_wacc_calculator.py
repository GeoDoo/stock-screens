import pytest
from app.services.wacc_calculator import WACCCalculator, validate_wacc_inputs


class TestWACCCalculator:
    def test_cost_of_equity(self):
        """Cost of equity using CAPM: rf + beta * (rm - rf)"""
        calculator = WACCCalculator(
            risk_free_rate=0.04,  # 4%
            beta=1.2,
            market_risk_premium=0.06,  # 6%
            cost_of_debt=0.05,
            tax_rate=0.25,
            market_cap=1000,
            total_debt=500,
        )

        # Cost of equity = 0.04 + 1.2 * 0.06 = 0.112 (11.2%)
        assert abs(calculator.cost_of_equity() - 0.112) < 0.0001

    def test_after_tax_cost_of_debt(self):
        """Cost of debt adjusted for tax shield."""
        calculator = WACCCalculator(
            risk_free_rate=0.04,
            beta=1.0,
            market_risk_premium=0.06,
            cost_of_debt=0.08,  # 8%
            tax_rate=0.25,  # 25%
            market_cap=1000,
            total_debt=500,
        )

        # After-tax cost of debt = 0.08 * (1 - 0.25) = 0.06 (6%)
        assert abs(calculator.after_tax_cost_of_debt() - 0.06) < 0.0001

    def test_wacc_calculation(self):
        """WACC = (E/V)*Re + (D/V)*Rd*(1-T)"""
        calculator = WACCCalculator(
            risk_free_rate=0.04,
            beta=1.0,
            market_risk_premium=0.06,
            cost_of_debt=0.08,
            tax_rate=0.25,
            market_cap=1000,  # E
            total_debt=500,   # D
        )

        # V = 1000 + 500 = 1500
        # E/V = 1000/1500 = 0.6667
        # D/V = 500/1500 = 0.3333
        # Cost of equity = 0.04 + 1.0 * 0.06 = 0.10
        # After-tax cost of debt = 0.08 * 0.75 = 0.06
        # WACC = 0.6667 * 0.10 + 0.3333 * 0.06 = 0.0867 (8.67%)
        wacc = calculator.calculate()
        assert abs(wacc - 0.0867) < 0.001

    def test_zero_debt_company(self):
        """Company with no debt - WACC equals cost of equity."""
        calculator = WACCCalculator(
            risk_free_rate=0.04,
            beta=1.2,
            market_risk_premium=0.06,
            cost_of_debt=0.0,
            tax_rate=0.25,
            market_cap=1000,
            total_debt=0,
        )

        wacc = calculator.calculate()
        cost_of_equity = calculator.cost_of_equity()
        assert abs(wacc - cost_of_equity) < 0.0001

    def test_high_leverage_company(self):
        """Highly leveraged company - debt weight dominates."""
        calculator = WACCCalculator(
            risk_free_rate=0.04,
            beta=1.5,
            market_risk_premium=0.06,
            cost_of_debt=0.10,
            tax_rate=0.30,
            market_cap=200,
            total_debt=800,
        )

        wacc = calculator.calculate()
        # Should be closer to after-tax cost of debt due to high leverage
        assert wacc > 0 and wacc < 0.15


class TestWACCInputValidation:
    """Tests for input validation and guardrails."""
    
    def test_tax_rate_clamped_to_valid_range(self):
        """Tax rate should be clamped to [0, 1]."""
        # Tax rate > 1 should be clamped
        calculator = WACCCalculator(
            risk_free_rate=0.04,
            beta=1.0,
            market_risk_premium=0.06,
            cost_of_debt=0.08,
            tax_rate=1.5,  # Invalid: > 1
            market_cap=1000,
            total_debt=500,
        )
        # Should use 1.0 (max valid)
        assert calculator.after_tax_cost_of_debt() == 0.0  # 0.08 * (1 - 1.0) = 0

    def test_negative_tax_rate_clamped(self):
        """Negative tax rate should be clamped to 0."""
        calculator = WACCCalculator(
            risk_free_rate=0.04,
            beta=1.0,
            market_risk_premium=0.06,
            cost_of_debt=0.08,
            tax_rate=-0.25,  # Invalid: < 0
            market_cap=1000,
            total_debt=500,
        )
        # Should use 0.0 (min valid) - no tax shield
        assert calculator.after_tax_cost_of_debt() == 0.08  # 0.08 * (1 - 0) = 0.08

    def test_negative_debt_treated_as_zero(self):
        """Negative debt should be treated as zero (net cash position)."""
        calculator = WACCCalculator(
            risk_free_rate=0.04,
            beta=1.0,
            market_risk_premium=0.06,
            cost_of_debt=0.08,
            tax_rate=0.25,
            market_cap=1000,
            total_debt=-500,  # Negative debt
        )
        wacc = calculator.calculate()
        # With no debt, WACC should equal cost of equity
        assert abs(wacc - calculator.cost_of_equity()) < 0.0001

    def test_validate_wacc_inputs_returns_warnings(self):
        """validate_wacc_inputs should return list of warnings for bad inputs."""
        warnings = validate_wacc_inputs(
            tax_rate=1.5,
            total_debt=-100,
            market_cap=1000,
        )
        assert len(warnings) >= 2
        assert any("tax" in w.lower() for w in warnings)
        assert any("debt" in w.lower() for w in warnings)


class TestBetaUnleverRelever:
    """
    Tests for beta unlever/relever functions.
    
    Problem: Raw beta from providers reflects both business risk AND financial
    leverage. When comparing companies or using industry betas, you need to:
    1. Unlever raw beta to get "pure" business risk
    2. Relever for the target company's capital structure
    
    Hamada Equation:
    - Unlevered Beta = Levered Beta / (1 + (1 - Tax Rate) × (D/E))
    - Relevered Beta = Unlevered Beta × (1 + (1 - Tax Rate) × (D/E))
    """
    
    def test_unlever_beta_removes_leverage_effect(self):
        """
        Unlevered beta should be LOWER than levered beta for companies with debt.
        """
        from app.services.wacc_calculator import unlever_beta
        
        levered_beta = 1.5
        debt = 500
        equity = 1000  # D/E = 0.5
        tax_rate = 0.25
        
        unlevered = unlever_beta(levered_beta, debt, equity, tax_rate)
        
        # Unlevered should be lower (debt amplifies beta)
        assert unlevered < levered_beta, (
            f"Unlevered beta ({unlevered:.2f}) should be lower than "
            f"levered beta ({levered_beta:.2f}) for company with debt"
        )
        
        # Expected: 1.5 / (1 + 0.75 * 0.5) = 1.5 / 1.375 = 1.09
        assert unlevered == pytest.approx(1.09, rel=0.01)
    
    def test_unlever_beta_no_debt(self):
        """
        For company with no debt, unlevered = levered beta.
        """
        from app.services.wacc_calculator import unlever_beta
        
        levered_beta = 1.2
        unlevered = unlever_beta(levered_beta, debt=0, equity=1000, tax_rate=0.25)
        
        assert unlevered == pytest.approx(levered_beta, rel=0.01)
    
    def test_relever_beta_adds_leverage_effect(self):
        """
        Relevered beta should be HIGHER than unlevered for companies with debt.
        """
        from app.services.wacc_calculator import relever_beta
        
        unlevered_beta = 1.0  # Pure business risk
        debt = 500
        equity = 1000  # D/E = 0.5
        tax_rate = 0.25
        
        relevered = relever_beta(unlevered_beta, debt, equity, tax_rate)
        
        # Relevered should be higher (debt amplifies beta)
        assert relevered > unlevered_beta, (
            f"Relevered beta ({relevered:.2f}) should be higher than "
            f"unlevered beta ({unlevered_beta:.2f}) for company with debt"
        )
        
        # Expected: 1.0 * (1 + 0.75 * 0.5) = 1.0 * 1.375 = 1.375
        assert relevered == pytest.approx(1.375, rel=0.01)
    
    def test_unlever_relever_roundtrip(self):
        """
        Unlever then relever with same leverage should return original beta.
        """
        from app.services.wacc_calculator import unlever_beta, relever_beta
        
        original_beta = 1.5
        debt = 500
        equity = 1000
        tax_rate = 0.25
        
        unlevered = unlever_beta(original_beta, debt, equity, tax_rate)
        relevered = relever_beta(unlevered, debt, equity, tax_rate)
        
        assert relevered == pytest.approx(original_beta, rel=0.01)
    
    def test_calculate_adjusted_beta(self):
        """
        WACCCalculator should provide method to adjust beta for different leverage.
        
        Use case: Apply industry beta to company with different capital structure.
        """
        from app.services.wacc_calculator import calculate_adjusted_beta
        
        # Industry average: beta=1.2 with D/E=0.3
        industry_beta = 1.2
        industry_debt = 300
        industry_equity = 1000
        
        # Target company: D/E=0.8 (more leveraged)
        target_debt = 800
        target_equity = 1000
        
        tax_rate = 0.25
        
        adjusted = calculate_adjusted_beta(
            peer_beta=industry_beta,
            peer_debt=industry_debt,
            peer_equity=industry_equity,
            target_debt=target_debt,
            target_equity=target_equity,
            tax_rate=tax_rate,
        )
        
        # More leveraged company should have HIGHER beta
        assert adjusted > industry_beta, (
            f"More leveraged company should have higher beta. "
            f"Got {adjusted:.2f}, expected > {industry_beta:.2f}"
        )
    
    def test_high_leverage_significantly_increases_beta(self):
        """
        High leverage (D/E > 1) should significantly increase beta.
        """
        from app.services.wacc_calculator import relever_beta
        
        unlevered_beta = 1.0
        tax_rate = 0.25
        
        # D/E = 2 (very high leverage)
        high_leverage_beta = relever_beta(unlevered_beta, debt=2000, equity=1000, tax_rate=tax_rate)
        
        # Beta should roughly double with D/E=2
        # 1.0 * (1 + 0.75 * 2) = 1.0 * 2.5 = 2.5
        assert high_leverage_beta == pytest.approx(2.5, rel=0.01)
    
    def test_negative_equity_handled_safely(self):
        """
        Negative equity (technically insolvent) should return high/capped beta.
        """
        from app.services.wacc_calculator import relever_beta
        
        unlevered_beta = 1.0
        # Negative equity - company is insolvent
        relevered = relever_beta(unlevered_beta, debt=1000, equity=-100, tax_rate=0.25)
        
        # Should return a high capped value, not crash
        assert relevered is not None
        assert relevered >= 3.0, "Insolvent company should have very high beta"
    
    def test_unlever_beta_with_negative_equity_clamps_minimum(self):
        """
        P1 Bug: unlever_beta with negative equity returns min(levered_beta, MAX_BETA)
        but doesn't clamp minimum. Negative beta should be clamped to minimum.
        
        Edge case: Defensive stock with beta < 0 and negative equity.
        """
        from app.services.wacc_calculator import unlever_beta, MAX_BETA
        
        # Very low/negative beta (extremely defensive)
        levered_beta = -0.5
        
        unlevered = unlever_beta(levered_beta, debt=1000, equity=-100, tax_rate=0.25)
        
        # Should clamp to reasonable range, not return negative
        assert unlevered >= 0, f"Beta should not be negative, got {unlevered}"
        assert unlevered <= MAX_BETA, f"Beta should be capped at MAX_BETA"
    
    def test_unlever_beta_clamps_result(self):
        """
        Unlevered beta should be clamped to [0, MAX_BETA] range.
        """
        from app.services.wacc_calculator import unlever_beta, MAX_BETA
        
        # Extremely high beta
        unlevered = unlever_beta(levered_beta=10.0, debt=100, equity=1000, tax_rate=0.25)
        assert unlevered <= MAX_BETA, f"Unlevered beta {unlevered} exceeds MAX_BETA"
        
        # Very low beta (defensive stock)
        unlevered = unlever_beta(levered_beta=0.1, debt=100, equity=1000, tax_rate=0.25)
        assert unlevered >= 0, f"Unlevered beta {unlevered} should not be negative"
    
    def test_relever_beta_no_debt_still_clamps(self):
        """
        P1 Bug: relever_beta with debt <= 0 returns unlevered_beta without clamping.
        Should still enforce bounds.
        """
        from app.services.wacc_calculator import relever_beta, MAX_BETA
        
        # Extremely high unlevered beta passed directly through
        relevered = relever_beta(unlevered_beta=10.0, debt=0, equity=1000, tax_rate=0.25)
        
        # Should be capped even with no debt
        assert relevered <= MAX_BETA, (
            f"Beta {relevered} should be capped at MAX_BETA={MAX_BETA} even with no debt"
        )
    
    def test_wacc_calculator_with_adjusted_beta(self):
        """
        WACCCalculator should accept adjusted_beta parameter.
        """
        # Standard calculation with raw beta
        standard_calc = WACCCalculator(
            risk_free_rate=0.04,
            beta=1.5,  # Raw levered beta
            market_risk_premium=0.06,
            cost_of_debt=0.06,
            tax_rate=0.25,
            market_cap=1000,
            total_debt=500,
        )
        
        # Calculation with properly adjusted beta
        # First unlever the peer's beta, then relever for our capital structure
        from app.services.wacc_calculator import calculate_adjusted_beta
        
        adjusted = calculate_adjusted_beta(
            peer_beta=1.2,
            peer_debt=200,  # Peer has lower leverage
            peer_equity=1000,
            target_debt=500,  # Our company has higher leverage
            target_equity=1000,
            tax_rate=0.25,
        )
        
        adjusted_calc = WACCCalculator(
            risk_free_rate=0.04,
            beta=adjusted,
            market_risk_premium=0.06,
            cost_of_debt=0.06,
            tax_rate=0.25,
            market_cap=1000,
            total_debt=500,
        )
        
        # Both should compute WACC, but with different cost of equity
        standard_wacc = standard_calc.calculate()
        adjusted_wacc = adjusted_calc.calculate()
        
        assert standard_wacc > 0
        assert adjusted_wacc > 0
        # The adjusted beta should give different result
        assert standard_wacc != adjusted_wacc

