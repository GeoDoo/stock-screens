"""
Financial Ratio Calculator

Calculates comprehensive financial ratios for a single company.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValuationRatios:
    """Valuation metrics."""
    pe_ratio: Optional[float] = None
    earnings_yield: Optional[float] = None
    ps_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    ev_to_revenue: Optional[float] = None
    peg_ratio: Optional[float] = None


@dataclass
class DividendMetrics:
    """Dividend-related metrics."""
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None


@dataclass
class ProfitabilityRatios:
    """Profitability metrics."""
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    roic: Optional[float] = None
    rotic: Optional[float] = None  # Return on Tangible Invested Capital


@dataclass
class LiquidityRatios:
    """Liquidity and solvency metrics."""
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None


@dataclass
class EfficiencyRatios:
    """Efficiency metrics."""
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None


@dataclass
class FinancialRatios:
    """Complete set of financial ratios."""
    valuation: ValuationRatios
    dividend: DividendMetrics
    profitability: ProfitabilityRatios
    liquidity: LiquidityRatios
    efficiency: EfficiencyRatios


class RatioCalculator:
    """
    Calculates comprehensive financial ratios from stock data.
    
    All ratios are calculated from the provided data dictionary,
    which follows the legacy format from DataExtractor/DataAdapter.
    """
    
    def calculate(self, data: dict) -> FinancialRatios:
        """
        Calculate all financial ratios from stock data.
        
        Args:
            data: Stock data dictionary with profile, income_statement,
                  balance_sheet, and cash_flow keys
                  
        Returns:
            FinancialRatios with all calculated metrics
        """
        profile = data.get("profile", {})
        income_stmt = data.get("income_statement", [{}])[0] if data.get("income_statement") else {}
        balance_sheet = data.get("balance_sheet", [{}])[0] if data.get("balance_sheet") else {}
        cash_flow = data.get("cash_flow", [{}])[0] if data.get("cash_flow") else {}
        
        # Extract key values
        price = profile.get("price")
        market_cap = profile.get("marketCap")
        shares = profile.get("sharesOutstanding")
        
        revenue = income_stmt.get("revenue")
        gross_profit = income_stmt.get("grossProfit")
        operating_income = income_stmt.get("operatingIncome")
        net_income = income_stmt.get("netIncome")
        interest_expense = income_stmt.get("interestExpense")
        income_before_tax = income_stmt.get("incomeBeforeTax")
        cogs = income_stmt.get("costOfRevenue")
        
        # D&A comes from cash_flow, not income_statement
        # (stock_data_to_legacy places it in cash_flow)
        depreciation = cash_flow.get("depreciationAndAmortization") or 0
        
        total_assets = balance_sheet.get("totalAssets")
        current_assets = balance_sheet.get("totalCurrentAssets")
        inventory = balance_sheet.get("inventory") or 0
        current_liabilities = balance_sheet.get("totalCurrentLiabilities")
        total_debt = balance_sheet.get("totalDebt") or 0
        equity = balance_sheet.get("totalStockholdersEquity")
        cash = balance_sheet.get("cashAndCashEquivalents") or 0
        goodwill = balance_sheet.get("goodwill") or 0
        intangibles = balance_sheet.get("intangibleAssets") or 0
        
        dividends_paid = abs(cash_flow.get("dividendsPaid") or 0)
        
        # Calculate Enterprise Value
        ev = None
        if market_cap is not None:
            ev = market_cap + total_debt - cash
        
        # Calculate EBITDA
        ebitda = None
        if operating_income is not None:
            ebitda = operating_income + depreciation
        
        return FinancialRatios(
            valuation=self._calc_valuation(
                price, market_cap, shares, net_income, revenue, equity, ev, ebitda
            ),
            dividend=self._calc_dividend(
                price, shares, dividends_paid, net_income
            ),
            profitability=self._calc_profitability(
                revenue, gross_profit, operating_income, net_income,
                equity, total_assets, total_debt, cash, income_before_tax,
                goodwill, intangibles
            ),
            liquidity=self._calc_liquidity(
                current_assets, current_liabilities, inventory,
                total_debt, equity, operating_income, interest_expense
            ),
            efficiency=self._calc_efficiency(
                revenue, total_assets, cogs, inventory
            ),
        )
    
    def _calc_valuation(
        self,
        price: Optional[float],
        market_cap: Optional[float],
        shares: Optional[float],
        net_income: Optional[float],
        revenue: Optional[float],
        equity: Optional[float],
        ev: Optional[float],
        ebitda: Optional[float],
    ) -> ValuationRatios:
        """Calculate valuation ratios."""
        ratios = ValuationRatios()
        
        # P/E Ratio (only for positive earnings)
        if price and shares and net_income and net_income > 0:
            eps = net_income / shares
            ratios.pe_ratio = price / eps
        
        # Earnings Yield (can be negative for losses)
        if price and shares and net_income:
            eps = net_income / shares
            ratios.earnings_yield = eps / price
        
        # P/S Ratio
        if market_cap and revenue and revenue > 0:
            ratios.ps_ratio = market_cap / revenue
        
        # P/B Ratio
        if market_cap and equity and equity > 0:
            ratios.pb_ratio = market_cap / equity
        
        # EV/EBITDA
        if ev and ebitda and ebitda > 0:
            ratios.ev_to_ebitda = ev / ebitda
        
        # EV/Revenue
        if ev and revenue and revenue > 0:
            ratios.ev_to_revenue = ev / revenue
        
        return ratios
    
    def _calc_dividend(
        self,
        price: Optional[float],
        shares: Optional[float],
        dividends_paid: float,
        net_income: Optional[float],
    ) -> DividendMetrics:
        """Calculate dividend metrics."""
        metrics = DividendMetrics()
        
        # Dividend Yield
        if price and shares and dividends_paid >= 0:
            dps = dividends_paid / shares if shares else 0
            metrics.dividend_yield = dps / price if price else 0
        
        # Payout Ratio
        if net_income and net_income > 0 and dividends_paid >= 0:
            metrics.payout_ratio = dividends_paid / net_income
        elif dividends_paid == 0:
            metrics.payout_ratio = 0.0
        
        return metrics
    
    def _calc_profitability(
        self,
        revenue: Optional[float],
        gross_profit: Optional[float],
        operating_income: Optional[float],
        net_income: Optional[float],
        equity: Optional[float],
        total_assets: Optional[float],
        total_debt: float,
        cash: float,
        income_before_tax: Optional[float],
        goodwill: float = 0,
        intangibles: float = 0,
    ) -> ProfitabilityRatios:
        """Calculate profitability ratios."""
        ratios = ProfitabilityRatios()
        
        # Margin ratios (need positive revenue)
        if revenue and revenue > 0:
            if gross_profit is not None:
                ratios.gross_margin = gross_profit / revenue
            if operating_income is not None:
                ratios.operating_margin = operating_income / revenue
            if net_income is not None:
                ratios.net_margin = net_income / revenue
        
        # ROE
        if net_income and equity and equity > 0:
            ratios.roe = net_income / equity
        
        # ROA
        if net_income and total_assets and total_assets > 0:
            ratios.roa = net_income / total_assets
        
        # ROIC = NOPAT / Invested Capital
        # Note: We use EXCESS cash, not ALL cash, because businesses need
        # operating cash (typically 2% of revenue) to function. Subtracting
        # all cash artificially inflates ROIC for cash-rich companies.
        # Revenue is required to calculate operating cash needs.
        if operating_income and equity and income_before_tax and net_income and revenue:
            # Estimate tax rate
            tax_expense = income_before_tax - net_income
            tax_rate = tax_expense / income_before_tax if income_before_tax > 0 else 0.21
            tax_rate = max(0, min(tax_rate, 0.5))  # Bound between 0% and 50%
            
            nopat = operating_income * (1 - tax_rate)
            
            # Calculate excess cash (only subtract what's above operating needs)
            operating_cash = 0.02 * revenue if revenue else 0  # 2% of revenue
            excess_cash = max(0, cash - operating_cash)
            invested_capital = equity + total_debt - excess_cash
            
            if invested_capital > 0:
                ratios.roic = nopat / invested_capital
            
            # ROTIC = NOPAT / Tangible Invested Capital
            # Tangible IC excludes Goodwill and Intangible Assets from acquisitions.
            # This reveals true operating efficiency of the core business.
            tangible_invested_capital = invested_capital - goodwill - intangibles
            if tangible_invested_capital > 0:
                ratios.rotic = nopat / tangible_invested_capital
        
        return ratios
    
    def _calc_liquidity(
        self,
        current_assets: Optional[float],
        current_liabilities: Optional[float],
        inventory: float,
        total_debt: float,
        equity: Optional[float],
        operating_income: Optional[float],
        interest_expense: Optional[float],
    ) -> LiquidityRatios:
        """Calculate liquidity and solvency ratios."""
        ratios = LiquidityRatios()
        
        # Current Ratio
        if current_assets and current_liabilities and current_liabilities > 0:
            ratios.current_ratio = current_assets / current_liabilities
        
        # Quick Ratio
        if current_assets and current_liabilities and current_liabilities > 0:
            ratios.quick_ratio = (current_assets - inventory) / current_liabilities
        
        # Debt to Equity
        if equity and equity > 0:
            ratios.debt_to_equity = total_debt / equity
        
        # Interest Coverage
        if operating_income and interest_expense and interest_expense > 0:
            ratios.interest_coverage = operating_income / interest_expense
        
        return ratios
    
    def _calc_efficiency(
        self,
        revenue: Optional[float],
        total_assets: Optional[float],
        cogs: Optional[float],
        inventory: Optional[float],
    ) -> EfficiencyRatios:
        """Calculate efficiency ratios."""
        ratios = EfficiencyRatios()
        
        # Asset Turnover
        if revenue and total_assets and total_assets > 0:
            ratios.asset_turnover = revenue / total_assets
        
        # Inventory Turnover
        if cogs and inventory and inventory > 0:
            ratios.inventory_turnover = cogs / inventory
        
        return ratios


