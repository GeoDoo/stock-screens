from dataclasses import dataclass
from typing import List, Optional


def validate_wacc_inputs(
    tax_rate: float,
    total_debt: float,
    market_cap: float,
) -> List[str]:
    """
    Validate WACC inputs and return list of warnings.
    
    Returns:
        List of warning messages for invalid/unusual inputs
    """
    warnings = []
    
    if tax_rate < 0:
        warnings.append(f"Tax rate ({tax_rate:.1%}) is negative - will be treated as 0%")
    elif tax_rate > 1:
        warnings.append(f"Tax rate ({tax_rate:.1%}) exceeds 100% - will be capped at 100%")
    
    if total_debt < 0:
        warnings.append(f"Total debt ({total_debt:,.0f}) is negative - will be treated as 0 (net cash position)")
    
    if market_cap <= 0:
        warnings.append(f"Market cap ({market_cap:,.0f}) is zero or negative - WACC calculation may be invalid")
    
    return warnings


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


@dataclass
class WACCCalculator:
    """
    Weighted Average Cost of Capital calculator.
    
    WACC = (E/V) * Re + (D/V) * Rd * (1 - T)
    
    Where:
    - E = Market cap (equity value)
    - D = Total debt
    - V = E + D (total firm value)
    - Re = Cost of equity
    - Rd = Cost of debt
    - T = Tax rate
    """
    risk_free_rate: float      # e.g., 10-year treasury yield
    beta: float                # Stock's beta
    market_risk_premium: float # Expected market return - risk free rate
    cost_of_debt: float        # Interest rate on debt
    tax_rate: float            # Effective tax rate
    market_cap: float          # Market capitalization
    total_debt: float          # Total debt

    def cost_of_equity(self) -> float:
        """
        Calculate cost of equity using CAPM.
        Re = Rf + β * (Rm - Rf)
        """
        return self.risk_free_rate + self.beta * self.market_risk_premium

    @property
    def _effective_tax_rate(self) -> float:
        """Tax rate clamped to valid range [0, 1]."""
        return _clamp(self.tax_rate, 0.0, 1.0)
    
    @property
    def _effective_debt(self) -> float:
        """Debt clamped to non-negative (negative debt = net cash position)."""
        return max(0.0, self.total_debt)

    def after_tax_cost_of_debt(self) -> float:
        """
        Calculate after-tax cost of debt.
        Rd * (1 - T)
        
        Tax rate is clamped to [0, 1] range.
        """
        return self.cost_of_debt * (1 - self._effective_tax_rate)

    def calculate(self) -> float:
        """
        Calculate WACC.
        
        Handles edge cases:
        - Tax rate clamped to [0, 1]
        - Negative debt treated as 0 (net cash position)
        """
        effective_debt = self._effective_debt
        total_value = self.market_cap + effective_debt
        
        if total_value == 0:
            return 0.0

        equity_weight = self.market_cap / total_value
        debt_weight = effective_debt / total_value

        wacc = (
            equity_weight * self.cost_of_equity() +
            debt_weight * self.after_tax_cost_of_debt()
        )

        return wacc



