import pytest
from app.services.data_extractor import DataExtractor


class TestDataExtractor:
    def test_extract_beta(self):
        """Extract beta from profile data."""
        data = {
            "profile": {"beta": 1.25},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.beta() == 1.25

    def test_extract_market_cap(self):
        """Extract market cap from profile data."""
        data = {
            "profile": {"mktCap": 3000000000000},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.market_cap() == 3000000000000

    def test_extract_total_debt(self):
        """Extract total debt from balance sheet."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{"totalDebt": 100000000000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.total_debt() == 100000000000

    def test_extract_cash(self):
        """Extract cash from balance sheet."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [{"cashAndCashEquivalents": 50000000000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.cash() == 50000000000

    def test_extract_tax_rate(self):
        """Calculate effective tax rate from income statement."""
        data = {
            "profile": {},
            "income_statement": [
                {"incomeTaxExpense": 25000000, "incomeBeforeTax": 100000000}
            ],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        # 25M / 100M = 0.25 (25%)
        assert abs(extractor.tax_rate() - 0.25) < 0.001

    def test_extract_cost_of_debt(self):
        """Calculate cost of debt from interest expense and total debt."""
        data = {
            "profile": {},
            "income_statement": [{"interestExpense": 5000000}],
            "balance_sheet": [{"totalDebt": 100000000}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        # 5M / 100M = 0.05 (5%)
        assert abs(extractor.cost_of_debt() - 0.05) < 0.001

    def test_extract_fcf(self):
        """Extract free cash flow from cash flow statement."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [{"freeCashFlow": 99000000000}],
        }
        extractor = DataExtractor(data)
        assert extractor.free_cash_flow() == 99000000000

    def test_extract_shares_outstanding(self):
        """Extract shares outstanding from income statement."""
        data = {
            "profile": {},
            "income_statement": [{"weightedAverageShsOut": 15500000000}],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.shares_outstanding() == 15500000000

    def test_handles_missing_data_gracefully(self):
        """Return None for missing data instead of crashing."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.beta() is None
        assert extractor.total_debt() is None

    def test_handles_zero_debt_for_cost_of_debt(self):
        """Cost of debt should be 0 if no debt."""
        data = {
            "profile": {},
            "income_statement": [{"interestExpense": 0}],
            "balance_sheet": [{"totalDebt": 0}],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.cost_of_debt() == 0.0

    def test_market_risk_premium_default(self):
        """Market risk premium defaults to 6%."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data)
        assert extractor.market_risk_premium() == 0.06

    def test_market_risk_premium_override(self):
        """User can override market risk premium."""
        data = {
            "profile": {},
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
        }
        extractor = DataExtractor(data, market_risk_premium=0.07)
        assert extractor.market_risk_premium() == 0.07

