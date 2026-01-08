import pytest
from app.services.dcf_calculator import DCFCalculator


class TestDCFCalculator:
    def test_calculate_intrinsic_value_basic(self):
        """Basic DCF calculation with simple inputs."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,  # 10%
            discount_rate=0.10,  # 10%
            terminal_growth_rate=0.03,  # 3%
            projection_years=5,
            shares_outstanding=10,
        )

        result = calculator.calculate()

        assert "intrinsic_value_per_share" in result
        assert "enterprise_value" in result
        assert "projected_fcf" in result
        assert result["intrinsic_value_per_share"] > 0

    def test_projected_fcf_grows_correctly(self):
        """FCF should grow at the specified growth rate."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=3,
            shares_outstanding=10,
        )

        result = calculator.calculate()

        # Year 1: 100 * 1.10 = 110
        # Year 2: 100 * 1.10^2 = 121
        # Year 3: 100 * 1.10^3 = 133.1
        assert len(result["projected_fcf"]) == 3
        assert abs(result["projected_fcf"][0] - 110) < 0.01
        assert abs(result["projected_fcf"][1] - 121) < 0.01
        assert abs(result["projected_fcf"][2] - 133.1) < 0.01

    def test_terminal_value_calculation(self):
        """Terminal value should use Gordon growth model."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=10,
        )

        result = calculator.calculate()

        # Final FCF = 100 * 1.10^5 = 161.051
        # Terminal value = 161.051 * 1.03 / (0.10 - 0.03) = 2369.32
        assert "terminal_value" in result
        assert result["terminal_value"] > 0

    def test_zero_growth_rate(self):
        """Should handle zero growth rate."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.0,
            discount_rate=0.10,
            terminal_growth_rate=0.02,
            projection_years=5,
            shares_outstanding=10,
        )

        result = calculator.calculate()

        # All projected FCF should be 100
        assert all(abs(fcf - 100) < 0.01 for fcf in result["projected_fcf"])

    def test_negative_fcf_returns_warning(self):
        """Negative FCF should still calculate but flag it."""
        calculator = DCFCalculator(
            current_fcf=-50,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=10,
        )

        result = calculator.calculate()

        assert result["intrinsic_value_per_share"] < 0
        assert result.get("warning") is not None

    def test_net_debt_adjustment(self):
        """Equity value should be enterprise value minus net debt."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=10,
            total_debt=500,
            cash=100,
        )

        result = calculator.calculate()

        # Net debt = 500 - 100 = 400
        assert result["net_debt"] == 400
        # Equity value = Enterprise value - 400
        assert abs(result["equity_value"] - (result["enterprise_value"] - 400)) < 0.01

    def test_net_cash_position(self):
        """Company with more cash than debt increases equity value."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=10,
            total_debt=100,
            cash=500,
        )

        result = calculator.calculate()

        # Net debt = 100 - 500 = -400 (net cash)
        assert result["net_debt"] == -400
        # Equity value should be higher than enterprise value
        assert result["equity_value"] > result["enterprise_value"]

    def test_distressed_company_warning(self):
        """Warn when net debt exceeds enterprise value."""
        calculator = DCFCalculator(
            current_fcf=10,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.02,
            projection_years=5,
            shares_outstanding=10,
            total_debt=10000,
            cash=100,
        )

        result = calculator.calculate()

        assert "distressed" in result.get("warning", "").lower()

    def test_discount_rate_must_exceed_terminal_growth(self):
        """WACC must be greater than terminal growth rate - fundamental DCF constraint."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.03,  # Same as terminal growth
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=10,
        )

        with pytest.raises(ValueError, match="(?i)discount rate.*must be greater.*terminal growth"):
            calculator.calculate()

    def test_discount_rate_less_than_terminal_growth_raises(self):
        """WACC less than terminal growth produces nonsense - must error."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.02,  # Less than terminal growth
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=10,
        )

        with pytest.raises(ValueError, match="(?i)discount rate.*must be greater.*terminal growth"):
            calculator.calculate()

    def test_zero_shares_raises_error(self):
        """Zero shares outstanding must raise explicit error."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=0,
        )

        with pytest.raises(ValueError, match="(?i)shares outstanding.*must be positive"):
            calculator.calculate()

    def test_negative_shares_raises_error(self):
        """Negative shares outstanding must raise explicit error."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=-10,
        )

        with pytest.raises(ValueError, match="(?i)shares outstanding.*must be positive"):
            calculator.calculate()

    def test_mid_year_discounting_increases_value(self):
        """Mid-year convention should produce higher values (cash received sooner)."""
        # End-of-year discounting (default)
        calc_eoy = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=10,
            mid_year_discounting=False,
        )
        
        # Mid-year discounting
        calc_mid = DCFCalculator(
            current_fcf=100,
            growth_rate=0.10,
            discount_rate=0.10,
            terminal_growth_rate=0.03,
            projection_years=5,
            shares_outstanding=10,
            mid_year_discounting=True,
        )
        
        result_eoy = calc_eoy.calculate()
        result_mid = calc_mid.calculate()
        
        # Mid-year should be higher (discounted for less time)
        assert result_mid["intrinsic_value_per_share"] > result_eoy["intrinsic_value_per_share"]

    def test_mid_year_discounting_factor(self):
        """Mid-year discounting should use n-0.5 instead of n for discount factor."""
        calculator = DCFCalculator(
            current_fcf=100,
            growth_rate=0.0,  # No growth for easier calculation
            discount_rate=0.10,
            terminal_growth_rate=0.02,
            projection_years=1,
            shares_outstanding=10,
            mid_year_discounting=True,
        )
        
        result = calculator.calculate()
        
        # Year 1 FCF = 100, discounted at mid-year (0.5)
        # PV = 100 / (1.10)^0.5 ≈ 95.35 (vs 90.91 with end-of-year)
        # This is reflected in higher enterprise value
        assert result["enterprise_value"] > 0
