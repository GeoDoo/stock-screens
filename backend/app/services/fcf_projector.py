from dataclasses import dataclass
from typing import List, Literal, Optional


# Default tax rate when company data is missing
DEFAULT_TAX_RATE = 0.25

# Working capital calculation modes
WCMode = Literal["level", "incremental"]


@dataclass
class FCFProjector:
    """
    Projects Free Cash Flow from first principles.
    
    Standard FCF = NOPAT + D&A - CapEx - ΔWorking Capital
    Conservative FCF = NOPAT + D&A - CapEx - ΔWC - SBC (when sbc_ratio provided)
    
    Where:
    - NOPAT = EBIT × (1 - Tax Rate)
    - D&A = Depreciation & Amortization
    - CapEx = Capital Expenditures
    - ΔWC = Change in Working Capital
    - SBC = Stock-Based Compensation (optional, projected as % of revenue)
    
    Working Capital Modes:
    - "level" (default): WC_t = Revenue_t × WC_ratio, ΔWC = WC_t - WC_{t-1}
      This maintains WC as a % of revenue (traditional approach)
    
    - "incremental": ΔWC = ΔRevenue × WC_intensity
      This ties WC investment directly to revenue growth (institutional approach)
      Better for high-growth companies and more realistic for stable businesses
    
    Conservative FCF Mode (NOTES2.md):
    Some investors treat SBC as a real cash expense because it represents
    value transferred from shareholders to employees through dilution.
    When sbc_ratio or sbc_schedule is provided, SBC is subtracted from FCF.
    """
    historical_revenue: List[float]
    historical_ebit: List[float]
    historical_da: List[float]
    historical_capex: List[float]
    historical_working_capital: List[float]
    historical_sbc: Optional[List[float]] = None  # Historical Stock-Based Compensation
    tax_rate: Optional[float] = None  # Will use DEFAULT_TAX_RATE if None
    wc_mode: WCMode = "level"  # Default to level-based for backward compatibility
    
    @property
    def effective_tax_rate(self) -> float:
        """Return tax rate or default if not available."""
        return self.tax_rate if self.tax_rate is not None else DEFAULT_TAX_RATE

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
        Always returns positive value (CapEx is an expense).
        """
        if not self.historical_revenue or not self.historical_capex:
            return 0.0
        
        ratios = [
            abs(capex) / rev  # Use abs() - historical capex is often stored as negative (outflow)
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
    
    def sbc_to_revenue_ratio(self) -> float:
        """
        Calculate average Stock-Based Compensation as percentage of revenue.
        
        NOTES2.md: Conservative FCF treats SBC as a real expense because
        it represents value transferred from shareholders to employees.
        
        Returns 0.0 if no historical SBC data available.
        """
        if not self.historical_revenue or not self.historical_sbc:
            return 0.0
        
        ratios = [
            sbc / rev 
            for sbc, rev in zip(self.historical_sbc, self.historical_revenue)
            if rev > 0 and sbc is not None
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
        wc_mode: Optional[str] = None,
        sbc_ratio: Optional[float] = None,
    ) -> dict:
        """
        Project FCF for a single year.
        
        Working capital calculation depends on wc_mode:
        - "level": WC = Revenue × wc_ratio (maintains WC as % of revenue)
        - "incremental": ΔWC = ΔRevenue × wc_ratio (ties WC to growth)
        
        Conservative FCF (when sbc_ratio provided):
        - SBC = Revenue × sbc_ratio
        - FCF = NOPAT + D&A - CapEx - ΔWC - SBC
        
        Returns dict with all components for transparency.
        """
        # Use passed wc_mode or fall back to instance default
        _wc_mode = wc_mode if wc_mode is not None else self.wc_mode
        
        # Project revenue
        revenue = prior_revenue * (1 + revenue_growth)
        
        # Calculate EBIT from operating margin
        ebit = revenue * operating_margin
        
        # Calculate NOPAT (Net Operating Profit After Tax)
        nopat = ebit * (1 - self.effective_tax_rate)
        
        # D&A as % of revenue
        da = revenue * da_ratio
        
        # CapEx as % of revenue
        capex = revenue * capex_ratio
        
        # Working capital change - depends on mode
        if _wc_mode == "incremental":
            # Incremental: ΔWC = ΔRevenue × WC_intensity
            delta_revenue = revenue - prior_revenue
            delta_wc = delta_revenue * wc_ratio
            new_wc = prior_working_capital + delta_wc
        else:
            # Level (default): WC = Revenue × WC_ratio
            new_wc = revenue * wc_ratio
            delta_wc = new_wc - prior_working_capital
        
        # FCF = NOPAT + D&A - CapEx - ΔWC
        fcf = nopat + da - capex - delta_wc
        
        # Conservative FCF: subtract SBC if provided (NOTES2.md)
        sbc = 0.0
        if sbc_ratio is not None and sbc_ratio > 0:
            sbc = revenue * sbc_ratio
            fcf = fcf - sbc
        
        return {
            "revenue": revenue,
            "ebit": ebit,
            "nopat": nopat,
            "da": da,
            "capex": capex,
            "working_capital": new_wc,
            "delta_wc": delta_wc,
            "sbc": sbc,  # Always include for transparency
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
        wc_mode: str = "level",
        growth_schedule: Optional[List[float]] = None,
        # Economics schedules for multi-stage modeling
        margin_schedule: Optional[List[float]] = None,
        da_schedule: Optional[List[float]] = None,
        capex_schedule: Optional[List[float]] = None,
        wc_schedule: Optional[List[float]] = None,
        # Conservative FCF: SBC as real expense (NOTES2.md)
        sbc_ratio: Optional[float] = None,
        sbc_schedule: Optional[List[float]] = None,
    ) -> List[dict]:
        """
        Project FCF for multiple years.
        
        All ratios default to historical averages but can be overridden.
        
        Schedules take precedence over constant values:
        - growth_schedule overrides revenue_growth
        - margin_schedule overrides operating_margin
        - da_schedule overrides da_ratio
        - capex_schedule overrides capex_ratio
        - wc_schedule overrides wc_ratio
        - sbc_schedule overrides sbc_ratio
        
        When a schedule is shorter than the projection period, the last
        value is repeated for remaining years.
        
        Args:
            years: Number of years to project (ignored if growth_schedule provided)
            revenue_growth: Constant growth rate for all years (ignored if growth_schedule provided)
            growth_schedule: List of growth rates per year (overrides revenue_growth and years)
            margin_schedule: List of operating margins per year
            da_schedule: List of D&A ratios per year
            capex_schedule: List of CapEx ratios per year
            wc_schedule: List of WC ratios per year
            wc_mode: "level" (WC = Revenue × Ratio) or "incremental" (ΔWC = ΔRevenue × Intensity)
            sbc_ratio: SBC as % of revenue (Conservative FCF mode)
            sbc_schedule: Per-year SBC ratios (overrides sbc_ratio)
        """
        # Use historical averages as defaults for constant values
        _revenue_growth = revenue_growth if revenue_growth is not None else self.revenue_cagr()
        _operating_margin = operating_margin if operating_margin is not None else self.operating_margin()
        _da_ratio = da_ratio if da_ratio is not None else self.da_to_revenue_ratio()
        _capex_ratio = capex_ratio if capex_ratio is not None else self.capex_to_revenue_ratio()
        _wc_ratio = wc_ratio if wc_ratio is not None else self.wc_to_revenue_ratio()
        _sbc_ratio = sbc_ratio  # None means no SBC subtraction (standard FCF)
        
        # If growth_schedule provided, use it for variable growth rates
        if growth_schedule:
            num_years = len(growth_schedule)
        else:
            num_years = years
            growth_schedule = [_revenue_growth] * num_years  # Constant growth
        
        # Helper to get schedule value with fallback to constant
        def get_schedule_value(schedule: Optional[List[float]], index: int, constant: Optional[float]) -> Optional[float]:
            if schedule is None:
                return constant
            if index < len(schedule):
                return schedule[index]
            # Schedule shorter than projection - use last value
            return schedule[-1] if schedule else constant
        
        projections = []
        prior_revenue = self.historical_revenue[-1] if self.historical_revenue else 0.0
        prior_wc = self.historical_working_capital[-1] if self.historical_working_capital else 0.0
        
        for year_idx in range(num_years):
            year_growth = growth_schedule[year_idx]
            
            # Get year-specific economics (or constant if no schedule)
            year_margin = get_schedule_value(margin_schedule, year_idx, _operating_margin)
            year_da = get_schedule_value(da_schedule, year_idx, _da_ratio)
            year_capex = get_schedule_value(capex_schedule, year_idx, _capex_ratio)
            year_wc = get_schedule_value(wc_schedule, year_idx, _wc_ratio)
            year_sbc = get_schedule_value(sbc_schedule, year_idx, _sbc_ratio)
            
            year_projection = self.project_fcf_year(
                prior_revenue=prior_revenue,
                prior_working_capital=prior_wc,
                revenue_growth=year_growth,
                operating_margin=year_margin,
                da_ratio=year_da,
                capex_ratio=year_capex,
                wc_ratio=year_wc,
                wc_mode=wc_mode,
                sbc_ratio=year_sbc,
            )
            projections.append(year_projection)
            
            # Update for next year
            prior_revenue = year_projection["revenue"]
            prior_wc = year_projection["working_capital"]
        
        return projections



