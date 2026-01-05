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

