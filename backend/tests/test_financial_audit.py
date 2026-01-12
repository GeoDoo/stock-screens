import pytest
from unittest.mock import MagicMock
from app.services.data_extractor import DataExtractor
from app.services.financial_audit import FinancialAuditService

@pytest.fixture
def mock_extractor():
    extractor = MagicMock(spec=DataExtractor)
    return extractor

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
    
    assert len(results["quantitative_findings"]) > 0
    assert any("Sloan" in f for f in results["quantitative_findings"])
