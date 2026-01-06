import pytest
from app.services.data_adapter import stock_data_to_legacy
from app.services.base_provider import StockData, CompanyProfile, FinancialStatement


class TestDataAdapter:
    @pytest.fixture
    def sample_stock_data(self):
        """Create sample StockData for testing."""
        return StockData(
            profile=CompanyProfile(
                symbol="AAPL",
                name="Apple Inc.",
                price=190.0,
                market_cap=3000000000000,
                beta=1.25,
                shares_outstanding=15744231000,
                currency="USD",
                exchange="NASDAQ",
                industry="Consumer Electronics",
                sector="Technology",
            ),
            financials=[
                FinancialStatement(
                    date="2024-01-01",
                    period="annual",
                    revenue=383285000000,
                    cost_of_revenue=214137000000,
                    gross_profit=169148000000,
                    operating_income=114301000000,
                    net_income=96995000000,
                    interest_expense=3933000000,
                    income_tax_expense=16741000000,
                    total_assets=352583000000,
                    total_liabilities=290437000000,
                    total_equity=62146000000,
                    total_debt=111088000000,
                    cash_and_equivalents=29965000000,
                    current_assets=143566000000,
                    current_liabilities=145308000000,
                    operating_cash_flow=110543000000,
                    capital_expenditure=-10959000000,
                    free_cash_flow=99584000000,
                    depreciation_amortization=11519000000,
                ),
            ],
            provider="fmp",
        )

    def test_converts_profile_correctly(self, sample_stock_data):
        """Profile data should be converted to legacy format."""
        result = stock_data_to_legacy(sample_stock_data)
        
        assert result["profile"]["symbol"] == "AAPL"
        assert result["profile"]["companyName"] == "Apple Inc."
        assert result["profile"]["price"] == 190.0
        assert result["profile"]["marketCap"] == 3000000000000
        assert result["profile"]["beta"] == 1.25
        assert result["profile"]["sharesOutstanding"] == 15744231000
        assert result["profile"]["industry"] == "Consumer Electronics"
        assert result["profile"]["sector"] == "Technology"

    def test_converts_income_statement(self, sample_stock_data):
        """Income statement data should be converted."""
        result = stock_data_to_legacy(sample_stock_data)
        
        assert len(result["income_statement"]) == 1
        income = result["income_statement"][0]
        
        assert income["revenue"] == 383285000000
        assert income["operatingIncome"] == 114301000000
        assert income["netIncome"] == 96995000000
        assert income["interestExpense"] == 3933000000
        assert income["incomeTaxExpense"] == 16741000000
        assert income["date"] == "2024-01-01"
        assert income["period"] == "FY"

    def test_converts_balance_sheet(self, sample_stock_data):
        """Balance sheet data should be converted."""
        result = stock_data_to_legacy(sample_stock_data)
        
        assert len(result["balance_sheet"]) == 1
        balance = result["balance_sheet"][0]
        
        assert balance["totalDebt"] == 111088000000
        assert balance["cashAndCashEquivalents"] == 29965000000
        assert balance["totalAssets"] == 352583000000
        assert balance["totalLiabilities"] == 290437000000

    def test_converts_cash_flow(self, sample_stock_data):
        """Cash flow data should be converted."""
        result = stock_data_to_legacy(sample_stock_data)
        
        assert len(result["cash_flow"]) == 1
        cf = result["cash_flow"][0]
        
        assert cf["freeCashFlow"] == 99584000000
        assert cf["capitalExpenditure"] == -10959000000
        assert cf["operatingCashFlow"] == 110543000000
        assert cf["depreciationAndAmortization"] == 11519000000

    def test_calculates_income_before_tax(self, sample_stock_data):
        """Should calculate incomeBeforeTax from net_income + tax_expense."""
        result = stock_data_to_legacy(sample_stock_data)
        income = result["income_statement"][0]
        
        expected = 96995000000 + 16741000000  # net_income + tax
        assert income["incomeBeforeTax"] == expected

    def test_handles_quarterly_period(self):
        """Quarterly data should have 'Q' period."""
        stock_data = StockData(
            profile=CompanyProfile(
                symbol="TEST", name="Test", price=100, market_cap=1000,
                beta=1.0, shares_outstanding=100, currency="USD",
            ),
            financials=[
                FinancialStatement(
                    date="2024-Q1",
                    period="quarterly",  # quarterly
                    revenue=100000000,
                ),
            ],
            provider="test",
        )
        
        result = stock_data_to_legacy(stock_data)
        assert result["income_statement"][0]["period"] == "Q"

    def test_handles_multiple_financials(self):
        """Should handle multiple years of financial data."""
        stock_data = StockData(
            profile=CompanyProfile(
                symbol="TEST", name="Test", price=100, market_cap=1000,
                beta=1.0, shares_outstanding=100, currency="USD",
            ),
            financials=[
                FinancialStatement(date="2024", period="annual", revenue=300),
                FinancialStatement(date="2023", period="annual", revenue=250),
                FinancialStatement(date="2022", period="annual", revenue=200),
            ],
            provider="test",
        )
        
        result = stock_data_to_legacy(stock_data)
        
        assert len(result["income_statement"]) == 3
        assert len(result["balance_sheet"]) == 3
        assert len(result["cash_flow"]) == 3

    def test_handles_none_values(self):
        """Should handle None values in financial data."""
        stock_data = StockData(
            profile=CompanyProfile(
                symbol="TEST", name="Test", price=100, market_cap=1000,
                beta=None,  # None value
                shares_outstanding=100, currency="USD",
            ),
            financials=[
                FinancialStatement(
                    date="2024",
                    period="annual",
                    revenue=100000000,
                    net_income=None,  # None value
                    income_tax_expense=None,  # None value
                ),
            ],
            provider="test",
        )
        
        result = stock_data_to_legacy(stock_data)
        
        assert result["profile"]["beta"] is None
        assert result["income_statement"][0]["netIncome"] is None
        assert result["income_statement"][0]["incomeBeforeTax"] is None

    def test_empty_financials(self):
        """Should handle empty financials list."""
        stock_data = StockData(
            profile=CompanyProfile(
                symbol="TEST", name="Test", price=100, market_cap=1000,
                beta=1.0, shares_outstanding=100, currency="USD",
            ),
            financials=[],
            provider="test",
        )
        
        result = stock_data_to_legacy(stock_data)
        
        assert result["income_statement"] == []
        assert result["balance_sheet"] == []
        assert result["cash_flow"] == []

