import pytest
from unittest.mock import MagicMock
from app.services.data_extractor import DataExtractor
from app.services.financial_audit import FinancialAuditService

@pytest.fixture
def mock_extractor():
    extractor = MagicMock(spec=DataExtractor)
    # Default mock values for common metrics to avoid None issues in tests
    extractor.net_income.return_value = 100
    extractor.cash_flow_from_operations.return_value = 120
    extractor.total_assets.return_value = 1000
    extractor.total_liabilities.return_value = 500
    extractor.total_current_liabilities.return_value = 200
    extractor.market_cap.return_value = 1500
    extractor.latest_revenue.return_value = 1000
    extractor.latest_operating_income.return_value = 150
    extractor.latest_working_capital.return_value = 200
    extractor.retained_earnings.return_value = 300
    extractor.accounts_receivable.return_value = 150
    extractor.account_payables.return_value = 100
    extractor.inventory.return_value = 50
    extractor.current_assets.return_value = 400
    extractor.ppe.return_value = 300
    extractor.goodwill.return_value = 50
    extractor.intangible_assets.return_value = 20
    extractor.cash.return_value = 50
    extractor.total_debt.return_value = 300
    extractor.free_cash_flow.return_value = 80
    
    # History mocks (return lists, oldest first)
    extractor.revenue_history.return_value = [900, 1000]
    
    def mock_get_ttm(statements, key):
        if key == "interestExpense": return 10
        if key == "costOfRevenue": return 600
        if key == "depreciationAndAmortization": return 50
        if key == "stockBasedCompensation": return 20
        return None
        
    extractor._get_ttm.side_effect = mock_get_ttm
    
    extractor.get_full_history.side_effect = lambda statement, metric: {
        ("balance_sheet", "netReceivables"): [100, 150],
        ("income_statement", "grossProfitRatio"): [0.3, 0.35],
        ("cash_flow", "stockBasedCompensation"): [10, 15],
        ("cash_flow", "dividendsPaid"): [5, 5],
        ("income_statement", "researchAndDevelopment"): [100, 110, 120, 130, 140, 150],
    }.get((statement, metric), [])
    extractor.capex_history.return_value = [30, 40]
    extractor.da_history.return_value = [20, 25]
    
    # Statement access
    extractor.income_statement = [{"period": "TTM", "interestExpense": 10, "costOfRevenue": 600}]
    extractor.cash_flow = [{"period": "TTM", "depreciationAndAmortization": 50, "stockBasedCompensation": 20}]
    extractor.balance_sheet = [{"period": "FY"}]

    return extractor

def test_calculate_ratios(mock_extractor):
    auditor = FinancialAuditService(mock_extractor)
    ratios = auditor.calculate_ratios()
    
    assert "liquidity" in ratios
    assert "solvency" in ratios
    assert "efficiency" in ratios
    assert "profitability" in ratios
    assert ratios["liquidity"]["current_ratio"] == 2.0 # 400 / 200

def test_accounting_corrections(mock_extractor):
    auditor = FinancialAuditService(mock_extractor)
    corrections = auditor.get_accounting_corrections()
    
    assert len(corrections) > 0
    assert any("R&D Capitalization" in c["name"] for c in corrections)
    assert corrections[0]["impact_on_ebit"] > 0

def test_sloan_ratio_calculation(mock_extractor):
    # Set up mock data: (Net Income 150 - OCF 50) / Total Assets 1000 = 0.10
    mock_extractor.net_income.return_value = 150
    mock_extractor.cash_flow_from_operations.return_value = 50
    mock_extractor.total_assets.return_value = 1000
    
    auditor = FinancialAuditService(mock_extractor)
    assert auditor.sloan_ratio() == 0.10

def test_altman_z_score_calculation(mock_extractor):
    # Mock all components for Altman Z-Score
    mock_extractor.total_assets.return_value = 1000
    mock_extractor.total_liabilities.return_value = 500
    mock_extractor.market_cap.return_value = 2000
    mock_extractor.latest_revenue.return_value = 1500
    mock_extractor.latest_operating_income.return_value = 200
    mock_extractor.latest_working_capital.return_value = 300
    mock_extractor.retained_earnings.return_value = 400
    
    auditor = FinancialAuditService(mock_extractor)
    result = auditor.altman_z_score()
    
    assert result["score"] > 0
    assert result["zone"] in ["Safe", "Gray", "Distress"]
    assert "A" in result["components"]

def test_beneish_m_score_insufficient_history(mock_extractor):
    # Less than 2 years of revenue history
    mock_extractor.revenue_history.return_value = [1000]
    
    auditor = FinancialAuditService(mock_extractor)
    assert auditor.beneish_m_score() is None

def test_analyze_statements_summary(mock_extractor):
    # Set up mock data for high-risk scenario
    mock_extractor.net_income.return_value = 200
    mock_extractor.cash_flow_from_operations.return_value = 50
    mock_extractor.total_assets.return_value = 500 # Sloan = 0.30 (High)
    
    mock_extractor.total_liabilities.return_value = 1000
    mock_extractor.market_cap.return_value = 100
    mock_extractor.latest_revenue.return_value = 500
    mock_extractor.latest_operating_income.return_value = -50
    mock_extractor.latest_working_capital.return_value = -100
    mock_extractor.retained_earnings.return_value = -200 # Altman will be low
    
    auditor = FinancialAuditService(mock_extractor)
    results = auditor.analyze_statements()
    
    assert "liquidity_ratios" in results
    assert "accounting_corrections" in results
    assert len(results["quantitative_findings"]) > 0
    assert any("Sloan" in f for f in results["quantitative_findings"])
