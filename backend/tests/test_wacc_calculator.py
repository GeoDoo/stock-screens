import pytest
from app.services.wacc_calculator import WACCCalculator


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

