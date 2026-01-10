from dataclasses import dataclass
from typing import Any, List, Optional, Tuple
from app.constants import DEFAULT_MARKET_RISK_PREMIUM, DEFAULT_TREASURY_RATE, DEFAULT_CREDIT_SPREAD


@dataclass
class ProvenanceInfo:
    """
    Tracks the source/derivation of a financial metric.
    
    Institutional-grade transparency: analysts need to know whether
    a value comes from TTM data, annual averages, or fallbacks.
    """
    source: str  # e.g., "ttm", "fy_average", "fallback", "calculated"
    description: str  # Human-readable explanation
    confidence: str = "high"  # "high", "medium", "low"
    
    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "description": self.description,
            "confidence": self.confidence,
        }


# Synthetic Credit Rating Spread Table
# Based on Damodaran's synthetic rating methodology
# ICR thresholds → Credit Rating → Spread over risk-free rate
# Sources: Historical corporate bond spreads, updated for current market conditions
SYNTHETIC_RATING_TABLE: List[Tuple[float, str, float]] = [
    # (min_icr, rating, spread)
    (12.5, "AAA", 0.0063),   # 0.63% spread
    (9.5, "AA", 0.0078),     # 0.78% spread  
    (7.5, "A+", 0.0098),     # 0.98% spread
    (6.0, "A", 0.0108),      # 1.08% spread
    (4.5, "A-", 0.0122),     # 1.22% spread
    (4.0, "BBB+", 0.0156),   # 1.56% spread
    (3.5, "BBB", 0.0175),    # 1.75% spread
    (3.0, "BBB-", 0.0200),   # 2.00% spread
    (2.5, "BB+", 0.0250),    # 2.50% spread
    (2.0, "BB", 0.0325),     # 3.25% spread
    (1.5, "BB-", 0.0400),    # 4.00% spread
    (1.25, "B+", 0.0475),    # 4.75% spread
    (1.0, "B", 0.0550),      # 5.50% spread
    (0.8, "B-", 0.0650),     # 6.50% spread
    (0.5, "CCC", 0.0850),    # 8.50% spread
    (0.0, "CC", 0.1100),     # 11.00% spread
    (-999, "D", 0.1500),     # 15.00% spread (distressed/default)
]


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
    
    def _get_ttm(self, statements: list, key: str) -> Optional[Any]:
        """
        Get value preferring TTM (Trailing Twelve Months) data.
        
        For flow items (revenue, income, cash flow), TTM is more current
        than the last annual report, which can be 9+ months stale.
        
        Returns TTM value if available, otherwise falls back to latest.
        """
        if not statements:
            return None
        
        # Look for TTM/LTM record first
        for stmt in statements:
            period = stmt.get("period", "").upper()
            if period in ("TTM", "LTM"):
                val = stmt.get(key)
                if val is not None:
                    return val
        
        # Fallback to most recent (annual)
        return statements[0].get(key)
    
    def is_using_ltm(self) -> bool:
        """
        Check if LTM/TTM data is available for flow items.
        
        Returns True if the most recent income statement is TTM/LTM period.
        This indicates we're using current (rolling 12 month) data
        rather than potentially stale annual data.
        """
        if not self.income_statement:
            return False
        period = self.income_statement[0].get("period", "").upper()
        return period in ("TTM", "LTM")

    def _is_annual_period(self, statement: dict) -> bool:
        """
        Check if a statement is from an annual (fiscal year) period.
        
        Excludes:
        - TTM/LTM (trailing twelve months - overlaps with annual)
        - Quarterly (Q1, Q2, Q3, Q4 - partial year)
        
        Includes:
        - FY, annual, or no period specified (treated as annual)
        """
        period = statement.get("period", "").upper()
        
        # Explicitly exclude TTM/LTM
        if period in ("TTM", "LTM"):
            return False
        
        # Exclude quarterly periods
        if period.startswith("Q") and len(period) <= 3:  # Q1, Q2, Q3, Q4
            return False
        
        # Everything else (FY, annual, empty) is treated as annual
        return True
    
    def _get_history(self, statements: list, key: str) -> List[float]:
        """
        Get historical annual values (oldest first for CAGR calculation).
        
        IMPORTANT: This excludes TTM/LTM and quarterly data to prevent
        invalid CAGR calculations. TTM data overlaps with the most recent
        fiscal year, which would distort year-over-year growth calculations.
        
        For current period data (including TTM), use _get_ttm() instead.
        """
        if not statements:
            return []
        
        # Filter to annual-only and get values
        annual_statements = [s for s in statements if self._is_annual_period(s)]
        values = [s.get(key) for s in reversed(annual_statements) if s.get(key) is not None]
        return values

    def beta(self) -> Optional[float]:
        """Stock beta from profile."""
        return self.profile.get("beta")

    def market_cap(self) -> Optional[float]:
        """Market capitalization from profile."""
        return self.profile.get("marketCap")

    def sector(self) -> Optional[str]:
        """Company sector from profile (e.g., 'Technology', 'Financial Services')."""
        return self.profile.get("sector")

    def industry(self) -> Optional[str]:
        """Company industry from profile (e.g., 'Software—Application', 'Banks—Regional')."""
        return self.profile.get("industry")

    def total_debt(self) -> Optional[float]:
        """Total debt from balance sheet."""
        return self._get_latest(self.balance_sheet, "totalDebt")

    def total_equity(self) -> Optional[float]:
        """Total stockholders equity from balance sheet."""
        return self._get_latest(self.balance_sheet, "totalStockholdersEquity")

    def cash(self) -> Optional[float]:
        """Cash and equivalents from balance sheet."""
        return self._get_latest(self.balance_sheet, "cashAndCashEquivalents")
    
    # Equity Bridge components (institutional-grade)
    def minority_interest(self) -> Optional[float]:
        """Non-controlling interest - subtract from equity value."""
        return self._get_latest(self.balance_sheet, "minorityInterest")
    
    def preferred_stock(self) -> Optional[float]:
        """Preferred stock - sits above common equity, subtract from common."""
        return self._get_latest(self.balance_sheet, "preferredStock")
    
    def deferred_tax_assets(self) -> Optional[float]:
        """Deferred tax assets (NOLs/tax shields) - add to equity value."""
        return self._get_latest(self.balance_sheet, "deferredTaxAssets")
    
    def pension_liability(self) -> Optional[float]:
        """Underfunded pension obligations - debt-like, subtract from equity."""
        return self._get_latest(self.balance_sheet, "pensionLiability")
    
    def latest_revenue(self) -> Optional[float]:
        """
        Latest revenue, preferring TTM over annual data.
        
        TTM (Trailing Twelve Months) is more current than the last fiscal year,
        which can be 9+ months stale. This is important for valuation because
        it gives the most current view of the company's revenue run-rate.
        """
        return self._get_ttm(self.income_statement, "revenue")
    
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
        Effective tax rate, preferring TTM data when available.
        
        If TTM data is available and valid, use it directly (most current).
        Otherwise, use 3-year average for stability.
        
        Effective tax rates are notoriously volatile due to one-time items:
        - R&D tax credits
        - Foreign tax adjustments  
        - Deferred tax benefits/charges
        - One-time restructuring charges
        """
        # Check for TTM data first (most current)
        # Only use TTM if there's an actual TTM record (not fallback)
        if self.is_using_ltm():
            ttm_tax = self._get_ttm(self.income_statement, "incomeTaxExpense")
            ttm_income = self._get_ttm(self.income_statement, "incomeBeforeTax")
            
            if ttm_tax is not None and ttm_income is not None and ttm_income > 0:
                rate = ttm_tax / ttm_income
                # Only use TTM if it's reasonable (0% to 50%)
                if 0 <= rate <= 0.50:
                    return rate
        
        # Fallback to multi-year average using ANNUAL data only
        valid_rates = []
        annual_count = 0
        
        for statement in self.income_statement:
            # Skip non-annual periods (TTM, LTM, quarterly)
            if not self._is_annual_period(statement):
                continue
            
            annual_count += 1
            if annual_count > 3:  # Limit to 3 years
                break
                
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

    def tax_rate_with_provenance(self) -> Tuple[Optional[float], ProvenanceInfo]:
        """
        Get tax rate with provenance information.
        
        Returns:
            Tuple of (tax_rate, provenance_info)
        """
        # Check for TTM data first (most current)
        if self.is_using_ltm():
            ttm_tax = self._get_ttm(self.income_statement, "incomeTaxExpense")
            ttm_income = self._get_ttm(self.income_statement, "incomeBeforeTax")
            
            if ttm_tax is not None and ttm_income is not None and ttm_income > 0:
                rate = ttm_tax / ttm_income
                if 0 <= rate <= 0.50:
                    return (rate, ProvenanceInfo(
                        source="ttm",
                        description="Trailing 12-month effective tax rate",
                        confidence="high"
                    ))
        
        # Fallback to multi-year average
        valid_rates = []
        annual_count = 0
        years_used = []
        
        for statement in self.income_statement:
            if not self._is_annual_period(statement):
                continue
            
            annual_count += 1
            if annual_count > 3:
                break
                
            tax_expense = statement.get("incomeTaxExpense")
            income_before_tax = statement.get("incomeBeforeTax")
            
            if tax_expense is None or income_before_tax is None:
                continue
            if income_before_tax <= 0:
                continue
                
            rate = tax_expense / income_before_tax
            if rate < 0 or rate > 0.50:
                continue
                
            valid_rates.append(rate)
            years_used.append(statement.get("date", "unknown")[:4])
        
        if valid_rates:
            avg_rate = sum(valid_rates) / len(valid_rates)
            return (avg_rate, ProvenanceInfo(
                source="fy_average",
                description=f"{len(valid_rates)}-year average ({', '.join(years_used)})",
                confidence="medium" if len(valid_rates) >= 2 else "low"
            ))
        
        # Last resort fallback
        tax_expense = self._get_latest(self.income_statement, "incomeTaxExpense")
        income_before_tax = self._get_latest(self.income_statement, "incomeBeforeTax")
        if tax_expense is not None and income_before_tax is not None and income_before_tax > 0:
            return (tax_expense / income_before_tax, ProvenanceInfo(
                source="fallback",
                description="Latest year only (may include outliers)",
                confidence="low"
            ))
        
        return (None, ProvenanceInfo(
            source="unavailable",
            description="No valid tax rate data available",
            confidence="low"
        ))

    def interest_coverage_ratio(self) -> Optional[float]:
        """
        Interest Coverage Ratio (ICR) = EBIT / Interest Expense.
        
        Key metric for credit analysis:
        - ICR > 10x: Strong investment grade (AAA/AA)
        - ICR 3-6x: Medium investment grade (BBB)  
        - ICR < 1.5x: Below investment grade / distressed
        
        Returns None if either component is missing.
        """
        ebit = self._get_latest(self.income_statement, "operatingIncome")
        interest_expense = self._get_latest(self.income_statement, "interestExpense")
        
        if ebit is None or interest_expense is None:
            return None
        if interest_expense <= 0:
            # Can't calculate ratio with zero/negative interest
            # This could mean net interest income or data issue
            return None
            
        return ebit / interest_expense
    
    def synthetic_credit_rating(self) -> str:
        """
        Determine synthetic credit rating based on Interest Coverage Ratio.
        
        Uses Damodaran's synthetic rating methodology, mapping ICR to
        credit ratings. This is professional practice when actual credit
        ratings aren't available (which is most companies).
        
        Returns credit rating string (AAA, AA, A, BBB, BB, B, CCC, etc.)
        """
        icr = self.interest_coverage_ratio()
        
        # If ICR can't be calculated, assume conservative BBB-
        if icr is None:
            return "BBB-"
        
        # Walk through table to find matching rating
        for min_icr, rating, _ in SYNTHETIC_RATING_TABLE:
            if icr >= min_icr:
                return rating
        
        # Should never reach here, but fallback to D
        return "D"
    
    def synthetic_credit_spread(self) -> float:
        """
        Get credit spread (over risk-free rate) for synthetic rating.
        
        Returns spread as decimal (e.g., 0.0175 for 1.75%).
        """
        icr = self.interest_coverage_ratio()
        
        # If ICR can't be calculated, use conservative BBB- spread
        if icr is None:
            return 0.0200  # BBB- spread
        
        for min_icr, _, spread in SYNTHETIC_RATING_TABLE:
            if icr >= min_icr:
                return spread
        
        return 0.1500  # D spread (distressed)

    def cost_of_debt(self, risk_free_rate: Optional[float] = None) -> Optional[float]:
        """
        Cost of debt using synthetic credit rating methodology.
        
        Cost of Debt = Risk-Free Rate + Credit Spread
        
        The credit spread is determined by the company's synthetic credit
        rating, which is derived from Interest Coverage Ratio (ICR).
        
        This is more accurate than the naive approach of:
            interest_expense / total_debt
        
        ...because it accounts for the company's actual credit quality,
        not just what they happened to borrow at historically.
        
        Args:
            risk_free_rate: Optional risk-free rate to use. If provided, this
                should be the same rate used in cost of equity (CAPM) to ensure
                consistent capital market assumptions in WACC. If None, falls
                back to DEFAULT_TREASURY_RATE for backward compatibility.
        """
        total_debt = self.total_debt()

        if total_debt is None:
            return None
        if total_debt == 0:
            return 0.0  # No debt, no cost
        
        # Use provided risk-free rate or fall back to default
        rf_rate = risk_free_rate if risk_free_rate is not None else DEFAULT_TREASURY_RATE
        
        # Use synthetic credit rating spread
        spread = self.synthetic_credit_spread()
        synthetic_rate = rf_rate + spread
        
        # Also calculate historical rate as sanity check
        interest_expense = self._get_latest(self.income_statement, "interestExpense")
        historical_rate = None
        if interest_expense and interest_expense > 0:
            historical_rate = interest_expense / total_debt
        
        # Use the HIGHER of synthetic or historical rate
        # This prevents artificially low cost of debt if company
        # borrowed at favorable rates that may not be repeatable
        if historical_rate is not None:
            return max(synthetic_rate, historical_rate)
        
        return synthetic_rate

    def free_cash_flow(self) -> Optional[float]:
        """
        Free cash flow, preferring TTM over annual data.
        
        TTM FCF is more current than the last fiscal year.
        """
        return self._get_ttm(self.cash_flow, "freeCashFlow")

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
    
    def shares_provenance(self) -> ProvenanceInfo:
        """Get provenance info for shares outstanding."""
        share_type = self.shares_outstanding_type()
        if share_type == "diluted":
            return ProvenanceInfo(
                source="diluted",
                description="Fully diluted shares (includes options, RSUs, convertibles)",
                confidence="high"
            )
        elif share_type == "basic":
            return ProvenanceInfo(
                source="basic",
                description="Basic shares (may undercount dilution)",
                confidence="medium"
            )
        return ProvenanceInfo(
            source="profile",
            description="Company profile shares (least accurate)",
            confidence="low"
        )
    
    def get_all_provenance(self) -> dict:
        """
        Get provenance information for all key metrics.
        
        Returns dict with source/confidence for each metric.
        Useful for UI transparency about data quality.
        """
        _, tax_prov = self.tax_rate_with_provenance()
        
        return {
            "tax_rate": tax_prov.to_dict(),
            "shares_outstanding": self.shares_provenance().to_dict(),
            "revenue_source": {
                "source": "ttm" if self.is_using_ltm() else "fy",
                "description": "TTM (trailing 12 months)" if self.is_using_ltm() else "Latest fiscal year",
                "confidence": "high",
            },
            "cost_of_debt": {
                "source": "synthetic",
                "description": f"Synthetic rating ({self.synthetic_credit_rating()}) + historical check",
                "confidence": "high" if self.interest_coverage_ratio() else "medium",
            },
        }

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
        
        Note: Excludes TTM/LTM and quarterly data to ensure valid year-over-year
        comparisons in FCF projections.
        """
        if not self.balance_sheet:
            return []
        
        # Filter to annual-only balance sheets
        annual_sheets = [bs for bs in self.balance_sheet if self._is_annual_period(bs)]
        
        wc_values = []
        for bs in reversed(annual_sheets):
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

