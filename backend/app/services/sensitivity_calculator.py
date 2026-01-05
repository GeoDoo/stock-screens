from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SensitivityCalculator:
    """
    Calculates sensitivity matrix for DCF valuation.
    
    Varies two inputs (discount rate, terminal growth) and shows
    how intrinsic value changes across combinations.
    """
    projected_fcfs: List[float]
    projection_years: int
    shares_outstanding: float
    total_debt: float
    cash: float
    
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
        
        # Net debt adjustment
        net_debt = self.total_debt - self.cash
        equity_value = enterprise_value - net_debt
        
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


