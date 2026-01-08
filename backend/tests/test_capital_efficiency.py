import pytest
from app.services.capital_efficiency import CapitalEfficiencyCalculator, analyze_value_creation


class TestCapitalEfficiencyCalculator:
    """Tests for ROIC and capital efficiency metrics."""
    
    @pytest.fixture
    def basic_calculator(self):
        """Basic calculator with sample data."""
        return CapitalEfficiencyCalculator(
            nopat=100,
            invested_capital=500,
            revenue_growth=0.10,
        )
    
    def test_roic_calculation(self, basic_calculator):
        """ROIC = NOPAT / Invested Capital."""
        roic = basic_calculator.roic()
        # 100 / 500 = 0.20 (20%)
        assert abs(roic - 0.20) < 0.001
    
    def test_reinvestment_rate(self, basic_calculator):
        """Reinvestment Rate = Growth / ROIC."""
        rr = basic_calculator.reinvestment_rate()
        # 0.10 / 0.20 = 0.50 (50%)
        assert abs(rr - 0.50) < 0.001
    
    def test_value_creation_positive(self, basic_calculator):
        """Growth is value-creating when ROIC > WACC."""
        wacc = 0.10  # 10%
        roic = basic_calculator.roic()  # 20%
        
        # ROIC (20%) > WACC (10%), so growth creates value
        assert roic > wacc
        assert basic_calculator.is_value_creating(wacc)
    
    def test_value_creation_negative(self):
        """Growth destroys value when ROIC < WACC."""
        calculator = CapitalEfficiencyCalculator(
            nopat=50,
            invested_capital=1000,  # Low ROIC = 5%
            revenue_growth=0.15,
        )
        
        wacc = 0.10  # 10%
        roic = calculator.roic()  # 5%
        
        # ROIC (5%) < WACC (10%), so growth destroys value
        assert roic < wacc
        assert not calculator.is_value_creating(wacc)
    
    def test_value_spread(self):
        """Value spread = ROIC - WACC."""
        calculator = CapitalEfficiencyCalculator(
            nopat=150,
            invested_capital=1000,  # ROIC = 15%
            revenue_growth=0.10,
        )
        
        wacc = 0.10
        spread = calculator.value_spread(wacc)
        
        # 15% - 10% = 5%
        assert abs(spread - 0.05) < 0.001
    
    def test_economic_profit(self):
        """Economic Profit (EVA) = (ROIC - WACC) × Invested Capital."""
        calculator = CapitalEfficiencyCalculator(
            nopat=200,
            invested_capital=1000,  # ROIC = 20%
            revenue_growth=0.10,
        )
        
        wacc = 0.10
        eva = calculator.economic_profit(wacc)
        
        # (20% - 10%) × 1000 = 100
        assert abs(eva - 100) < 0.1
    
    def test_zero_invested_capital_returns_none(self):
        """Zero invested capital should return None for ROIC."""
        calculator = CapitalEfficiencyCalculator(
            nopat=100,
            invested_capital=0,
            revenue_growth=0.10,
        )
        
        assert calculator.roic() is None
        assert calculator.reinvestment_rate() is None
    
    def test_negative_invested_capital_returns_none(self):
        """Negative invested capital should return None for ROIC."""
        calculator = CapitalEfficiencyCalculator(
            nopat=100,
            invested_capital=-500,
            revenue_growth=0.10,
        )
        
        assert calculator.roic() is None
    
    def test_zero_growth_reinvestment_rate(self):
        """Zero growth = zero reinvestment rate."""
        calculator = CapitalEfficiencyCalculator(
            nopat=100,
            invested_capital=500,
            revenue_growth=0.0,
        )
        
        rr = calculator.reinvestment_rate()
        assert rr == 0.0
    
    def test_high_roic_company(self):
        """Asset-light company with very high ROIC."""
        calculator = CapitalEfficiencyCalculator(
            nopat=500,
            invested_capital=200,  # ROIC = 250%
            revenue_growth=0.25,
        )
        
        roic = calculator.roic()
        rr = calculator.reinvestment_rate()
        
        assert abs(roic - 2.50) < 0.001  # 250%
        assert abs(rr - 0.10) < 0.001  # Only needs to reinvest 10% of earnings


class TestAnalyzeValueCreation:
    """Tests for the high-level value creation analysis function."""
    
    def test_returns_analysis_dict(self):
        """analyze_value_creation returns comprehensive analysis."""
        result = analyze_value_creation(
            nopat=100,
            invested_capital=500,
            revenue_growth=0.10,
            wacc=0.08,
        )
        
        assert "roic" in result
        assert "reinvestment_rate" in result
        assert "value_spread" in result
        assert "economic_profit" in result
        assert "is_value_creating" in result
        assert "assessment" in result
    
    def test_strong_value_creator_assessment(self):
        """Strong value creator gets positive assessment."""
        result = analyze_value_creation(
            nopat=200,
            invested_capital=500,  # ROIC = 40%
            revenue_growth=0.20,
            wacc=0.10,
        )
        
        assert result["is_value_creating"] is True
        assert "creates" in result["assessment"].lower() or "strong" in result["assessment"].lower()
    
    def test_value_destroyer_assessment(self):
        """Value destroyer gets negative assessment."""
        result = analyze_value_creation(
            nopat=30,
            invested_capital=500,  # ROIC = 6%
            revenue_growth=0.20,
            wacc=0.12,  # WACC > ROIC
        )
        
        assert result["is_value_creating"] is False
        assert "destroyer" in result["assessment"].lower() or "reduces" in result["assessment"].lower()
