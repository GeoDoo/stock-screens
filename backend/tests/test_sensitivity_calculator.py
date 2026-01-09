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
