"""
Monte Carlo Simulation for DCF Valuation.

Runs thousands of DCF valuations with randomized inputs to produce
a probability distribution of intrinsic values.

This is far more powerful than single-point estimates because it:
1. Quantifies uncertainty explicitly
2. Shows the range of possible outcomes
3. Helps identify which assumptions matter most
4. Provides probability-weighted expected values

Usage:
    result = run_monte_carlo_valuation(
        base_revenue=1000,
        base_growth=0.10,
        growth_std=0.03,
        base_margin=0.20,
        margin_std=0.02,
        base_discount_rate=0.10,
        discount_std=0.01,
        terminal_growth=0.03,
        projection_years=5,
        iterations=10000,
    )
    
    print(f"Expected Value: ${result.mean:,.0f}")
    print(f"10th-90th percentile: ${result.percentiles['p10']:,.0f} - ${result.percentiles['p90']:,.0f}")
"""
import random
import statistics
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class MonteCarloInput:
    """
    Configuration for a single Monte Carlo input variable.
    
    Can sample from either:
    - Normal distribution (if std_dev is provided)
    - Uniform distribution (if min_value and max_value are provided)
    """
    name: str
    base_value: float
    std_dev: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    def sample(self) -> float:
        """Draw a random sample for this input."""
        if self.std_dev is not None:
            # Normal distribution
            return random.gauss(self.base_value, self.std_dev)
        elif self.min_value is not None and self.max_value is not None:
            # Uniform distribution
            return random.uniform(self.min_value, self.max_value)
        else:
            # No randomness - return base value
            return self.base_value


@dataclass
class MonteCarloResult:
    """
    Results from a Monte Carlo simulation.
    
    Contains:
    - Full distribution statistics
    - Percentiles for easy interpretation
    - Raw values for custom analysis
    """
    iterations: int
    valid_simulations: int
    values: List[float]
    mean: float
    std_dev: float
    percentiles: Dict[str, float] = field(default_factory=dict)
    
    @classmethod
    def from_values(cls, values: List[float], iterations: int) -> "MonteCarloResult":
        """Create result from list of simulated values."""
        valid_values = [v for v in values if v is not None]
        
        if not valid_values:
            return cls(
                iterations=iterations,
                valid_simulations=0,
                values=[],
                mean=0.0,
                std_dev=0.0,
                percentiles={},
            )
        
        sorted_values = sorted(valid_values)
        n = len(sorted_values)
        
        def percentile(p: float) -> float:
            """Get value at percentile p (0-100)."""
            idx = int((p / 100) * (n - 1))
            return sorted_values[idx]
        
        return cls(
            iterations=iterations,
            valid_simulations=len(valid_values),
            values=valid_values,
            mean=statistics.mean(valid_values),
            std_dev=statistics.stdev(valid_values) if len(valid_values) > 1 else 0.0,
            percentiles={
                "p5": percentile(5),
                "p10": percentile(10),
                "p25": percentile(25),
                "p50": percentile(50),  # Median
                "p75": percentile(75),
                "p90": percentile(90),
                "p95": percentile(95),
                "min": sorted_values[0],
                "max": sorted_values[-1],
            },
        )


@dataclass
class MonteCarloSimulator:
    """
    Monte Carlo simulator for valuation models.
    
    Takes a list of input configurations and a valuation function,
    then runs many iterations to produce a value distribution.
    """
    inputs: List[MonteCarloInput]
    iterations: int = 10000
    seed: Optional[int] = None
    
    def run(self, valuation_fn: Callable[[Dict[str, float]], Optional[float]]) -> MonteCarloResult:
        """
        Run Monte Carlo simulation.
        
        Args:
            valuation_fn: Function that takes dict of parameter values
                         and returns valuation (or None if invalid)
        
        Returns:
            MonteCarloResult with distribution statistics
        """
        # Set seed at run time for reproducibility
        if self.seed is not None:
            random.seed(self.seed)
        
        values = []
        
        for _ in range(self.iterations):
            # Sample all inputs
            params = {inp.name: inp.sample() for inp in self.inputs}
            
            # Run valuation
            try:
                value = valuation_fn(params)
                values.append(value)
            except Exception:
                values.append(None)
        
        return MonteCarloResult.from_values(values, self.iterations)


def run_monte_carlo_valuation(
    base_revenue: float,
    base_growth: float,
    growth_std: float,
    base_margin: float,
    margin_std: float,
    base_discount_rate: float,
    discount_std: float,
    terminal_growth: float,
    projection_years: int = 5,
    iterations: int = 10000,
    seed: Optional[int] = None,
) -> MonteCarloResult:
    """
    Run Monte Carlo simulation on a simplified DCF model.
    
    Varies:
    - Revenue growth rate (normal distribution)
    - Operating margin (normal distribution)
    - Discount rate (normal distribution)
    
    Returns distribution of enterprise values.
    """
    inputs = [
        MonteCarloInput("growth", base_growth, std_dev=growth_std),
        MonteCarloInput("margin", base_margin, std_dev=margin_std),
        MonteCarloInput("discount", base_discount_rate, std_dev=discount_std),
    ]
    
    def valuation_fn(params: Dict[str, float]) -> Optional[float]:
        growth = params["growth"]
        margin = params["margin"]
        discount = params["discount"]
        
        # Ensure valid parameters
        if discount <= terminal_growth:
            return None
        if margin < 0:
            return None
        
        # Project FCF
        revenue = base_revenue
        fcfs = []
        
        for _ in range(projection_years):
            revenue = revenue * (1 + growth)
            fcf = revenue * margin * 0.75  # Simplified: FCF ≈ EBIT margin × (1 - tax)
            fcfs.append(fcf)
        
        # Discount FCFs
        pv_fcf = sum(
            fcf / ((1 + discount) ** year)
            for year, fcf in enumerate(fcfs, start=1)
        )
        
        # Terminal value
        final_fcf = fcfs[-1]
        terminal_value = final_fcf * (1 + terminal_growth) / (discount - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount) ** projection_years)
        
        return pv_fcf + pv_terminal
    
    simulator = MonteCarloSimulator(inputs, iterations, seed)
    return simulator.run(valuation_fn)
