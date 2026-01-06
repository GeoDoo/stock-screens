"""
Historical Valuation Analyzer Service

Compares current valuation multiples to historical averages.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from statistics import mean


@dataclass
class YearlyMetrics:
    """Valuation metrics for a single year."""
    year: int
    date: str
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    equity: Optional[float] = None
    pe: Optional[float] = None
    ps: Optional[float] = None
    pb: Optional[float] = None
    ev_ebitda: Optional[float] = None


@dataclass
class HistoricalValuation:
    """Complete historical valuation analysis."""
    # Current multiples
    current_pe: Optional[float] = None
    current_ps: Optional[float] = None
    current_pb: Optional[float] = None
    current_ev_ebitda: Optional[float] = None
    
    # 5-year averages
    avg_pe_5yr: Optional[float] = None
    avg_ps_5yr: Optional[float] = None
    avg_pb_5yr: Optional[float] = None
    avg_ev_ebitda_5yr: Optional[float] = None
    
    # Premium/discount vs average
    premium_discount_pe: Optional[float] = None
    premium_discount_ps: Optional[float] = None
    premium_discount_pb: Optional[float] = None
    premium_discount_ev_ebitda: Optional[float] = None
    
    # Assessment
    pe_assessment: str = "fair"
    ps_assessment: str = "fair"
    pb_assessment: str = "fair"
    ev_ebitda_assessment: str = "fair"
    
    # Yearly breakdown
    yearly_metrics: List[YearlyMetrics] = field(default_factory=list)


class HistoricalValuationAnalyzer:
    """
    Analyzes historical valuation multiples.
    
    Compares current P/E, P/S, P/B, EV/EBITDA to 5-year averages
    to determine if a stock is expensive or cheap relative to itself.
    """
    
    # Thresholds for assessment
    CHEAP_THRESHOLD = -0.15  # 15% below average
    EXPENSIVE_THRESHOLD = 0.15  # 15% above average
    
    def analyze(
        self,
        financials: List[dict],
        profile: dict,
    ) -> HistoricalValuation:
        """
        Analyze historical valuation.
        
        Args:
            financials: List of annual financial statements (most recent first)
            profile: Current company profile with price, market_cap, shares
            
        Returns:
            HistoricalValuation with current vs historical comparison
        """
        result = HistoricalValuation()
        
        if not financials:
            return result
        
        # Extract current market data
        price = profile.get("price")
        market_cap = profile.get("market_cap") or profile.get("marketCap")
        shares = profile.get("shares_outstanding") or profile.get("sharesOutstanding")
        
        # Calculate current multiples from most recent financials
        latest = financials[0]
        
        current_revenue = latest.get("revenue")
        current_net_income = latest.get("net_income") or latest.get("netIncome")
        current_equity = latest.get("total_equity") or latest.get("totalStockholdersEquity")
        current_debt = latest.get("total_debt") or latest.get("totalDebt") or 0
        current_cash = latest.get("cash_and_equivalents") or latest.get("cashAndCashEquivalents") or 0
        current_operating_income = latest.get("operating_income") or latest.get("operatingIncome")
        current_da = latest.get("depreciation_amortization") or latest.get("depreciationAndAmortization") or 0
        
        # Calculate current multiples
        if market_cap and market_cap > 0:
            if current_net_income and current_net_income > 0:
                result.current_pe = market_cap / current_net_income
            
            if current_revenue and current_revenue > 0:
                result.current_ps = market_cap / current_revenue
            
            if current_equity and current_equity > 0:
                result.current_pb = market_cap / current_equity
            
            # EV/EBITDA
            ev = market_cap + current_debt - current_cash
            if current_operating_income:
                ebitda = current_operating_income + current_da
                if ebitda > 0:
                    result.current_ev_ebitda = ev / ebitda
        
        # Calculate yearly metrics (for historical comparison)
        yearly_metrics = []
        for fin in financials:
            ym = self._calculate_yearly_metrics(fin, market_cap)
            if ym:
                yearly_metrics.append(ym)
        
        result.yearly_metrics = yearly_metrics
        
        # Calculate 5-year averages (need at least 2 years)
        if len(yearly_metrics) >= 2:
            pe_values = [ym.pe for ym in yearly_metrics if ym.pe and ym.pe > 0]
            ps_values = [ym.ps for ym in yearly_metrics if ym.ps and ym.ps > 0]
            pb_values = [ym.pb for ym in yearly_metrics if ym.pb and ym.pb > 0]
            ev_ebitda_values = [ym.ev_ebitda for ym in yearly_metrics if ym.ev_ebitda and ym.ev_ebitda > 0]
            
            if len(pe_values) >= 2:
                result.avg_pe_5yr = mean(pe_values)
            if len(ps_values) >= 2:
                result.avg_ps_5yr = mean(ps_values)
            if len(pb_values) >= 2:
                result.avg_pb_5yr = mean(pb_values)
            if len(ev_ebitda_values) >= 2:
                result.avg_ev_ebitda_5yr = mean(ev_ebitda_values)
        
        # Calculate premium/discount
        if result.current_pe and result.avg_pe_5yr:
            result.premium_discount_pe = (result.current_pe - result.avg_pe_5yr) / result.avg_pe_5yr
            result.pe_assessment = self._assess(result.premium_discount_pe)
        
        if result.current_ps and result.avg_ps_5yr:
            result.premium_discount_ps = (result.current_ps - result.avg_ps_5yr) / result.avg_ps_5yr
            result.ps_assessment = self._assess(result.premium_discount_ps)
        
        if result.current_pb and result.avg_pb_5yr:
            result.premium_discount_pb = (result.current_pb - result.avg_pb_5yr) / result.avg_pb_5yr
            result.pb_assessment = self._assess(result.premium_discount_pb)
        
        if result.current_ev_ebitda and result.avg_ev_ebitda_5yr:
            result.premium_discount_ev_ebitda = (result.current_ev_ebitda - result.avg_ev_ebitda_5yr) / result.avg_ev_ebitda_5yr
            result.ev_ebitda_assessment = self._assess(result.premium_discount_ev_ebitda)
        
        return result
    
    def _calculate_yearly_metrics(
        self,
        fin: dict,
        current_market_cap: Optional[float],
    ) -> Optional[YearlyMetrics]:
        """Calculate metrics for a single year."""
        date_str = fin.get("date")
        if not date_str:
            return None
        
        try:
            year = int(date_str[:4])
        except (ValueError, TypeError):
            return None
        
        revenue = fin.get("revenue")
        net_income = fin.get("net_income") or fin.get("netIncome")
        equity = fin.get("total_equity") or fin.get("totalStockholdersEquity")
        debt = fin.get("total_debt") or fin.get("totalDebt") or 0
        cash = fin.get("cash_and_equivalents") or fin.get("cashAndCashEquivalents") or 0
        operating_income = fin.get("operating_income") or fin.get("operatingIncome")
        da = fin.get("depreciation_amortization") or fin.get("depreciationAndAmortization") or 0
        
        ebitda = None
        if operating_income:
            ebitda = operating_income + da
        
        metrics = YearlyMetrics(
            year=year,
            date=date_str,
            revenue=revenue,
            net_income=net_income,
            ebitda=ebitda,
            equity=equity,
        )
        
        # Calculate ratios using current market cap (for historical comparison)
        # Note: Ideally we'd use historical prices, but we'll use current market cap
        # as a proxy to show how the business metrics have evolved
        if current_market_cap and current_market_cap > 0:
            if net_income and net_income > 0:
                metrics.pe = current_market_cap / net_income
            
            if revenue and revenue > 0:
                metrics.ps = current_market_cap / revenue
            
            if equity and equity > 0:
                metrics.pb = current_market_cap / equity
            
            if ebitda and ebitda > 0:
                ev = current_market_cap + debt - cash
                metrics.ev_ebitda = ev / ebitda
        
        return metrics
    
    def _assess(self, premium_discount: float) -> str:
        """Assess if valuation is cheap, fair, or expensive."""
        if premium_discount <= self.CHEAP_THRESHOLD:
            return "cheap"
        elif premium_discount >= self.EXPENSIVE_THRESHOLD:
            return "expensive"
        return "fair"


