from typing import Any, Optional


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

    def beta(self) -> Optional[float]:
        """Stock beta from profile."""
        return self.profile.get("beta")

    def market_cap(self) -> Optional[float]:
        """Market capitalization from profile."""
        return self.profile.get("mktCap")

    def total_debt(self) -> Optional[float]:
        """Total debt from balance sheet."""
        return self._get_latest(self.balance_sheet, "totalDebt")

    def cash(self) -> Optional[float]:
        """Cash and equivalents from balance sheet."""
        return self._get_latest(self.balance_sheet, "cashAndCashEquivalents")

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
        """
        interest_expense = self._get_latest(self.income_statement, "interestExpense")
        total_debt = self.total_debt()

        if interest_expense is None or total_debt is None:
            return None
        if total_debt == 0:
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

