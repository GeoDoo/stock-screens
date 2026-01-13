import pytest
from app.services.ltm_calculator import LTMCalculator

def test_ltm_calculation_math():
    calc = LTMCalculator()
    
    # Current Q3 (9 months)
    current_facts = [
        {"date": "2025-09-30", "duration": 273, "revenue": 900, "net_income": 90},
        {"date": "2025-09-30", "duration": 0, "total_assets": 1000} # Balance Sheet
    ]
    
    # Previous FY (12 months)
    previous_fy_facts = [
        {"date": "2024-12-31", "duration": 365, "revenue": 1000, "net_income": 100}
    ]
    
    # Previous Q3 (9 months)
    previous_ytd_facts = [
        {"date": "2024-09-30", "duration": 273, "revenue": 700, "net_income": 70}
    ]
    
    # LTM = 900 + 1000 - 700 = 1200
    # LTM NI = 90 + 100 - 70 = 120
    
    ltm_result = calc.calculate_ltm_facts(current_facts, previous_fy_facts, previous_ytd_facts)
    
    assert ltm_result["date"] == "2025-09-30"
    assert ltm_result["is_ltm"] is True
    assert ltm_result["revenue"] == 1200
    assert ltm_result["net_income"] == 120
    assert ltm_result["total_assets"] == 1000 # Carried over from latest BS

def test_ltm_calculation_missing_data_fallback():
    calc = LTMCalculator()
    
    current_facts = [{"date": "2025-09-30", "duration": 273, "revenue": 900}]
    previous_fy_facts = [] # Missing
    previous_ytd_facts = [] # Missing
    
    ltm_result = calc.calculate_ltm_facts(current_facts, previous_fy_facts, previous_ytd_facts)
    
    assert ltm_result["date"] == "2025-09-30"
    assert ltm_result["is_partial_ltm"] is True
    assert ltm_result["revenue"] == 900 # Fallback to current YTD

def test_ltm_calculation_complex_mix():
    calc = LTMCalculator()
    
    # Filing often has both 3m and 9m facts. 
    # We should prefer the longest duration for LTM math.
    current_facts = [
        {"date": "2025-09-30", "duration": 273, "revenue": 900}, # YTD
        {"date": "2025-09-30", "duration": 91, "revenue": 300},  # Q3
    ]
    
    previous_fy_facts = [
        {"date": "2024-12-31", "duration": 365, "revenue": 1000}
    ]
    
    previous_ytd_facts = [
        {"date": "2024-09-30", "duration": 273, "revenue": 700},
        {"date": "2024-09-30", "duration": 91, "revenue": 250}
    ]
    
    ltm_result = calc.calculate_ltm_facts(current_facts, previous_fy_facts, previous_ytd_facts)
    
    # Should use the 273 day periods
    assert ltm_result["revenue"] == 900 + 1000 - 700
