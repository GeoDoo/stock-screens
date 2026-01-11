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
    """Dividend and shareholder return metrics."""
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    # NEW: Total Shareholder Yield (Alpha Layer)
    buyback_yield: Optional[float] = None  # Share Repurchases / Market Cap
    total_shareholder_yield: Optional[float] = None  # Dividend Yield + Buyback Yield


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
    incremental_roic: Optional[float] = None  # ΔNOPAT / ΔInvested Capital


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
    # Cash Conversion Cycle components
    days_sales_outstanding: Optional[float] = None  # DSO = (AR / Revenue) × 365
    days_inventory_outstanding: Optional[float] = None  # DIO = (Inventory / COGS) × 365
    days_payables_outstanding: Optional[float] = None  # DPO = (AP / COGS) × 365
    cash_conversion_cycle: Optional[float] = None  # CCC = DSO + DIO - DPO


@dataclass
class RiskMetrics:
    """Risk and bankruptcy indicators."""
    altman_z_score: Optional[float] = None
    z_score_zone: Optional[str] = None  # "safe", "grey", or "distress"
    accrual_ratio: Optional[float] = None  # Earnings quality metric
    accrual_quality: Optional[str] = None  # "good", "elevated", or "warning"
    beneish_m_score: Optional[float] = None  # Fraud detection
    manipulation_risk: Optional[str] = None  # "low_risk" or "high_risk" (matches frontend contract)


@dataclass
class SBCMetrics:
    """Stock-Based Compensation metrics."""
    stock_based_compensation: Optional[float] = None  # Raw SBC amount
    fcf_adjusted: Optional[float] = None  # FCF - SBC
    sbc_percent_revenue: Optional[float] = None  # SBC / Revenue
    fcf_margin_reported: Optional[float] = None  # FCF / Revenue
    fcf_margin_adjusted: Optional[float] = None  # (FCF - SBC) / Revenue
    sbc_level: Optional[str] = None  # "normal", "elevated", or "high"


@dataclass
class FinancialRatios:
    """Complete set of financial ratios."""
    valuation: ValuationRatios
    dividend: DividendMetrics
    profitability: ProfitabilityRatios
    liquidity: LiquidityRatios
    efficiency: EfficiencyRatios
    risk: RiskMetrics
    sbc: SBCMetrics


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
        income_stmts = data.get("income_statement", [{}])
        balance_sheets = data.get("balance_sheet", [{}])
        cash_flows = data.get("cash_flow", [{}])
        
        income_stmt = income_stmts[0] if income_stmts else {}
        balance_sheet = balance_sheets[0] if balance_sheets else {}
        cash_flow = cash_flows[0] if cash_flows else {}
        
        # Prior year data for M-Score calculations
        prior_income = income_stmts[1] if len(income_stmts) > 1 else None
        prior_balance = balance_sheets[1] if len(balance_sheets) > 1 else None
        prior_cash_flow = cash_flows[1] if len(cash_flows) > 1 else None
        
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
        total_liabilities = balance_sheet.get("totalLiabilities")
        total_debt = balance_sheet.get("totalDebt") or 0
        equity = balance_sheet.get("totalStockholdersEquity")
        cash = balance_sheet.get("cashAndCashEquivalents") or 0
        goodwill = balance_sheet.get("goodwill") or 0
        intangibles = balance_sheet.get("intangibleAssets") or 0
        retained_earnings = balance_sheet.get("retainedEarnings") or 0
        accounts_receivable = balance_sheet.get("netReceivables")
        accounts_payable = balance_sheet.get("accountPayables")
        
        dividends_paid = abs(cash_flow.get("dividendsPaid") or 0)
        operating_cash_flow = cash_flow.get("operatingCashFlow")
        free_cash_flow = cash_flow.get("freeCashFlow")
        stock_based_compensation = cash_flow.get("stockBasedCompensation")
        # Share repurchases (negative = buybacks, positive = issuance)
        share_repurchases = cash_flow.get("shareRepurchases") or 0
        
        # Calculate Enterprise Value
        ev = None
        if market_cap is not None:
            ev = market_cap + total_debt - cash
        
        # Calculate EBITDA
        ebitda = None
        if operating_income is not None:
            ebitda = operating_income + depreciation
        
        # Calculate prior year NOPAT and Invested Capital for incremental ROIC
        prior_nopat = None
        prior_invested_capital = None
        if prior_income and prior_balance:
            prior_oi = prior_income.get("operatingIncome")
            prior_ibt = prior_income.get("incomeBeforeTax")
            prior_ni = prior_income.get("netIncome")
            prior_rev = prior_income.get("revenue")
            prior_equity = prior_balance.get("totalStockholdersEquity")
            prior_debt = prior_balance.get("totalDebt") or 0
            prior_cash = prior_balance.get("cashAndCashEquivalents") or 0
            
            if prior_oi and prior_ibt and prior_ni and prior_rev and prior_equity:
                # Calculate prior tax rate
                prior_tax_expense = prior_ibt - prior_ni
                prior_tax_rate = prior_tax_expense / prior_ibt if prior_ibt > 0 else 0.21
                prior_tax_rate = max(0, min(prior_tax_rate, 0.5))
                
                prior_nopat = prior_oi * (1 - prior_tax_rate)
                
                # Calculate prior excess cash and invested capital
                prior_op_cash = 0.02 * prior_rev
                prior_excess_cash = max(0, prior_cash - prior_op_cash)
                prior_invested_capital = prior_equity + prior_debt - prior_excess_cash
        
        return FinancialRatios(
            valuation=self._calc_valuation(
                price, market_cap, shares, net_income, revenue, equity, ev, ebitda
            ),
            dividend=self._calc_dividend(
                price, shares, dividends_paid, net_income, market_cap, share_repurchases
            ),
            profitability=self._calc_profitability(
                revenue, gross_profit, operating_income, net_income,
                equity, total_assets, total_debt, cash, income_before_tax,
                goodwill, intangibles,
                prior_nopat=prior_nopat,
                prior_invested_capital=prior_invested_capital
            ),
            liquidity=self._calc_liquidity(
                current_assets, current_liabilities, inventory,
                total_debt, equity, operating_income, interest_expense
            ),
            efficiency=self._calc_efficiency(
                revenue, total_assets, cogs, inventory,
                accounts_receivable, accounts_payable
            ),
            risk=self._calc_risk(
                current_assets, current_liabilities, total_assets,
                retained_earnings, operating_income, market_cap,
                total_liabilities, revenue, net_income, operating_cash_flow,
                income_stmt, balance_sheet, cash_flow,
                prior_income, prior_balance, prior_cash_flow
            ),
            sbc=self._calc_sbc(
                stock_based_compensation, free_cash_flow, revenue
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
        market_cap: Optional[float],
        share_repurchases: float,
    ) -> DividendMetrics:
        """
        Calculate dividend and total shareholder yield metrics.
        
        Total Shareholder Yield = Dividend Yield + Buyback Yield
        
        This captures the true "cash return" to shareholders, as modern
        tech companies often return more via buybacks than dividends.
        """
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
        
        # Buyback Yield = Share Repurchases / Market Cap
        # Note: In cash flow, repurchases are typically negative (cash outflow)
        # A negative shareRepurchases means money spent on buybacks (good for shareholders)
        # A positive shareRepurchases means shares issued (dilution)
        if market_cap and market_cap > 0:
            # Convert to positive for buybacks (negate the negative cash flow)
            buyback_amount = -share_repurchases if share_repurchases else 0
            metrics.buyback_yield = buyback_amount / market_cap
        # else: buyback_yield remains None (data unavailable, not "zero buybacks")
        
        # Total Shareholder Yield = Dividend Yield + Buyback Yield
        # Only calculate when we have at least one component with valid data
        if metrics.dividend_yield is not None or metrics.buyback_yield is not None:
            div_yield = metrics.dividend_yield or 0.0
            buy_yield = metrics.buyback_yield or 0.0
            metrics.total_shareholder_yield = div_yield + buy_yield
        # else: total_shareholder_yield remains None (insufficient data)
        
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
        # Prior year data for incremental ROIC
        prior_nopat: Optional[float] = None,
        prior_invested_capital: Optional[float] = None,
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
        nopat = None
        invested_capital = None
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
        
        # Incremental ROIC = ΔNOPAT / ΔInvested Capital
        # Measures return on NEW capital invested - critical for reinvestment quality
        if (nopat is not None and invested_capital is not None and
            prior_nopat is not None and prior_invested_capital is not None):
            delta_nopat = nopat - prior_nopat
            delta_ic = invested_capital - prior_invested_capital
            if delta_ic != 0:
                ratios.incremental_roic = delta_nopat / delta_ic
        
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
        accounts_receivable: Optional[float] = None,
        accounts_payable: Optional[float] = None,
    ) -> EfficiencyRatios:
        """Calculate efficiency ratios."""
        ratios = EfficiencyRatios()
        
        # Asset Turnover
        if revenue and total_assets and total_assets > 0:
            ratios.asset_turnover = revenue / total_assets
        
        # Inventory Turnover
        if cogs and inventory and inventory > 0:
            ratios.inventory_turnover = cogs / inventory
        
        # Cash Conversion Cycle components
        # DSO = (Accounts Receivable / Revenue) × 365
        if accounts_receivable is not None and revenue and revenue > 0:
            ratios.days_sales_outstanding = (accounts_receivable / revenue) * 365
        
        # DIO = (Inventory / COGS) × 365
        if inventory and cogs and cogs > 0:
            ratios.days_inventory_outstanding = (inventory / cogs) * 365
        
        # DPO = (Accounts Payable / COGS) × 365
        if accounts_payable is not None and cogs and cogs > 0:
            ratios.days_payables_outstanding = (accounts_payable / cogs) * 365
        
        # CCC = DSO + DIO - DPO
        # Only calculate if all components are available
        if (ratios.days_sales_outstanding is not None and
            ratios.days_inventory_outstanding is not None and
            ratios.days_payables_outstanding is not None):
            ratios.cash_conversion_cycle = (
                ratios.days_sales_outstanding +
                ratios.days_inventory_outstanding -
                ratios.days_payables_outstanding
            )
        
        return ratios
    
    def _calc_risk(
        self,
        current_assets: Optional[float],
        current_liabilities: Optional[float],
        total_assets: Optional[float],
        retained_earnings: float,
        operating_income: Optional[float],
        market_cap: Optional[float],
        total_liabilities: Optional[float],
        revenue: Optional[float],
        net_income: Optional[float],
        operating_cash_flow: Optional[float],
        income_stmt: dict,
        balance_sheet: dict,
        cash_flow: dict,
        prior_income: Optional[dict],
        prior_balance: Optional[dict],
        prior_cash_flow: Optional[dict],
    ) -> RiskMetrics:
        """
        Calculate risk metrics including Altman Z-Score, Accrual Ratio, and Beneish M-Score.
        """
        ratios = RiskMetrics()
        
        # Calculate Accrual Ratio (independent of Z-Score)
        if (total_assets and total_assets > 0 and 
            net_income is not None and operating_cash_flow is not None):
            accrual = (net_income - operating_cash_flow) / total_assets
            ratios.accrual_ratio = accrual
            
            # Determine quality level
            if accrual > 0.10:
                ratios.accrual_quality = "warning"
            elif accrual >= 0.05:
                ratios.accrual_quality = "elevated"
            else:
                ratios.accrual_quality = "good"
        
        # Calculate Beneish M-Score (requires prior year data)
        m_score = self._calc_beneish_m_score(
            income_stmt, balance_sheet, cash_flow,
            prior_income, prior_balance, prior_cash_flow
        )
        if m_score is not None:
            ratios.beneish_m_score = m_score
            # P0 Fix: Return "high_risk"/"low_risk" to match frontend contract
            ratios.manipulation_risk = "high_risk" if m_score > -1.78 else "low_risk"
        
        # Check for critical data needed for Z-Score
        if not total_assets or total_assets <= 0:
            return ratios
        if not total_liabilities or total_liabilities <= 0:
            return ratios
        if market_cap is None:
            return ratios
        
        # Calculate components
        working_capital = 0
        if current_assets is not None and current_liabilities is not None:
            working_capital = current_assets - current_liabilities
        
        # A = Working Capital / Total Assets
        a = working_capital / total_assets
        
        # B = Retained Earnings / Total Assets
        b = retained_earnings / total_assets
        
        # C = EBIT / Total Assets
        c = (operating_income or 0) / total_assets
        
        # D = Market Value of Equity / Total Liabilities
        d = market_cap / total_liabilities
        
        # E = Sales / Total Assets
        e = (revenue or 0) / total_assets
        
        # Calculate Z-Score
        z_score = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e
        ratios.altman_z_score = z_score
        
        # Determine zone
        if z_score > 2.99:
            ratios.z_score_zone = "safe"
        elif z_score < 1.81:
            ratios.z_score_zone = "distress"
        else:
            ratios.z_score_zone = "grey"
        
        return ratios
    
    def _calc_beneish_m_score(
        self,
        income_stmt: dict,
        balance_sheet: dict,
        cash_flow: dict,
        prior_income: Optional[dict],
        prior_balance: Optional[dict],
        prior_cash_flow: Optional[dict],
    ) -> Optional[float]:
        """
        Calculate Beneish M-Score for earnings manipulation detection.
        
        M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI 
            + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
        
        Requires prior year data for comparison indices.
        Returns None if insufficient data.
        
        Interpretation:
        - M > -1.78: High probability of manipulation
        - M < -1.78: Low probability of manipulation
        """
        if not prior_income or not prior_balance:
            return None
        
        # Current year values
        rev_t = income_stmt.get("revenue")
        gp_t = income_stmt.get("grossProfit")
        ni_t = income_stmt.get("netIncome")
        sga_t = income_stmt.get("sellingGeneralAndAdministrative")
        ta_t = balance_sheet.get("totalAssets")
        ca_t = balance_sheet.get("totalCurrentAssets")
        rec_t = balance_sheet.get("netReceivables")
        ppe_t = balance_sheet.get("propertyPlantEquipmentNet")
        debt_t = balance_sheet.get("totalDebt") or 0
        cfo_t = cash_flow.get("operatingCashFlow") if cash_flow else None
        dep_t = cash_flow.get("depreciationAndAmortization") if cash_flow else None
        
        # Prior year values
        rev_t1 = prior_income.get("revenue")
        gp_t1 = prior_income.get("grossProfit")
        sga_t1 = prior_income.get("sellingGeneralAndAdministrative")
        ta_t1 = prior_balance.get("totalAssets")
        ca_t1 = prior_balance.get("totalCurrentAssets")
        rec_t1 = prior_balance.get("netReceivables")
        ppe_t1 = prior_balance.get("propertyPlantEquipmentNet")
        debt_t1 = prior_balance.get("totalDebt") or 0
        dep_t1 = prior_cash_flow.get("depreciationAndAmortization") if prior_cash_flow else None
        
        # Check for minimum required data
        if not all([rev_t, rev_t1, ta_t, ta_t1]):
            return None
        if rev_t1 == 0 or ta_t1 == 0 or ta_t == 0:
            return None
        
        # Calculate indices (use 1.0 as default if can't calculate)
        
        # DSRI: Days Sales Receivable Index
        dsri = 1.0
        if rec_t and rec_t1 and rev_t1 > 0:
            dsr_t = rec_t / rev_t
            dsr_t1 = rec_t1 / rev_t1
            if dsr_t1 > 0:
                dsri = dsr_t / dsr_t1
        
        # GMI: Gross Margin Index (prior / current, so deterioration > 1)
        gmi = 1.0
        if gp_t and gp_t1:
            gm_t = gp_t / rev_t
            gm_t1 = gp_t1 / rev_t1
            if gm_t > 0:
                gmi = gm_t1 / gm_t
        
        # AQI: Asset Quality Index
        aqi = 1.0
        if ca_t and ppe_t and ca_t1 and ppe_t1:
            aq_t = 1 - (ca_t + ppe_t) / ta_t
            aq_t1 = 1 - (ca_t1 + ppe_t1) / ta_t1
            if aq_t1 != 0:
                aqi = aq_t / aq_t1
        
        # SGI: Sales Growth Index
        sgi = rev_t / rev_t1
        
        # DEPI: Depreciation Index
        depi = 1.0
        if dep_t and dep_t1 and ppe_t and ppe_t1:
            dep_rate_t = dep_t / (ppe_t + dep_t) if (ppe_t + dep_t) > 0 else 0
            dep_rate_t1 = dep_t1 / (ppe_t1 + dep_t1) if (ppe_t1 + dep_t1) > 0 else 0
            if dep_rate_t > 0:
                depi = dep_rate_t1 / dep_rate_t
        
        # SGAI: SG&A Index
        sgai = 1.0
        if sga_t and sga_t1:
            sga_ratio_t = sga_t / rev_t
            sga_ratio_t1 = sga_t1 / rev_t1
            if sga_ratio_t1 > 0:
                sgai = sga_ratio_t / sga_ratio_t1
        
        # TATA: Total Accruals to Total Assets
        tata = 0.0
        if ni_t is not None and cfo_t is not None:
            tata = (ni_t - cfo_t) / ta_t
        
        # LVGI: Leverage Index
        lvgi = 1.0
        leverage_t = debt_t / ta_t if ta_t > 0 else 0
        leverage_t1 = debt_t1 / ta_t1 if ta_t1 > 0 else 0
        if leverage_t1 > 0:
            lvgi = leverage_t / leverage_t1
        
        # Calculate M-Score
        m_score = (
            -4.84
            + 0.920 * dsri
            + 0.528 * gmi
            + 0.404 * aqi
            + 0.892 * sgi
            + 0.115 * depi
            - 0.172 * sgai
            + 4.679 * tata
            - 0.327 * lvgi
        )
        
        return m_score
    
    def _calc_sbc(
        self,
        stock_based_compensation: Optional[float],
        free_cash_flow: Optional[float],
        revenue: Optional[float],
    ) -> SBCMetrics:
        """
        Calculate Stock-Based Compensation metrics.
        
        SBC is a real expense that dilutes shareholders but is added back
        in CFO because it's "non-cash". This hides the true cost of
        employee compensation.
        
        SBC-Adjusted FCF = FCF - SBC (treats SBC as real expense)
        """
        metrics = SBCMetrics()
        
        if stock_based_compensation is None:
            return metrics
        
        metrics.stock_based_compensation = stock_based_compensation
        
        # SBC-adjusted FCF
        if free_cash_flow is not None:
            metrics.fcf_adjusted = free_cash_flow - stock_based_compensation
        
        # SBC as % of revenue
        if revenue and revenue > 0:
            metrics.sbc_percent_revenue = stock_based_compensation / revenue
            
            # Determine SBC level
            if metrics.sbc_percent_revenue > 0.10:
                metrics.sbc_level = "high"
            elif metrics.sbc_percent_revenue >= 0.05:
                metrics.sbc_level = "elevated"
            else:
                metrics.sbc_level = "normal"
            
            # FCF margins
            if free_cash_flow is not None:
                metrics.fcf_margin_reported = free_cash_flow / revenue
                metrics.fcf_margin_adjusted = (free_cash_flow - stock_based_compensation) / revenue
        
        return metrics


