"""
Tests for schema input validation ranges.

High Priority #4: Add field validators to catch unrealistic inputs early.
"""
import pytest
from pydantic import ValidationError

from app.schemas.stock import (
    ValuationRequest,
    ScenarioInput,
    MonteCarloRequest,
    FullMonteCarloRequest,
)


class TestTerminalGrowthValidation:
    """Terminal growth rate must be 0-10%."""
    
    def test_terminal_growth_accepts_valid_range(self):
        """Terminal growth between 0% and 10% should be accepted."""
        # 3% - typical
        req = ValuationRequest(
            revenue_growth=0.10,
            operating_margin=0.20,
            terminal_growth_rate=0.03,
            market_risk_premium=0.055,
            projection_years=5,
        )
        assert req.terminal_growth_rate == 0.03
        
        # 0% - zero growth
        req2 = ValuationRequest(
            revenue_growth=0.10,
            operating_margin=0.20,
            terminal_growth_rate=0.0,
            market_risk_premium=0.055,
            projection_years=5,
        )
        assert req2.terminal_growth_rate == 0.0
        
        # 10% - upper bound
        req3 = ValuationRequest(
            revenue_growth=0.10,
            operating_margin=0.20,
            terminal_growth_rate=0.10,
            market_risk_premium=0.055,
            projection_years=5,
        )
        assert req3.terminal_growth_rate == 0.10
    
    def test_terminal_growth_rejects_negative(self):
        """Negative terminal growth should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ValuationRequest(
                revenue_growth=0.10,
                operating_margin=0.20,
                terminal_growth_rate=-0.01,  # Invalid
                market_risk_premium=0.055,
                projection_years=5,
            )
        assert "terminal_growth_rate" in str(exc_info.value)
    
    def test_terminal_growth_rejects_above_10_percent(self):
        """Terminal growth above 10% should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ValuationRequest(
                revenue_growth=0.10,
                operating_margin=0.20,
                terminal_growth_rate=0.15,  # Invalid - 15%
                market_risk_premium=0.055,
                projection_years=5,
            )
        assert "terminal_growth_rate" in str(exc_info.value)


class TestOperatingMarginValidation:
    """Operating margin should be -50% to 80%."""
    
    def test_operating_margin_accepts_valid_range(self):
        """Operating margin between -50% and 80% should be accepted."""
        req = ValuationRequest(
            revenue_growth=0.10,
            operating_margin=0.25,  # 25%
            terminal_growth_rate=0.03,
            market_risk_premium=0.055,
            projection_years=5,
        )
        assert req.operating_margin == 0.25
    
    def test_operating_margin_accepts_negative(self):
        """Negative operating margin (loss-making) should be accepted up to -50%."""
        req = ValuationRequest(
            revenue_growth=0.10,
            operating_margin=-0.10,  # -10% loss
            terminal_growth_rate=0.03,
            market_risk_premium=0.055,
            projection_years=5,
        )
        assert req.operating_margin == -0.10
    
    def test_operating_margin_rejects_unrealistic_high(self):
        """Operating margin above 80% is unrealistic."""
        with pytest.raises(ValidationError) as exc_info:
            ValuationRequest(
                revenue_growth=0.10,
                operating_margin=0.90,  # 90% - unrealistic
                terminal_growth_rate=0.03,
                market_risk_premium=0.055,
                projection_years=5,
            )
        assert "operating_margin" in str(exc_info.value)


class TestProjectionYearsValidation:
    """Projection years should be 1-30."""
    
    def test_projection_years_accepts_valid_range(self):
        """Projection years between 1 and 30 should be accepted."""
        req = ValuationRequest(
            revenue_growth=0.10,
            operating_margin=0.20,
            terminal_growth_rate=0.03,
            market_risk_premium=0.055,
            projection_years=10,
        )
        assert req.projection_years == 10
    
    def test_projection_years_rejects_zero(self):
        """Zero projection years is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ValuationRequest(
                revenue_growth=0.10,
                operating_margin=0.20,
                terminal_growth_rate=0.03,
                market_risk_premium=0.055,
                projection_years=0,
            )
        assert "projection_years" in str(exc_info.value)
    
    def test_projection_years_rejects_excessive(self):
        """More than 30 years projection is unreliable."""
        with pytest.raises(ValidationError) as exc_info:
            ValuationRequest(
                revenue_growth=0.10,
                operating_margin=0.20,
                terminal_growth_rate=0.03,
                market_risk_premium=0.055,
                projection_years=50,  # Too far out
            )
        assert "projection_years" in str(exc_info.value)


class TestScenarioInputValidation:
    """ScenarioInput should also validate ranges."""
    
    def test_scenario_terminal_growth_validated(self):
        """Scenario terminal growth should be validated."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioInput(
                name="Test",
                revenue_growth=0.10,
                operating_margin=0.20,
                terminal_growth=0.20,  # Invalid - 20%
            )
        assert "terminal_growth" in str(exc_info.value)
    
    def test_scenario_probability_validated(self):
        """Scenario probability should be 0-1."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioInput(
                name="Test",
                revenue_growth=0.10,
                operating_margin=0.20,
                terminal_growth=0.03,
                probability=1.5,  # Invalid - > 1
            )
        assert "probability" in str(exc_info.value)
    
    def test_scenario_operating_margin_validated(self):
        """
        Bug: ScenarioInput.operating_margin lacked validator while 
        ValuationRequest had one. Both should reject unrealistic values.
        """
        with pytest.raises(ValidationError) as exc_info:
            ScenarioInput(
                name="Test",
                revenue_growth=0.10,
                operating_margin=0.95,  # Invalid - 95%
                terminal_growth=0.03,
            )
        assert "operating_margin" in str(exc_info.value)
