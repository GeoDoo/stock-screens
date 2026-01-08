from typing import Any, List, Optional


class DataExtractor:
    """
    Extracts financial metrics from FMP data for use in valuation models.
    """

    # Default market risk premium (historical average ~6%)
    DEFAULT_MARKET_RISK_PREMIUM = 0.06

    def __init__(self, data: dict, market_risk_premium: float = None):
        self.profile = data.get("profile", {})
        self.income_statement = data.get("income_statement", [])
        self.balance_sheet = data.get("balance_sheet", [])
        self.cash_flow = data.get("cash_flow", [])
        self._market_risk_premium = market_risk_premium

    def _get_latest(self, statements: list, key: str) -> Optional[Any]:
        """Get value from most recent statement."""
        if not statements:
            return None
        return statements[0].get(key)

    def _get_history(self, statements: list, key: str) -> List[float]:
        """Get historical values (oldest first for CAGR calculation)."""
        if not statements:
            return []
        values = [s.get(key) for s in reversed(statements) if s.get(key) is not None]
        return values

    def beta(self) -> Optional[float]:
        """Stock beta from profile."""
        return self.profile.get("beta")

    def market_cap(self) -> Optional[float]:
        """Market capitalization from profile."""
        return self.profile.get("marketCap")

    def total_debt(self) -> Optional[float]:
        """Total debt from balance sheet."""
        return self._get_latest(self.balance_sheet, "totalDebt")

    def total_equity(self) -> Optional[float]:
        """Total stockholders equity from balance sheet."""
        return self._get_latest(self.balance_sheet, "totalStockholdersEquity")

    def cash(self) -> Optional[float]:
        """Cash and equivalents from balance sheet."""
        return self._get_latest(self.balance_sheet, "cashAndCashEquivalents")
    
    def latest_revenue(self) -> Optional[float]:
        """Latest revenue from income statement."""
        return self._get_latest(self.income_statement, "revenue")
    
    def latest_working_capital(self) -> Optional[float]:
        """Latest working capital (current assets - current liabilities)."""
        current_assets = self._get_latest(self.balance_sheet, "totalCurrentAssets")
        current_liabilities = self._get_latest(self.balance_sheet, "totalCurrentLiabilities")
        if current_assets is None or current_liabilities is None:
            return None
        return current_assets - current_liabilities

    def tax_rate(self) -> Optional[float]:
        """
        Effective tax rate calculated from income statement.
        tax_rate = income_tax_expense / income_before_tax
        """
        tax_expense = self._get_latest(self.income_statement, "incomeTaxExpense")
        income_before_tax = self._get_latest(self.income_statement, "incomeBeforeTax")

        if tax_expense is None or income_before_tax is None:
            return None
        if income_before_tax == 0:
            return 0.0

        return tax_expense / income_before_tax

    def cost_of_debt(self) -> Optional[float]:
        """
        Cost of debt calculated from interest expense and total debt.
        cost_of_debt = interest_expense / total_debt
        
        For companies with no interest expense reported (e.g., Apple has more 
        interest income than expense), returns 0.0 if they have debt.
        """
        interest_expense = self._get_latest(self.income_statement, "interestExpense")
        total_debt = self.total_debt()

        if total_debt is None:
            return None
        if total_debt == 0:
            return 0.0  # No debt, no cost
        if interest_expense is None:
            # Company has debt but no interest expense reported
            # (e.g., interest income exceeds expense, or data is missing)
            # Return 0.0 as they effectively have no net borrowing cost
            return 0.0

        return interest_expense / total_debt

    def free_cash_flow(self) -> Optional[float]:
        """Free cash flow from cash flow statement."""
        return self._get_latest(self.cash_flow, "freeCashFlow")

    def shares_outstanding(self) -> Optional[float]:
        """Weighted average shares outstanding from income statement."""
        return self._get_latest(self.income_statement, "weightedAverageShsOut")

    def market_risk_premium(self) -> float:
        """
        Market risk premium (expected market return - risk free rate).
        
        This is an assumption, not data. Historical average is ~6%.
        User can override via constructor.
        """
        if self._market_risk_premium is not None:
            return self._market_risk_premium
        return self.DEFAULT_MARKET_RISK_PREMIUM

    # Historical data for FCF projections
    def revenue_history(self) -> List[float]:
        """Historical revenue (oldest first)."""
        return self._get_history(self.income_statement, "revenue")

    def ebit_history(self) -> List[float]:
        """Historical EBIT / operating income (oldest first)."""
        return self._get_history(self.income_statement, "operatingIncome")

    def da_history(self) -> List[float]:
        """Historical depreciation & amortization (oldest first)."""
        return self._get_history(self.cash_flow, "depreciationAndAmortization")

    def capex_history(self) -> List[float]:
        """Historical capital expenditures (oldest first)."""
        # CapEx is usually negative in cash flow, we want positive values
        values = self._get_history(self.cash_flow, "capitalExpenditure")
        return [abs(v) for v in values]

    def working_capital_history(self) -> List[float]:
        """
        Historical working capital (oldest first).
        WC = Current Assets - Current Liabilities
        """
        if not self.balance_sheet:
            return []
        
        wc_values = []
        for bs in reversed(self.balance_sheet):
            current_assets = bs.get("totalCurrentAssets", 0) or 0
            current_liabilities = bs.get("totalCurrentLiabilities", 0) or 0
            wc_values.append(current_assets - current_liabilities)
        return wc_values

