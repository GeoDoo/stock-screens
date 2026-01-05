from dataclasses import dataclass
from typing import Optional


@dataclass
class DCFCalculator:
    current_fcf: float
    growth_rate: float
    discount_rate: float
    terminal_growth_rate: float
    projection_years: int
    shares_outstanding: float

    def calculate(self) -> dict:
        """
        Calculate intrinsic value per share using DCF model.
        
        Returns dict with:
        - projected_fcf: list of projected free cash flows
        - terminal_value: terminal value using Gordon growth model
        - enterprise_value: sum of discounted cash flows + discounted terminal value
        - intrinsic_value_per_share: enterprise value / shares outstanding
        - warning: optional warning message
        """
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
        pv_fcf = sum(
            fcf / ((1 + self.discount_rate) ** year)
            for year, fcf in enumerate(projected_fcf, start=1)
        )
        pv_terminal = terminal_value / ((1 + self.discount_rate) ** self.projection_years)

        enterprise_value = pv_fcf + pv_terminal
        result["enterprise_value"] = enterprise_value

        # Intrinsic value per share
        intrinsic_value_per_share = enterprise_value / self.shares_outstanding
        result["intrinsic_value_per_share"] = intrinsic_value_per_share

        # Warning for negative FCF
        if self.current_fcf < 0:
            result["warning"] = "Negative FCF - intrinsic value may not be meaningful"

        return result

