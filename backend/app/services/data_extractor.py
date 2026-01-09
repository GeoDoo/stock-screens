from typing import Any, List, Optional
from app.constants import DEFAULT_MARKET_RISK_PREMIUM, DEFAULT_TREASURY_RATE, DEFAULT_CREDIT_SPREAD


class DataExtractor:
    """
    Extracts financial metrics from FMP data for use in valuation models.
    """

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
        """
        Latest Non-Cash Working Capital for DCF analysis.
        
        Formula: (Current Assets - Cash) - (Current Liabilities - Short-term Debt)
        
        Why Non-Cash:
        - Cash is added back separately (EV → Equity Value)
        - Short-term debt is financing, not operating
        - Including them double-counts and distorts FCF projections
        """
        current_assets = self._get_latest(self.balance_sheet, "totalCurrentAssets")
        current_liabilities = self._get_latest(self.balance_sheet, "totalCurrentLiabilities")
        if current_assets is None or current_liabilities is None:
            return None
        
        # Exclude cash from current assets (treat missing as 0)
        cash = self._get_latest(self.balance_sheet, "cashAndCashEquivalents") or 0
        
        # Exclude short-term debt from current liabilities (treat missing as 0)
        short_term_debt = self._get_latest(self.balance_sheet, "shortTermDebt") or 0
        
        non_cash_current_assets = current_assets - cash
        operating_current_liabilities = current_liabilities - short_term_debt
        
        return non_cash_current_assets - operating_current_liabilities

    def tax_rate(self) -> Optional[float]:
        """
        Effective tax rate using multi-year average for stability.
        
        Effective tax rates are notoriously volatile due to one-time items:
        - R&D tax credits
        - Foreign tax adjustments  
        - Deferred tax benefits/charges
        - One-time restructuring charges
        
        Using a single year can badly distort 10-year FCF projections.
        We use a 3-year average, excluding:
        - Years with negative income (loss years)
        - Years with extreme rates (< 0% or > 50%)
        """
        valid_rates = []
        
        for statement in self.income_statement[:3]:  # Up to 3 years
            tax_expense = statement.get("incomeTaxExpense")
            income_before_tax = statement.get("incomeBeforeTax")
            
            if tax_expense is None or income_before_tax is None:
                continue
            if income_before_tax <= 0:  # Skip loss years
                continue
                
            rate = tax_expense / income_before_tax
            
            # Skip extreme outliers (< 0% or > 50%)
            if rate < 0 or rate > 0.50:
                continue
                
            valid_rates.append(rate)
        
        if not valid_rates:
            # Fallback: try latest year even if extreme rate, but still require positive income
            tax_expense = self._get_latest(self.income_statement, "incomeTaxExpense")
            income_before_tax = self._get_latest(self.income_statement, "incomeBeforeTax")
            if tax_expense is not None and income_before_tax is not None and income_before_tax > 0:
                return tax_expense / income_before_tax
            return None
        
        return sum(valid_rates) / len(valid_rates)

    def cost_of_debt(self) -> Optional[float]:
        """
        Cost of debt calculated from interest expense and total debt.
        cost_of_debt = interest_expense / total_debt
        
        When interest expense is missing but debt exists, applies a conservative
        floor (risk-free rate + credit spread) to avoid understating WACC.
        """
        interest_expense = self._get_latest(self.income_statement, "interestExpense")
        total_debt = self.total_debt()

        if total_debt is None:
            return None
        if total_debt == 0:
            return 0.0  # No debt, no cost
        if interest_expense is None or interest_expense <= 0:
            # Company has debt but no/negative interest expense reported
            # (e.g., interest income exceeds expense, or data is missing)
            # Apply conservative floor: risk-free rate + credit spread
            # This prevents artificially low WACC that inflates valuations
            return DEFAULT_TREASURY_RATE + DEFAULT_CREDIT_SPREAD
        
        calculated_rate = interest_expense / total_debt
        
        # Apply floor to prevent unrealistically low cost of debt
        floor_rate = DEFAULT_TREASURY_RATE + DEFAULT_CREDIT_SPREAD
        return max(calculated_rate, floor_rate)

    def free_cash_flow(self) -> Optional[float]:
        """Free cash flow from cash flow statement."""
        return self._get_latest(self.cash_flow, "freeCashFlow")

    def diluted_shares_outstanding(self) -> Optional[float]:
        """
        Fully Diluted Shares Outstanding (FDSO) from income statement.
        
        FDSO includes the dilutive effect of:
        - Stock options
        - RSUs (Restricted Stock Units)
        - Convertible securities
        
        Returns None if diluted shares not available.
        """
        return self._get_latest(self.income_statement, "weightedAverageShsOutDil")
    
    def shares_outstanding(self) -> Optional[float]:
        """
        Shares outstanding for valuation - prefers diluted over basic.
        
        Priority:
        1. Diluted shares from income statement (FDSO)
        2. Basic shares from income statement
        3. Shares from company profile (last resort)
        
        Professional DCF always uses diluted shares to account for
        future dilution from options, RSUs, and convertibles.
        Using basic shares OVERVALUES the company.
        """
        # First try: diluted shares (preferred for DCF)
        diluted = self._get_latest(self.income_statement, "weightedAverageShsOutDil")
        if diluted is not None:
            return diluted
        
        # Fallback: basic shares from income statement
        basic = self._get_latest(self.income_statement, "weightedAverageShsOut")
        if basic is not None:
            return basic
        
        # Last resort: profile shares (less accurate, but better than nothing)
        return self.profile.get("sharesOutstanding")
    
    def shares_outstanding_type(self) -> str:
        """
        Returns the source of shares used for valuation transparency.
        
        Returns:
            'diluted' - Fully Diluted Shares from income statement (preferred)
            'basic' - Basic shares from income statement
            'profile' - Shares from company profile (least accurate)
        """
        if self._get_latest(self.income_statement, "weightedAverageShsOutDil") is not None:
            return "diluted"
        if self._get_latest(self.income_statement, "weightedAverageShsOut") is not None:
            return "basic"
        return "profile"

    def market_risk_premium(self) -> float:
        """
        Market risk premium (expected market return - risk free rate).
        
        This is an assumption, not data. Historical average is ~6%.
        User can override via constructor.
        """
        if self._market_risk_premium is not None:
            return self._market_risk_premium
        return DEFAULT_MARKET_RISK_PREMIUM

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
        Historical Non-Cash Working Capital (oldest first).
        
        NCWC = (Current Assets - Cash) - (Current Liabilities - Short-term Debt)
        
        Uses same Non-Cash formula as latest_working_capital() for consistency.
        """
        if not self.balance_sheet:
            return []
        
        wc_values = []
        for bs in reversed(self.balance_sheet):
            current_assets = bs.get("totalCurrentAssets", 0) or 0
            current_liabilities = bs.get("totalCurrentLiabilities", 0) or 0
            cash = bs.get("cashAndCashEquivalents", 0) or 0
            short_term_debt = bs.get("shortTermDebt", 0) or 0
            
            # Non-Cash Working Capital
            non_cash_current_assets = current_assets - cash
            operating_current_liabilities = current_liabilities - short_term_debt
            ncwc = non_cash_current_assets - operating_current_liabilities
            
            wc_values.append(ncwc)
        return wc_values

