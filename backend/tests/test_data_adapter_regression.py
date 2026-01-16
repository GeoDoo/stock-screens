import pytest
from app.services.data_adapter import ixbrl_facts_to_legacy

def test_ixbrl_facts_to_legacy_gross_profit_fallback():
    """Test that gross_profit is calculated from revenue and cost_of_revenue if missing."""
    facts = [
        {
            "date": "2023-12-31",
            "duration": 365,
            "revenue": 1000.0,
            "cost_of_revenue": 400.0,
            # gross_profit is missing
            "operating_cash_flow": 200.0,
            "capex": 50.0
        }
    ]
    
    legacy = ixbrl_facts_to_legacy(facts)
    
    # Check income statement
    income_stmt = legacy["income_statement"][0]
    assert income_stmt["grossProfit"] == 600.0
    assert income_stmt["grossProfitRatio"] == 0.6
    
    # Check cash flow (also verifying FCF reconstruction and camelCase keys)
    cash_flow = legacy["cash_flow"][0]
    assert cash_flow["operatingCashFlow"] == 200.0
    assert cash_flow["capitalExpenditure"] == 50.0
    assert cash_flow["freeCashFlow"] == 150.0

def test_ixbrl_facts_to_legacy_negative_capex():
    """Test that FCF is calculated correctly even if capex is negative in source."""
    facts = [
        {
            "date": "2023-12-31",
            "duration": 365,
            "operating_cash_flow": 200.0,
            "capex": -50.0  # Common in some filings
        }
    ]
    
    legacy = ixbrl_facts_to_legacy(facts)
    cash_flow = legacy["cash_flow"][0]
    assert cash_flow["freeCashFlow"] == 150.0
