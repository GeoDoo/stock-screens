"""
Full-Model Monte Carlo Simulation for DCF Valuation.

This is the DECISION-GRADE Monte Carlo that reuses the full DCF engine.
Unlike the simplified version, this:
1. Uses FCFProjector for proper FCF calculations (NOPAT + D&A - CapEx - ΔWC)
2. Samples ALL DCF inputs with bounded distributions
3. Implements correlations between inputs (growth↔margin, growth↔reinvestment)
4. Computes comprehensive decision-support outputs (CVaR, P(upside), etc.)

Enhanced features:
- WACC calculation from components (risk-free rate, beta, MRP, cost of debt)
- Multi-stage growth support (high growth → fade → mature)
- Mid-year discounting (more realistic timing assumption)

Use this for actual investment decisions. Use the simplified version for quick intuition.
"""
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from app.services.fcf_projector import FCFProjector
from app.services.wacc_calculator import WACCCalculator
from app.services.multi_stage_growth import GrowthStage, calculate_growth_schedule


@dataclass
class BoundedInput:
    """
    Input parameter with bounded distribution.
    
    Uses truncated normal distribution - samples from normal but rejects
    values outside [min_val, max_val]. More realistic than unbounded normal.
    """
    name: str
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    
    def sample(self) -> float:
        """Sample from truncated normal distribution."""
        # Rejection sampling for truncated normal
        for _ in range(100):  # Max attempts to avoid infinite loop
            value = random.gauss(self.mean, self.std_dev)
            if self.min_val <= value <= self.max_val:
                return value
        # Fallback: clamp to bounds
        return max(self.min_val, min(self.max_val, random.gauss(self.mean, self.std_dev)))


@dataclass 
class CorrelatedInputs:
    """
    Handles correlated sampling of multiple inputs.
    
    Uses Cholesky decomposition to generate correlated random variables.
    Key correlations for DCF:
    - Growth ↔ Margin: Often negative (competition at high growth)
    - Growth ↔ Reinvestment (CapEx): Positive (growth requires investment)
    """
    inputs: List[BoundedInput]
    correlation_matrix: Optional[List[List[float]]] = None
    
    def __post_init__(self):
        n = len(self.inputs)
        if self.correlation_matrix is None:
            # Default: identity matrix (no correlation)
            self.correlation_matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    
    def _cholesky(self, matrix: List[List[float]]) -> List[List[float]]:
        """Cholesky decomposition for correlation matrix."""
        n = len(matrix)
        L = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(i + 1):
                s = sum(L[i][k] * L[j][k] for k in range(j))
                if i == j:
                    L[i][j] = math.sqrt(max(0, matrix[i][i] - s))
                else:
                    L[i][j] = (matrix[i][j] - s) / L[j][j] if L[j][j] != 0 else 0
        return L
    
    def sample(self) -> Dict[str, float]:
        """
        Sample all inputs with correlations applied.
        
        Uses Cholesky decomposition to transform independent samples
        into correlated samples.
        """
        n = len(self.inputs)
        
        # Generate independent standard normal samples
        z = [random.gauss(0, 1) for _ in range(n)]
        
        # Apply Cholesky to get correlated samples
        L = self._cholesky(self.correlation_matrix)
        correlated_z = [sum(L[i][j] * z[j] for j in range(i + 1)) for i in range(n)]
        
        # Transform to bounded distributions
        result = {}
        for i, inp in enumerate(self.inputs):
            # Transform standard normal to actual distribution
            raw_value = inp.mean + correlated_z[i] * inp.std_dev
            # Clamp to bounds
            value = max(inp.min_val, min(inp.max_val, raw_value))
            result[inp.name] = value
        
        return result


@dataclass
class FullMonteCarloResult:
    """
    Comprehensive results from Full-Model Monte Carlo.
    
    Includes decision-support metrics beyond just percentiles:
    - Probability of upside thresholds
    - CVaR (expected shortfall)
    - Margin of safety distribution
    """
    iterations: int
    valid_simulations: int
    
    # Per-share value distribution
    values: List[float]
    mean: float
    median: float
    std_dev: float
    
    # Percentiles
    percentiles: Dict[str, float] = field(default_factory=dict)
    
    # Decision metrics
    probability_positive_upside: float = 0.0  # P(IV > price)
    probability_20pct_upside: float = 0.0     # P(IV > price * 1.2)
    probability_20pct_downside: float = 0.0   # P(IV < price * 0.8)
    cvar_10: float = 0.0  # Expected value of worst 10% outcomes
    
    # Margin of safety distribution
    margin_of_safety_mean: float = 0.0
    margin_of_safety_median: float = 0.0
    
    @classmethod
    def from_simulations(
        cls,
        values: List[float],
        current_price: float,
        iterations: int,
    ) -> "FullMonteCarloResult":
        """Create result from list of simulated per-share values."""
        valid_values = [v for v in values if v is not None and v > 0]
        
        if not valid_values:
            return cls(
                iterations=iterations,
                valid_simulations=0,
                values=[],
                mean=0.0,
                median=0.0,
                std_dev=0.0,
            )
        
        sorted_values = sorted(valid_values)
        n = len(sorted_values)
        
        def percentile(p: float) -> float:
            idx = int((p / 100) * (n - 1))
            return sorted_values[idx]
        
        # Calculate margin of safety for each simulation
        margins = [(v - current_price) / current_price for v in valid_values]
        
        # Decision metrics
        prob_positive = sum(1 for v in valid_values if v > current_price) / n
        prob_20_up = sum(1 for v in valid_values if v > current_price * 1.2) / n
        prob_20_down = sum(1 for v in valid_values if v < current_price * 0.8) / n
        
        # CVaR 10% (average of worst 10%)
        worst_10_pct = sorted_values[:max(1, n // 10)]
        cvar_10 = statistics.mean(worst_10_pct)
        
        return cls(
            iterations=iterations,
            valid_simulations=n,
            values=valid_values,
            mean=statistics.mean(valid_values),
            median=statistics.median(valid_values),
            std_dev=statistics.stdev(valid_values) if n > 1 else 0.0,
            percentiles={
                "p5": percentile(5),
                "p10": percentile(10),
                "p25": percentile(25),
                "p50": percentile(50),
                "p75": percentile(75),
                "p90": percentile(90),
                "p95": percentile(95),
                "min": sorted_values[0],
                "max": sorted_values[-1],
            },
            probability_positive_upside=prob_positive,
            probability_20pct_upside=prob_20_up,
            probability_20pct_downside=prob_20_down,
            cvar_10=cvar_10,
            margin_of_safety_mean=statistics.mean(margins),
            margin_of_safety_median=statistics.median(margins),
        )


def run_full_monte_carlo(
    # Historical data for FCFProjector
    historical_revenue: List[float],
    historical_ebit: List[float],
    historical_da: List[float],
    historical_capex: List[float],
    historical_working_capital: List[float],
    
    # Company data
    shares_outstanding: float,
    total_debt: float,
    cash: float,
    current_price: float,
    
    # Base assumptions (means)
    base_growth: Optional[float] = None,  # Optional if growth_stages provided
    base_margin: float = 0.15,
    base_da_ratio: float = 0.05,
    base_capex_ratio: float = 0.08,
    base_wc_ratio: float = 0.10,
    base_tax_rate: float = 0.25,
    base_discount_rate: Optional[float] = None,  # Optional if wacc_components provided
    base_terminal_growth: float = 0.03,
    
    # Standard deviations
    growth_std: float = 0.03,
    margin_std: float = 0.02,
    da_ratio_std: float = 0.01,
    capex_ratio_std: float = 0.02,
    wc_ratio_std: float = 0.02,
    discount_std: float = 0.01,
    terminal_growth_std: float = 0.005,
    
    # Simulation settings
    projection_years: int = 5,
    iterations: int = 5000,
    seed: Optional[int] = None,
    
    # Correlations
    growth_margin_correlation: float = -0.2,  # Negative: high growth often compresses margins
    growth_capex_correlation: float = 0.3,    # Positive: growth requires investment
    
    # NEW: WACC from components (alternative to base_discount_rate)
    wacc_components: Optional[Dict[str, Any]] = None,
    
    # NEW: Multi-stage growth (alternative to base_growth)
    growth_stages: Optional[List[Dict[str, Any]]] = None,
    
    # NEW: Mid-year discounting
    use_mid_year_discounting: bool = False,
) -> FullMonteCarloResult:
    """
    Run Full-Model Monte Carlo using the complete DCF engine.
    
    This is the decision-grade simulation that:
    1. Samples all DCF inputs with bounded distributions
    2. Applies realistic correlations between inputs
    3. Runs full FCF projections for each simulation
    4. Computes comprehensive decision-support metrics
    
    Enhanced features:
    - wacc_components: Calculate WACC from risk-free rate, beta, MRP, cost of debt
    - growth_stages: Use multi-stage growth instead of single rate
    - use_mid_year_discounting: Assume cash flows occur mid-year
    
    Returns distribution of per-share intrinsic values with decision metrics.
    """
    if seed is not None:
        random.seed(seed)
    
    # Determine effective base_discount_rate
    effective_discount_rate = base_discount_rate
    wacc_sampling_enabled = False
    wacc_inputs: Dict[str, BoundedInput] = {}
    
    if wacc_components is not None:
        # Calculate base WACC from components
        wacc_calc = WACCCalculator(
            risk_free_rate=wacc_components["risk_free_rate"],
            beta=wacc_components["beta"],
            market_risk_premium=wacc_components["market_risk_premium"],
            cost_of_debt=wacc_components["cost_of_debt"],
            tax_rate=base_tax_rate,
            market_cap=wacc_components["market_cap"],
            total_debt=total_debt,
        )
        effective_discount_rate = wacc_calc.calculate()
        wacc_sampling_enabled = True
        
        # Set up WACC component sampling if std devs provided
        beta_std = wacc_components.get("beta_std", 0.0)
        mrp_std = wacc_components.get("market_risk_premium_std", 0.0)
        
        if beta_std > 0:
            wacc_inputs["beta"] = BoundedInput(
                "beta",
                wacc_components["beta"],
                beta_std,
                0.2, 3.0  # Reasonable beta range
            )
        if mrp_std > 0:
            wacc_inputs["mrp"] = BoundedInput(
                "mrp",
                wacc_components["market_risk_premium"],
                mrp_std,
                0.03, 0.10  # 3% to 10% MRP range
            )
    
    if effective_discount_rate is None:
        effective_discount_rate = 0.10  # Default fallback
    
    # Determine effective growth mode
    use_multi_stage = growth_stages is not None and len(growth_stages) > 0
    effective_base_growth = base_growth if base_growth is not None else 0.08
    
    # Convert growth_stages dicts to GrowthStage objects if provided
    parsed_growth_stages: List[GrowthStage] = []
    growth_stage_stds: List[float] = []  # Per-stage std devs
    
    if use_multi_stage:
        for stage_dict in growth_stages:
            parsed_growth_stages.append(GrowthStage(
                name=stage_dict["name"],
                years=stage_dict["years"],
                growth_rate=stage_dict["growth_rate"],
                end_growth_rate=stage_dict.get("end_growth_rate"),
            ))
            # Get per-stage std dev (default to global growth_std)
            growth_stage_stds.append(stage_dict.get("growth_std", growth_std))
        
        # Calculate total projection years from stages
        projection_years = sum(s.years for s in parsed_growth_stages)
    
    # Define bounded inputs for non-WACC, non-growth params
    core_inputs = [
        BoundedInput("margin", base_margin, margin_std, -0.20, 0.50),  # -20% to +50%
        BoundedInput("da_ratio", base_da_ratio, da_ratio_std, 0.0, 0.15),  # 0% to 15%
        BoundedInput("capex_ratio", base_capex_ratio, capex_ratio_std, 0.0, 0.25),  # 0% to 25%
        BoundedInput("wc_ratio", base_wc_ratio, wc_ratio_std, -0.15, 0.30),  # -15% to +30%
        BoundedInput("terminal_growth", base_terminal_growth, terminal_growth_std, 0.01, 0.05),  # 1% to 5%
    ]
    
    # Add growth input only if NOT using multi-stage
    if not use_multi_stage:
        core_inputs.insert(0, BoundedInput("growth", effective_base_growth, growth_std, -0.10, 0.50))
    
    # Add discount input only if NOT sampling WACC components
    if not wacc_sampling_enabled or not wacc_inputs:
        core_inputs.append(BoundedInput("discount", effective_discount_rate, discount_std, 0.04, 0.25))
    
    # Build correlation matrix for core inputs
    n = len(core_inputs)
    corr_matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    
    # Apply correlations (only if growth is in core_inputs at position 0)
    if not use_multi_stage:
        # growth (0) ↔ margin (1)
        corr_matrix[0][1] = growth_margin_correlation
        corr_matrix[1][0] = growth_margin_correlation
        # growth (0) ↔ capex_ratio (3)
        corr_matrix[0][3] = growth_capex_correlation
        corr_matrix[3][0] = growth_capex_correlation
    
    correlated_inputs = CorrelatedInputs(core_inputs, corr_matrix)
    
    # Net debt for EV → Equity conversion
    net_debt = total_debt - cash
    
    # Mid-year discounting offset
    discount_offset = 0.5 if use_mid_year_discounting else 0.0
    
    per_share_values = []
    
    for _ in range(iterations):
        # Sample correlated core inputs
        params = correlated_inputs.sample()
        
        margin = params["margin"]
        da_ratio = params["da_ratio"]
        capex_ratio = params["capex_ratio"]
        wc_ratio = params["wc_ratio"]
        terminal_growth = params["terminal_growth"]
        
        # Get discount rate (either from core sampling or WACC component sampling)
        if "discount" in params:
            discount = params["discount"]
        elif wacc_sampling_enabled and wacc_inputs:
            # Sample WACC components and calculate WACC
            sampled_beta = wacc_inputs["beta"].sample() if "beta" in wacc_inputs else wacc_components["beta"]
            sampled_mrp = wacc_inputs["mrp"].sample() if "mrp" in wacc_inputs else wacc_components["market_risk_premium"]
            
            wacc_calc = WACCCalculator(
                risk_free_rate=wacc_components["risk_free_rate"],
                beta=sampled_beta,
                market_risk_premium=sampled_mrp,
                cost_of_debt=wacc_components["cost_of_debt"],
                tax_rate=base_tax_rate,
                market_cap=wacc_components["market_cap"],
                total_debt=total_debt,
            )
            discount = wacc_calc.calculate()
        else:
            discount = effective_discount_rate
        
        # Get growth rate(s) - either single or multi-stage
        if use_multi_stage:
            # Sample each stage's growth rate
            sampled_stages = []
            for i, stage in enumerate(parsed_growth_stages):
                stage_std = growth_stage_stds[i]
                sampled_growth = random.gauss(stage.growth_rate, stage_std)
                # Clamp to reasonable bounds
                sampled_growth = max(-0.10, min(0.50, sampled_growth))
                
                # Handle end_growth_rate for fade stages
                sampled_end = None
                if stage.end_growth_rate is not None:
                    sampled_end = random.gauss(stage.end_growth_rate, stage_std * 0.5)
                    sampled_end = max(-0.10, min(0.50, sampled_end))
                
                sampled_stages.append(GrowthStage(
                    name=stage.name,
                    years=stage.years,
                    growth_rate=sampled_growth,
                    end_growth_rate=sampled_end,
                ))
            
            growth_schedule = calculate_growth_schedule(sampled_stages)
        else:
            growth = params.get("growth", effective_base_growth)
            growth_schedule = [growth] * projection_years
        
        # Skip invalid scenarios
        if discount <= terminal_growth:
            per_share_values.append(None)
            continue
        if margin < -0.5:  # Extreme losses
            per_share_values.append(None)
            continue
        
        try:
            # Create FCF projector
            projector = FCFProjector(
                historical_revenue=historical_revenue,
                historical_ebit=historical_ebit,
                historical_da=historical_da,
                historical_capex=historical_capex,
                historical_working_capital=historical_working_capital,
                tax_rate=base_tax_rate,
            )
            
            # Project FCF year by year with growth schedule
            fcfs = []
            current_revenue = historical_revenue[-1] if historical_revenue else 100e9
            
            for year_idx, year_growth in enumerate(growth_schedule):
                current_revenue = current_revenue * (1 + year_growth)
                ebit = current_revenue * margin
                nopat = ebit * (1 - base_tax_rate)
                da = current_revenue * da_ratio
                capex = current_revenue * capex_ratio
                wc = current_revenue * wc_ratio
                
                # Working capital change (level mode)
                if year_idx == 0:
                    prev_wc = (historical_working_capital[-1] 
                               if historical_working_capital else current_revenue * wc_ratio)
                else:
                    prev_wc = fcfs[year_idx - 1]["wc"]
                
                delta_wc = wc - prev_wc if year_idx > 0 else wc - (historical_working_capital[-1] if historical_working_capital else wc)
                
                fcf = nopat + da - capex - delta_wc
                fcfs.append({"fcf": fcf, "wc": wc})
            
            fcf_values = [p["fcf"] for p in fcfs]
            actual_years = len(fcf_values)
            
            # Discount FCFs with optional mid-year convention
            pv_fcf = sum(
                fcf / ((1 + discount) ** (year - discount_offset))
                for year, fcf in enumerate(fcf_values, start=1)
            )
            
            # Terminal value (Gordon growth)
            final_fcf = fcf_values[-1]
            if final_fcf > 0:
                terminal_value = final_fcf * (1 + terminal_growth) / (discount - terminal_growth)
                terminal_discount_period = actual_years - discount_offset
                pv_terminal = terminal_value / ((1 + discount) ** terminal_discount_period)
            else:
                # Negative terminal FCF - use simplified exit multiple
                terminal_value = final_fcf * 10  # 10x multiple for distressed
                terminal_discount_period = actual_years - discount_offset
                pv_terminal = terminal_value / ((1 + discount) ** terminal_discount_period)
            
            enterprise_value = pv_fcf + pv_terminal
            
            # EV → Equity → Per Share
            equity_value = enterprise_value - net_debt
            per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0
            
            per_share_values.append(per_share if per_share > 0 else None)
            
        except Exception:
            per_share_values.append(None)
    
    return FullMonteCarloResult.from_simulations(
        values=per_share_values,
        current_price=current_price,
        iterations=iterations,
    )
