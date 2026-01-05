from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FCFProjector:
    """
    Projects Free Cash Flow from first principles.
    
    FCF = NOPAT + D&A - CapEx - ΔWorking Capital
    
    Where:
    - NOPAT = EBIT × (1 - Tax Rate)
    - D&A = Depreciation & Amortization
    - CapEx = Capital Expenditures
    - ΔWC = Change in Working Capital
    """
    historical_revenue: List[float]
    historical_ebit: List[float]
    historical_da: List[float]
    historical_capex: List[float]
    historical_working_capital: List[float]
    tax_rate: float

    def revenue_cagr(self) -> float:
        """
        Calculate Compound Annual Growth Rate of revenue.
        CAGR = (End/Start)^(1/years) - 1
        """
        if len(self.historical_revenue) < 2:
            return 0.0
        
        start = self.historical_revenue[0]
        end = self.historical_revenue[-1]
        years = len(self.historical_revenue) - 1
        
        if start <= 0:
            return 0.0
            
        return (end / start) ** (1 / years) - 1

    def operating_margin(self) -> float:
        """
        Calculate average operating margin (EBIT / Revenue).
        """
        if not self.historical_revenue or not self.historical_ebit:
            return 0.0
        
        margins = [
            ebit / rev 
            for ebit, rev in zip(self.historical_ebit, self.historical_revenue)
            if rev > 0
        ]
        return sum(margins) / len(margins) if margins else 0.0

    def da_to_revenue_ratio(self) -> float:
        """
        Calculate average D&A as percentage of revenue.
        """
        if not self.historical_revenue or not self.historical_da:
            return 0.0
        
        ratios = [
            da / rev 
            for da, rev in zip(self.historical_da, self.historical_revenue)
            if rev > 0
        ]
        return sum(ratios) / len(ratios) if ratios else 0.0

    def capex_to_revenue_ratio(self) -> float:
        """
        Calculate average CapEx as percentage of revenue.
        """
        if not self.historical_revenue or not self.historical_capex:
            return 0.0
        
        ratios = [
            capex / rev 
            for capex, rev in zip(self.historical_capex, self.historical_revenue)
            if rev > 0
        ]
        return sum(ratios) / len(ratios) if ratios else 0.0

    def wc_to_revenue_ratio(self) -> float:
        """
        Calculate average Working Capital as percentage of revenue.
        """
        if not self.historical_revenue or not self.historical_working_capital:
            return 0.0
        
        ratios = [
            wc / rev 
            for wc, rev in zip(self.historical_working_capital, self.historical_revenue)
            if rev > 0
        ]
        return sum(ratios) / len(ratios) if ratios else 0.0

    def project_fcf_year(
        self,
        prior_revenue: float,
        prior_working_capital: float,
        revenue_growth: float,
        operating_margin: float,
        da_ratio: float,
        capex_ratio: float,
        wc_ratio: float,
    ) -> dict:
        """
        Project FCF for a single year.
        
        Returns dict with all components for transparency.
        """
        # Project revenue
        revenue = prior_revenue * (1 + revenue_growth)
        
        # Calculate EBIT from operating margin
        ebit = revenue * operating_margin
        
        # Calculate NOPAT (Net Operating Profit After Tax)
        nopat = ebit * (1 - self.tax_rate)
        
        # D&A as % of revenue
        da = revenue * da_ratio
        
        # CapEx as % of revenue
        capex = revenue * capex_ratio
        
        # Working capital change
        new_wc = revenue * wc_ratio
        delta_wc = new_wc - prior_working_capital
        
        # FCF = NOPAT + D&A - CapEx - ΔWC
        fcf = nopat + da - capex - delta_wc
        
        return {
            "revenue": revenue,
            "ebit": ebit,
            "nopat": nopat,
            "da": da,
            "capex": capex,
            "working_capital": new_wc,
            "delta_wc": delta_wc,
            "fcf": fcf,
        }

    def project(
        self,
        years: int,
        revenue_growth: Optional[float] = None,
        operating_margin: Optional[float] = None,
        da_ratio: Optional[float] = None,
        capex_ratio: Optional[float] = None,
        wc_ratio: Optional[float] = None,
    ) -> List[dict]:
        """
        Project FCF for multiple years.
        
        All ratios default to historical averages but can be overridden.
        """
        # Use historical averages as defaults
        _revenue_growth = revenue_growth if revenue_growth is not None else self.revenue_cagr()
        _operating_margin = operating_margin if operating_margin is not None else self.operating_margin()
        _da_ratio = da_ratio if da_ratio is not None else self.da_to_revenue_ratio()
        _capex_ratio = capex_ratio if capex_ratio is not None else self.capex_to_revenue_ratio()
        _wc_ratio = wc_ratio if wc_ratio is not None else self.wc_to_revenue_ratio()
        
        projections = []
        prior_revenue = self.historical_revenue[-1]
        prior_wc = self.historical_working_capital[-1]
        
        for _ in range(years):
            year_projection = self.project_fcf_year(
                prior_revenue=prior_revenue,
                prior_working_capital=prior_wc,
                revenue_growth=_revenue_growth,
                operating_margin=_operating_margin,
                da_ratio=_da_ratio,
                capex_ratio=_capex_ratio,
                wc_ratio=_wc_ratio,
            )
            projections.append(year_projection)
            
            # Update for next year
            prior_revenue = year_projection["revenue"]
            prior_wc = year_projection["working_capital"]
        
        return projections


