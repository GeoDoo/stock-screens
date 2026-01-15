import pytest
from app.services.scenario_calculator import ScenarioCalculator, Scenario

def test_scenario_currency_normalization():
    """
    TDD: Failing test for currency normalization in ScenarioCalculator.
    The ScenarioResult should include currency information.
    """
    calc = ScenarioCalculator(
        historical_revenue=[100, 110, 120],
        historical_ebit=[20, 22, 24],
        historical_da=[5, 5, 5],
        historical_capex=[-10, -10, -10],
        historical_working_capital=[10, 11, 12],
        tax_rate=0.25,
        shares_outstanding=1000,
        total_debt=200,
        cash=100,
        base_wacc=0.10,
        projection_years=5,
        # currency="EUR" # This argument doesn't exist yet!
    )
    
    scenario = Scenario(
        name="Base Case",
        revenue_growth=0.05,
        operating_margin=0.20,
        terminal_growth=0.02,
        probability=1.0
    )
    
    res = calc.run_scenario(scenario)
    
    # This should fail because ScenarioResult doesn't have 'currency' attribute
    # and we want ScenarioCalculator to handle currency.
    assert hasattr(res, "currency")
