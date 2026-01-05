from dataclasses import dataclass


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

    def after_tax_cost_of_debt(self) -> float:
        """
        Calculate after-tax cost of debt.
        Rd * (1 - T)
        """
        return self.cost_of_debt * (1 - self.tax_rate)

    def calculate(self) -> float:
        """
        Calculate WACC.
        """
        total_value = self.market_cap + self.total_debt
        
        if total_value == 0:
            return 0.0

        equity_weight = self.market_cap / total_value
        debt_weight = self.total_debt / total_value

        wacc = (
            equity_weight * self.cost_of_equity() +
            debt_weight * self.after_tax_cost_of_debt()
        )

        return wacc

