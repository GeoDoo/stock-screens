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
    
    Uses truncated distribution - samples from normal or Student's t,
    but rejects values outside [min_val, max_val].
    
    Fat tails (degrees_of_freedom):
    - None or very high → Normal distribution
    - 3-4 → Fat tails (recommended for finance - models crashes)
    - 5-10 → Moderate fat tails
    Note: df must be ≥ 3 for finite variance (math requirement)
    
    Student's t-distribution better models real market behavior where
    "1-in-100 year" crashes happen more often than Normal predicts.
    """
    name: str
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    degrees_of_freedom: Optional[float] = None  # None = Normal distribution
    
    def _sample_raw(self) -> float:
        """Sample from the underlying distribution (Normal or Student's t)."""
        if self.degrees_of_freedom is None or self.degrees_of_freedom > 100:
            # Normal distribution (or t with very high df ≈ Normal)
            return random.gauss(self.mean, self.std_dev)
        else:
            # Student's t-distribution with fat tails
            # t-distribution has variance = df/(df-2) for df > 2
            # We need to scale to get our target std_dev
            df = self.degrees_of_freedom
            
            # Generate standard t random variable using the ratio method
            # t = Z / sqrt(V/df) where Z ~ N(0,1) and V ~ chi-squared(df)
            z = random.gauss(0, 1)
            # Chi-squared(df) = sum of df squared standard normals
            v = sum(random.gauss(0, 1) ** 2 for _ in range(int(df)))
            t_sample = z / math.sqrt(v / df) if v > 0 else z
            
            # Scale to match desired std_dev
            # Standard t has variance df/(df-2), so std = sqrt(df/(df-2))
            # We want our target std_dev, so scale by std_dev / sqrt(df/(df-2))
            # Note: df must be > 2 for finite variance (validated in schema)
            if df > 2:
                scale = self.std_dev / math.sqrt(df / (df - 2))
            else:
                # Fallback for invalid df (should not happen with schema validation)
                # Use Normal distribution as safe default
                return random.gauss(self.mean, self.std_dev)
            
            return self.mean + scale * t_sample
    
    def sample(self) -> float:
        """Sample from truncated distribution (Normal or Student's t)."""
        # Rejection sampling for truncated distribution
        for _ in range(100):  # Max attempts to avoid infinite loop
            value = self._sample_raw()
            if self.min_val <= value <= self.max_val:
                return value
        # Fallback: clamp to bounds
        return max(self.min_val, min(self.max_val, self._sample_raw()))


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
    
    def _sample_standard(self, df: Optional[float]) -> float:
        """
        Sample from standard distribution (Normal or Student's t).
        
        For correlated sampling, we need standardized samples (mean=0, variance~1).
        When fat tails are enabled (df specified), uses Student's t-distribution.
        """
        if df is None or df > 100:
            # Standard Normal
            return random.gauss(0, 1)
        else:
            # Standard Student's t (with variance normalization)
            # Generate t random variable using ratio method
            z = random.gauss(0, 1)
            v = sum(random.gauss(0, 1) ** 2 for _ in range(int(df)))
            t_sample = z / math.sqrt(v / df) if v > 0 else z
            
            # Normalize to unit variance for correlation matrix math
            # Standard t has variance df/(df-2), so we divide by sqrt(df/(df-2))
            if df > 2:
                t_sample = t_sample / math.sqrt(df / (df - 2))
            # For df <= 2, variance is infinite but we still want fat tails
            # Just use the raw t-sample (will have very high variance)
            
            return t_sample
    
    def sample(self) -> Dict[str, float]:
        """
        Sample all inputs with correlations applied.
        
        Uses Cholesky decomposition to transform independent samples
        into correlated samples.
        
        Fat tails: If any input has degrees_of_freedom set, uses Student's t
        distribution for that input's base sample (preserving fat tail behavior
        while maintaining correlation structure).
        """
        n = len(self.inputs)
        
        # Generate independent samples (Normal or t-distribution based on each input's df)
        # This preserves fat tails for inputs that have degrees_of_freedom set
        z = [self._sample_standard(inp.degrees_of_freedom) for inp in self.inputs]
        
        # Apply Cholesky to get correlated samples
        L = self._cholesky(self.correlation_matrix)
        correlated_z = [sum(L[i][j] * z[j] for j in range(i + 1)) for i in range(n)]
        
        # Transform to bounded distributions
        result = {}
        for i, inp in enumerate(self.inputs):
            # Transform standardized sample to actual distribution
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
    
    # Simulation quality metrics
    negative_terminal_fcf_count: int = 0  # How many simulations had negative terminal FCF
    zero_equity_count: int = 0  # P0.3 Fix: How many simulations resulted in wipe-out (equity <= 0)
    warnings: List[str] = field(default_factory=list)  # Warnings about simulation quality
    
    @classmethod
    def from_simulations(
        cls,
        values: List[float],
        current_price: float,
        iterations: int,
        negative_terminal_fcf_count: int = 0,
        zero_equity_count: int = 0,  # P0.3 Fix: Track wipe-out scenarios
    ) -> "FullMonteCarloResult":
        """Create result from list of simulated per-share values."""
        # P0.3 Fix: Include zero values as valid outcomes (wipe-out scenarios)
        # Only exclude None (truly invalid scenarios like discount <= terminal_growth)
        valid_values = [v for v in values if v is not None]
        
        # Generate warnings based on simulation quality
        warnings = []
        if negative_terminal_fcf_count > 0:
            skip_pct = negative_terminal_fcf_count / iterations * 100
            if skip_pct > 50:
                warnings.append(
                    f"⚠️ CRITICAL: {skip_pct:.0f}% of simulations had negative terminal FCF and were skipped. "
                    "This company may not be suitable for DCF valuation - consider distressed valuation methods."
                )
            elif skip_pct > 20:
                warnings.append(
                    f"⚠️ WARNING: {skip_pct:.0f}% of simulations had negative terminal FCF and were skipped. "
                    "Results may not be representative - review operating margin assumptions."
                )
            elif skip_pct > 5:
                warnings.append(
                    f"Note: {skip_pct:.1f}% of simulations had negative terminal FCF and were excluded."
                )
        
        # P0.3 Fix: Warn about wipe-out scenarios (zero equity)
        if zero_equity_count > 0:
            wipeout_pct = zero_equity_count / iterations * 100
            if wipeout_pct > 30:
                warnings.append(
                    f"⚠️ WARNING: {wipeout_pct:.0f}% of simulations resulted in zero equity value (wipe-out). "
                    "This indicates high bankruptcy risk under stress scenarios."
                )
            elif wipeout_pct > 10:
                warnings.append(
                    f"Note: {wipeout_pct:.1f}% of simulations resulted in zero equity value (wipe-out). "
                    "These are included in the distribution as $0 outcomes."
                )
        
        if not valid_values:
            return cls(
                iterations=iterations,
                valid_simulations=0,
                values=[],
                mean=0.0,
                median=0.0,
                std_dev=0.0,
                negative_terminal_fcf_count=negative_terminal_fcf_count,
                zero_equity_count=zero_equity_count,
                warnings=warnings if warnings else ["No valid simulations produced values."],
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
            negative_terminal_fcf_count=negative_terminal_fcf_count,
            zero_equity_count=zero_equity_count,
            warnings=warnings,
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
    
    # NEW: Institutional equity bridge components
    minority_interest: float = 0.0,
    preferred_stock: float = 0.0,
    deferred_tax_assets: float = 0.0,  # NOLs - adds to equity
    pension_deficit: float = 0.0,
    
    # NEW: Fat tails (Student's t-distribution)
    # Markets don't follow Normal distribution - extreme events happen more often
    # - None → Normal distribution (traditional MC)
    # - 3-4 → Fat tails (recommended for finance - models crashes)
    # - 5-10 → Moderate fat tails
    # Note: df must be ≥ 3 for finite variance (math requirement)
    fat_tails_df: Optional[float] = None,
    
    # P0.1 Fix: FCFProjector integration parameters
    # These ensure Monte Carlo uses the same FCF engine as ValuationService
    wc_mode: str = "level",  # "level" or "incremental" - passed to FCFProjector
    margin_schedule: Optional[List[float]] = None,  # Per-year margins for multi-stage economics
    da_schedule: Optional[List[float]] = None,  # Per-year D&A ratios
    capex_schedule: Optional[List[float]] = None,  # Per-year CapEx ratios
    wc_schedule: Optional[List[float]] = None,  # Per-year WC ratios
    
    # P0.2 Fix: SBC dilution support
    # Same as ValuationService: terminal_shares = shares * (1 + rate)^years
    annual_dilution_rate: float = 0.0,  # Annual share growth from SBC (e.g., 0.03 for 3%)
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
                0.2, 3.0,  # Reasonable beta range
                fat_tails_df,  # Consistent with other inputs
            )
        if mrp_std > 0:
            wacc_inputs["mrp"] = BoundedInput(
                "mrp",
                wacc_components["market_risk_premium"],
                mrp_std,
                0.03, 0.10,  # 3% to 10% MRP range
                fat_tails_df,  # Consistent with other inputs
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
        BoundedInput("margin", base_margin, margin_std, -0.20, 0.50, fat_tails_df),  # -20% to +50%
        BoundedInput("da_ratio", base_da_ratio, da_ratio_std, 0.0, 0.15, fat_tails_df),  # 0% to 15%
        BoundedInput("capex_ratio", base_capex_ratio, capex_ratio_std, 0.0, 0.25, fat_tails_df),  # 0% to 25%
        BoundedInput("wc_ratio", base_wc_ratio, wc_ratio_std, -0.15, 0.30, fat_tails_df),  # -15% to +30%
        BoundedInput("terminal_growth", base_terminal_growth, terminal_growth_std, 0.01, 0.05, fat_tails_df),  # 1% to 5%
    ]
    
    # Add growth input only if NOT using multi-stage
    if not use_multi_stage:
        core_inputs.insert(0, BoundedInput("growth", effective_base_growth, growth_std, -0.10, 0.50, fat_tails_df))
    
    # Add discount input only if NOT using WACC components at all.
    # When WACC components are provided (even without sampling std devs),
    # use the computed WACC directly, don't sample discount rate.
    if not wacc_sampling_enabled:
        core_inputs.append(BoundedInput("discount", effective_discount_rate, discount_std, 0.04, 0.25, fat_tails_df))
    
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
    
    # Full institutional equity bridge for EV → Equity conversion
    # Equity = EV - Net Debt - Minority Interest - Preferred + NOLs - Pension
    net_debt = total_debt - cash
    equity_bridge_adjustment = (
        - minority_interest
        - preferred_stock
        + deferred_tax_assets
        - pension_deficit
    )
    
    # Mid-year discounting offset
    discount_offset = 0.5 if use_mid_year_discounting else 0.0
    
    per_share_values = []
    negative_terminal_fcf_count = 0  # Track simulations skipped due to negative terminal FCF
    zero_equity_count = 0  # P0.3 Fix: Track wipe-out scenarios (equity <= 0)
    
    # P0.2 Fix: Calculate terminal shares with dilution (same as ValuationService)
    # Dilution is applied for the ACTUAL projection period, not the original parameter.
    # When growth_stages is provided, projection_years is overwritten at line ~472
    # to sum(stage.years), so the effective projection period changes.
    # terminal_shares is calculated inside each iteration using actual_years
    # (= len(growth_schedule)) to ensure consistency.
    
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
            # P0.1 Fix: Use FCFProjector.project() for FCF calculations
            # This ensures Monte Carlo uses the same engine as ValuationService
            
            # Handle empty historical_working_capital
            # FCFProjector requires WC history for prior_wc baseline
            # If empty, synthesize from historical_revenue * wc_ratio
            effective_wc_history = historical_working_capital
            if not historical_working_capital and historical_revenue:
                # Use revenue-based WC baseline
                effective_wc_history = [rev * wc_ratio for rev in historical_revenue]
            
            projector = FCFProjector(
                historical_revenue=historical_revenue,
                historical_ebit=historical_ebit,
                historical_da=historical_da,
                historical_capex=historical_capex,
                historical_working_capital=effective_wc_history,
                tax_rate=base_tax_rate,
                wc_mode=wc_mode,  # P0.1: Respect wc_mode parameter
            )
            
            # Build per-year schedules from sampled values
            # If user provided a schedule, perturb it; otherwise use constant sampled value
            actual_years = len(growth_schedule)
            
            # Create schedules for this simulation run
            # Margin schedule: perturb user schedule or use constant sampled margin
            sim_margin_schedule = None
            if margin_schedule is not None:
                # User provided schedule - we could perturb each value, but for consistency
                # with the sampling model, use the sampled margin as a multiplier
                sim_margin_schedule = margin_schedule  # Use as-is for now
            # If no schedule, FCFProjector will use the constant margin
            
            sim_da_schedule = da_schedule  # Pass through user schedule if provided
            sim_capex_schedule = capex_schedule  # Pass through user schedule if provided  
            sim_wc_schedule = wc_schedule  # Pass through user schedule if provided
            
            # Project using FCFProjector (respects wc_mode and all schedules)
            fcf_projections = projector.project(
                years=actual_years,
                revenue_growth=None,  # Use growth_schedule instead
                operating_margin=margin if sim_margin_schedule is None else None,
                da_ratio=da_ratio if sim_da_schedule is None else None,
                capex_ratio=capex_ratio if sim_capex_schedule is None else None,
                wc_ratio=wc_ratio if sim_wc_schedule is None else None,
                wc_mode=wc_mode,  # P0.1: Pass wc_mode to projection
                growth_schedule=growth_schedule,
                margin_schedule=sim_margin_schedule,
                da_schedule=sim_da_schedule,
                capex_schedule=sim_capex_schedule,
                wc_schedule=sim_wc_schedule,
            )
            
            fcf_values = [p["fcf"] for p in fcf_projections]
            
            # Discount FCFs with optional mid-year convention
            pv_fcf = sum(
                fcf / ((1 + discount) ** (year - discount_offset))
                for year, fcf in enumerate(fcf_values, start=1)
            )
            
            # Terminal value (Gordon growth)
            # IMPORTANT: Gordon Growth Model requires non-negative terminal FCF
            # Negative terminal FCF means the business is not a going concern
            # in this scenario - skip rather than use arbitrary multiples
            # Zero terminal FCF is valid (TV = 0) and should NOT be skipped
            final_fcf = fcf_values[-1]
            if final_fcf < 0:
                # Skip this simulation - Gordon Growth Model doesn't apply
                negative_terminal_fcf_count += 1
                per_share_values.append(None)
                continue
            
            # Zero FCF gives TV = 0, positive FCF gives standard Gordon Growth
            terminal_value = final_fcf * (1 + terminal_growth) / (discount - terminal_growth)
            terminal_discount_period = actual_years - discount_offset
            pv_terminal = terminal_value / ((1 + discount) ** terminal_discount_period)
            
            enterprise_value = pv_fcf + pv_terminal
            
            # EV → Equity → Per Share (full institutional equity bridge)
            equity_value = enterprise_value - net_debt + equity_bridge_adjustment
            
            # P0.2 Fix: Use terminal shares with dilution (same as ValuationService)
            # terminal_shares = current_shares * ((1 + annual_dilution_rate) ** projection_years)
            terminal_shares = shares_outstanding * ((1 + annual_dilution_rate) ** actual_years)
            per_share = equity_value / terminal_shares if terminal_shares > 0 else 0
            
            # P0.3 Fix: Keep negative/zero outcomes as 0 (wipe-out), don't drop them
            # This prevents upward bias in mean/percentiles and tracks bankruptcy risk
            if per_share <= 0:
                zero_equity_count += 1
                per_share_values.append(0.0)  # Clamp to 0, keep in distribution
            else:
                per_share_values.append(per_share)
            
        except Exception:
            per_share_values.append(None)
    
    return FullMonteCarloResult.from_simulations(
        values=per_share_values,
        current_price=current_price,
        iterations=iterations,
        negative_terminal_fcf_count=negative_terminal_fcf_count,
        zero_equity_count=zero_equity_count,
    )
