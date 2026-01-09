from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DCFCalculator:
    """
    Discounted Cash Flow calculator with optional mid-year discounting.
    
    Mid-year convention assumes cash flows are received at the middle of each year
    rather than at the end. This is more realistic for most businesses and produces
    slightly higher valuations (since cash is received sooner on average).
    
    Equity Bridge (institutional-grade):
        Equity Value = Enterprise Value
                     - Net Debt (Total Debt - Cash)
                     - Minority Interest (Non-Controlling Interest)
                     - Preferred Stock
                     + Deferred Tax Assets (NOLs/Tax Shields)
                     - Pension Deficit (Underfunded Pension Obligations)
    """
    current_fcf: float
    growth_rate: float
    discount_rate: float
    terminal_growth_rate: float
    projection_years: int
    shares_outstanding: float
    total_debt: float = 0.0
    cash: float = 0.0
    mid_year_discounting: bool = False  # Professional feature: assumes FCF received mid-year
    # Institutional equity bridge components
    minority_interest: float = 0.0  # Non-controlling interest (subtract from equity)
    preferred_stock: float = 0.0  # Preferred equity (subtract from common equity)
    deferred_tax_assets: float = 0.0  # NOLs/tax shields (add to equity)
    pension_deficit: float = 0.0  # Underfunded pension obligations (subtract from equity)

    def calculate(self) -> dict:
        """
        Calculate intrinsic value per share using DCF model.
        
        Returns dict with:
        - projected_fcf: list of projected free cash flows
        - terminal_value: terminal value using Gordon growth model
        - enterprise_value: sum of discounted cash flows + discounted terminal value
        - net_debt: total debt - cash
        - equity_value: enterprise value - net debt
        - intrinsic_value_per_share: equity value / shares outstanding
        - warning: optional warning message
        
        Raises:
            ValueError: If discount rate <= terminal growth rate (produces nonsense)
            ValueError: If shares outstanding <= 0
        """
        # Validate inputs - these are fundamental DCF constraints
        if self.discount_rate <= self.terminal_growth_rate:
            raise ValueError(
                f"Discount rate ({self.discount_rate:.2%}) must be greater than "
                f"terminal growth rate ({self.terminal_growth_rate:.2%}). "
                "Otherwise terminal value calculation produces nonsense (negative or infinite)."
            )
        
        if self.shares_outstanding <= 0:
            raise ValueError(
                f"Shares outstanding ({self.shares_outstanding}) must be positive. "
                "Cannot calculate per-share value with zero or negative shares."
            )
        
        result = {}

        # Project FCF for each year
        projected_fcf = []
        for year in range(1, self.projection_years + 1):
            fcf = self.current_fcf * ((1 + self.growth_rate) ** year)
            projected_fcf.append(fcf)
        result["projected_fcf"] = projected_fcf

        # Calculate terminal value (Gordon growth model)
        final_fcf = projected_fcf[-1]
        terminal_value = final_fcf * (1 + self.terminal_growth_rate) / (
            self.discount_rate - self.terminal_growth_rate
        )
        result["terminal_value"] = terminal_value

        # Discount all cash flows to present value
        # Mid-year convention: discount by (year - 0.5) instead of year
        discount_offset = 0.5 if self.mid_year_discounting else 0.0
        
        pv_fcf = sum(
            fcf / ((1 + self.discount_rate) ** (year - discount_offset))
            for year, fcf in enumerate(projected_fcf, start=1)
        )
        
        # Terminal value is received at end of projection period
        # Mid-year adjustment: discount terminal value at (projection_years - 0.5)
        terminal_discount_period = self.projection_years - discount_offset
        pv_terminal = terminal_value / ((1 + self.discount_rate) ** terminal_discount_period)

        enterprise_value = pv_fcf + pv_terminal
        result["enterprise_value"] = enterprise_value

        # Net debt adjustment
        net_debt = self.total_debt - self.cash
        result["net_debt"] = net_debt

        # Institutional-grade Equity Bridge:
        # Equity = EV - Net Debt - Minority Interest - Preferred + NOLs - Pension
        equity_bridge = {
            "net_debt": net_debt,
            "minority_interest": self.minority_interest,
            "preferred_stock": self.preferred_stock,
            "deferred_tax_assets": self.deferred_tax_assets,
            "pension_deficit": self.pension_deficit,
        }
        result["equity_bridge"] = equity_bridge
        
        equity_value = (
            enterprise_value
            - net_debt
            - self.minority_interest
            - self.preferred_stock
            + self.deferred_tax_assets
            - self.pension_deficit
        )
        result["equity_value"] = equity_value

        # Intrinsic value per share (based on equity value)
        intrinsic_value_per_share = equity_value / self.shares_outstanding
        result["intrinsic_value_per_share"] = intrinsic_value_per_share

        # Warnings
        warnings = []
        if self.current_fcf < 0:
            warnings.append("Negative FCF - intrinsic value may not be meaningful")
        if net_debt > enterprise_value:
            warnings.append("Net debt exceeds enterprise value - company may be distressed")
        
        if warnings:
            result["warning"] = "; ".join(warnings)

        return result
