from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SensitivityCalculator:
    """
    Calculates sensitivity matrix for DCF valuation.
    
    Varies two inputs (discount rate, terminal growth) and shows
    how intrinsic value changes across combinations.
    
    Uses the full institutional equity bridge for consistency with
    the main valuation service.
    
    P0 Fix: Now uses actual FCF component ratios (da_ratio, capex_ratio, wc_ratio)
    instead of hardcoded 0.80 conversion factor, ensuring mathematical parity
    with FCFProjector used in main valuation.
    """
    projected_fcfs: List[float]
    projection_years: int
    shares_outstanding: float
    total_debt: float
    cash: float
    # Institutional equity bridge components (for consistency with main valuation)
    minority_interest: float = 0.0
    preferred_stock: float = 0.0
    deferred_tax_assets: float = 0.0
    pension_deficit: float = 0.0
    # FCF component ratios (for margin/growth matrix - matches FCFProjector)
    da_ratio: float = 0.05       # D&A as % of revenue
    capex_ratio: float = 0.08    # CapEx as % of revenue
    wc_ratio: float = 0.10       # Working capital as % of revenue
    tax_rate: float = 0.25       # Corporate tax rate
    wc_mode: str = "incremental" # "level" or "incremental"
    
    def calculate_intrinsic_value(
        self, 
        discount_rate: float, 
        terminal_growth_rate: float
    ) -> Optional[float]:
        """Calculate intrinsic value for a single discount_rate/terminal_growth combination."""
        if not self.projected_fcfs:
            return None
        
        # Discount rate must be greater than terminal growth
        if discount_rate <= terminal_growth_rate:
            return None
        
        # PV of projected FCFs
        pv_fcf = sum(
            fcf / ((1 + discount_rate) ** year)
            for year, fcf in enumerate(self.projected_fcfs, start=1)
        )
        
        # Terminal value (Gordon Growth Model)
        final_fcf = self.projected_fcfs[-1]
        terminal_value = final_fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        pv_terminal = terminal_value / ((1 + discount_rate) ** self.projection_years)
        
        enterprise_value = pv_fcf + pv_terminal
        
        # Full institutional equity bridge (consistent with main valuation)
        net_debt = self.total_debt - self.cash
        equity_value = (
            enterprise_value
            - net_debt
            - self.minority_interest
            - self.preferred_stock
            + self.deferred_tax_assets
            - self.pension_deficit
        )
        
        # Per share
        if self.shares_outstanding <= 0:
            return None
        
        return equity_value / self.shares_outstanding
    
    def generate_matrix(
        self,
        base_discount_rate: float,
        base_terminal_growth: float,
        discount_rate_steps: List[float],  # e.g., [-0.02, -0.01, 0, 0.01, 0.02]
        terminal_growth_steps: List[float],  # e.g., [-0.01, -0.005, 0, 0.005, 0.01]
    ) -> dict:
        """
        Generate sensitivity matrix.
        
        Returns:
            {
                "discount_rates": [0.08, 0.09, 0.10, 0.11, 0.12],
                "terminal_growth_rates": [0.02, 0.025, 0.03, 0.035, 0.04],
                "matrix": [[...], [...], ...],  # intrinsic values
                "base_discount_rate": 0.10,
                "base_terminal_growth": 0.03
            }
        """
        discount_rates = [base_discount_rate + step for step in discount_rate_steps]
        terminal_growth_rates = [base_terminal_growth + step for step in terminal_growth_steps]
        
        matrix = []
        for dr in discount_rates:
            row = []
            for tg in terminal_growth_rates:
                value = self.calculate_intrinsic_value(dr, tg)
                row.append(value)
            matrix.append(row)
        
        return {
            "discount_rates": discount_rates,
            "terminal_growth_rates": terminal_growth_rates,
            "matrix": matrix,
            "base_discount_rate": base_discount_rate,
            "base_terminal_growth": base_terminal_growth,
        }
    
    def generate_margin_growth_matrix(
        self,
        base_revenue: float,
        base_margin: float,
        base_growth: float,
        discount_rate: float,
        terminal_growth: float,
        margin_steps: List[float],  # e.g., [-0.05, -0.025, 0, 0.025, 0.05]
        growth_steps: List[float],  # e.g., [-0.05, -0.025, 0, 0.025, 0.05]
    ) -> dict:
        """
        Generate Margin vs Growth sensitivity matrix.
        
        Unlike the standard WACC/terminal growth matrix, this varies the
        business assumptions (margin and growth) to show execution risk.
        
        For each combination, re-projects FCF and calculates intrinsic value.
        
        Args:
            base_revenue: Current annual revenue
            base_margin: Base operating margin (e.g., 0.20 for 20%)
            base_growth: Base revenue growth rate (e.g., 0.10 for 10%)
            discount_rate: Fixed WACC for DCF
            terminal_growth: Fixed terminal growth rate
            margin_steps: Adjustments to base margin
            growth_steps: Adjustments to base growth rate
            
        Returns:
            {
                "margins": [0.15, 0.175, 0.20, 0.225, 0.25],
                "growth_rates": [0.05, 0.075, 0.10, 0.125, 0.15],
                "matrix": [[...], [...], ...],  # intrinsic values
                "base_margin": 0.20,
                "base_growth": 0.10
            }
        """
        margins = [base_margin + step for step in margin_steps]
        growth_rates = [base_growth + step for step in growth_steps]
        
        matrix = []
        for margin in margins:
            row = []
            for growth in growth_rates:
                value = self._calc_value_for_margin_growth(
                    base_revenue, margin, growth,
                    discount_rate, terminal_growth
                )
                row.append(value)
            matrix.append(row)
        
        return {
            "margins": margins,
            "growth_rates": growth_rates,
            "matrix": matrix,
            "base_margin": base_margin,
            "base_growth": base_growth,
        }
    
    def _calc_value_for_margin_growth(
        self,
        base_revenue: float,
        margin: float,
        growth: float,
        discount_rate: float,
        terminal_growth: float,
    ) -> Optional[float]:
        """
        Calculate intrinsic value for a specific margin/growth combination.
        
        Projects FCF using the same formula as FCFProjector:
        FCF = NOPAT + D&A - CapEx - ΔWC
        
        This ensures mathematical parity with the main valuation engine.
        """
        if discount_rate <= terminal_growth:
            return None
        
        # Project revenues year by year
        revenues = []
        revenue = base_revenue
        for _ in range(self.projection_years):
            revenue = revenue * (1 + growth)
            revenues.append(revenue)
        
        # Calculate FCF using actual component ratios (matches FCFProjector)
        # FCF = NOPAT + D&A - CapEx - ΔWC
        projected_fcfs = []
        prev_wc = base_revenue * self.wc_ratio  # Starting working capital
        
        for i, rev in enumerate(revenues):
            # NOPAT = Revenue × Margin × (1 - Tax)
            nopat = rev * margin * (1 - self.tax_rate)
            
            # D&A as % of revenue
            da = rev * self.da_ratio
            
            # CapEx as % of revenue
            capex = rev * self.capex_ratio
            
            # Working capital change
            if self.wc_mode == "level":
                # Level: WC = Revenue × ratio, ΔWC = WC[t] - WC[t-1]
                current_wc = rev * self.wc_ratio
                delta_wc = current_wc - prev_wc
                prev_wc = current_wc
            else:
                # Incremental: ΔWC = ΔRevenue × ratio
                if i == 0:
                    delta_rev = rev - base_revenue
                else:
                    delta_rev = rev - revenues[i - 1]
                delta_wc = delta_rev * self.wc_ratio
            
            # FCF = NOPAT + D&A - CapEx - ΔWC
            fcf = nopat + da - capex - delta_wc
            projected_fcfs.append(fcf)
        
        if not projected_fcfs:
            return None
        
        # PV of projected FCFs
        pv_fcf = sum(
            fcf / ((1 + discount_rate) ** year)
            for year, fcf in enumerate(projected_fcfs, start=1)
        )
        
        # Terminal value (Gordon Growth Model)
        final_fcf = projected_fcfs[-1]
        terminal_value = final_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** self.projection_years)
        
        enterprise_value = pv_fcf + pv_terminal
        
        # Full institutional equity bridge (consistent with main valuation)
        net_debt = self.total_debt - self.cash
        equity_value = (
            enterprise_value
            - net_debt
            - self.minority_interest
            - self.preferred_stock
            + self.deferred_tax_assets
            - self.pension_deficit
        )
        
        if self.shares_outstanding <= 0:
            return None
        
        return equity_value / self.shares_outstanding



