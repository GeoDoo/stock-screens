"""
Multi-Stage Growth Model for DCF Valuation.

Addresses one of the biggest criticisms of DCF: the assumption of constant growth.

Instead of assuming a single growth rate for all projection years, this model
supports multiple stages with optional fade (decay) between rates:

1. High Growth Phase: High but declining growth (e.g., 25-30%)
2. Fade Phase: Linear transition from high to stable growth
3. Mature Phase: Stable, sustainable growth approaching terminal rate
4. Terminal: Gordon Growth Model with perpetual growth (e.g., 2-3%)

Example:
    Year 1-3:  25% growth (hypergrowth)
    Year 4-6:  25% → 10% fade (competitive pressure)
    Year 7-10: 5% growth (mature)
    Terminal:  3% perpetuity

This is how institutional investors actually model companies.

Operating Leverage Enhancement:
    For capital-intensive businesses (airlines, manufacturers, utilities),
    margins don't fade linearly. They behave as step functions due to
    high fixed costs creating operating leverage:
    
    - Flat at low margin while capacity is being filled
    - Jump to high margin when utilization exceeds threshold
    - Flat again until next capacity investment
    
    This is modeled via FadeMode.STEP with margin_step_at_year.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class FadeMode(Enum):
    """
    How values transition from start to end over a growth stage.
    
    LINEAR: Smooth linear interpolation (default, good for most companies)
    STEP: Step function that jumps at a specific year (for operating leverage)
    """
    LINEAR = "linear"
    STEP = "step"


@dataclass
class GrowthStage:
    """
    A single growth phase in a multi-stage model.
    
    If end_* fields are provided, the stage will fade from start to end
    values over the years. The fade can be:
    - LINEAR (default): Smooth linear interpolation
    - STEP: Jump at a specific year (for operating leverage modeling)
    
    Economics fields (margin, capex, wc) allow modeling how a company's
    unit economics evolve as it matures - critical for accurate DCF.
    
    Operating Leverage (Step Function):
        For capital-intensive businesses, set margin_fade_mode=FadeMode.STEP
        and margin_step_at_year=N to model the capacity fill effect:
        - Years 1 to (N-1): margin stays at operating_margin (low utilization)
        - Years N onwards: margin jumps to end_operating_margin (capacity filled)
    """
    name: str
    years: int
    growth_rate: float
    end_growth_rate: Optional[float] = None  # If set, fade to this rate
    
    # Economics - operating margin as % of revenue
    operating_margin: Optional[float] = None
    end_operating_margin: Optional[float] = None
    margin_fade_mode: FadeMode = FadeMode.LINEAR
    margin_step_at_year: Optional[int] = None  # For STEP mode: year when margin jumps
    
    # Economics - CapEx as % of revenue  
    capex_ratio: Optional[float] = None
    end_capex_ratio: Optional[float] = None
    
    # Economics - Working Capital as % of revenue
    wc_ratio: Optional[float] = None
    end_wc_ratio: Optional[float] = None
    
    def __post_init__(self):
        """Validate step parameters."""
        if self.margin_fade_mode == FadeMode.STEP:
            if self.margin_step_at_year is None:
                raise ValueError(
                    "margin_step_at_year is required when margin_fade_mode=STEP"
                )
            if self.margin_step_at_year < 1 or self.margin_step_at_year > self.years:
                raise ValueError(
                    f"margin_step_at_year ({self.margin_step_at_year}) must be "
                    f"between 1 and years ({self.years})"
                )


def create_fade_schedule(
    start_rate: float,
    end_rate: float,
    years: int,
) -> List[float]:
    """
    Create a linear fade schedule from start_rate to end_rate.
    
    Returns list of growth rates for each year.
    Year 1 gets start_rate, final year approaches end_rate.
    """
    if years <= 1:
        return [start_rate]
    
    schedule = []
    step = (end_rate - start_rate) / (years - 1)
    
    for i in range(years):
        rate = start_rate + (step * i)
        schedule.append(rate)
    
    return schedule


def create_step_schedule(
    start_value: float,
    end_value: float,
    years: int,
    step_at_year: int,
) -> List[float]:
    """
    Create a step function schedule for operating leverage modeling.
    
    For capital-intensive businesses, margins don't fade linearly.
    Instead, they stay flat until capacity fills, then jump.
    
    Args:
        start_value: Value before the step (e.g., low margin during capacity fill)
        end_value: Value after the step (e.g., high margin when capacity filled)
        years: Total years in the stage
        step_at_year: Year when the step occurs (1-indexed, within years)
    
    Returns:
        List of values, flat at start_value until step_at_year, then end_value
    
    Example:
        create_step_schedule(0.08, 0.22, 5, 3)
        -> [0.08, 0.08, 0.22, 0.22, 0.22]
        # Margin stays at 8% for years 1-2, jumps to 22% at year 3
    """
    if years <= 0:
        return []
    
    if step_at_year < 1:
        step_at_year = 1
    if step_at_year > years:
        step_at_year = years
    
    schedule = []
    for year in range(1, years + 1):
        if year < step_at_year:
            schedule.append(start_value)
        else:
            schedule.append(end_value)
    
    return schedule


def calculate_growth_schedule(stages: List[GrowthStage]) -> List[float]:
    """
    Convert list of growth stages to year-by-year growth schedule.
    
    Handles both constant-rate stages and fade stages.
    """
    schedule = []
    
    for stage in stages:
        if stage.end_growth_rate is not None:
            # Fade stage
            stage_schedule = create_fade_schedule(
                start_rate=stage.growth_rate,
                end_rate=stage.end_growth_rate,
                years=stage.years,
            )
            schedule.extend(stage_schedule)
        else:
            # Constant rate stage
            schedule.extend([stage.growth_rate] * stage.years)
    
    return schedule


def calculate_economics_schedule(
    stages: List[GrowthStage],
    start_attr: str,
    end_attr: str,
    fade_mode_attr: Optional[str] = None,
    step_at_year_attr: Optional[str] = None,
) -> Optional[List[float]]:
    """
    Calculate year-by-year schedule for an economics metric (margin, capex, wc).
    
    Supports two fade modes:
    - LINEAR (default): Smooth linear interpolation
    - STEP: Jump at a specific year (for operating leverage modeling)
    
    Args:
        stages: List of growth stages
        start_attr: Attribute name for start value (e.g., 'operating_margin')
        end_attr: Attribute name for end value (e.g., 'end_operating_margin')
        fade_mode_attr: Attribute name for fade mode (e.g., 'margin_fade_mode')
        step_at_year_attr: Attribute name for step year (e.g., 'margin_step_at_year')
    
    Returns:
        List of values per year, or None if metric not specified in any stage
    """
    # Check if any stage has this metric
    has_metric = any(getattr(stage, start_attr) is not None for stage in stages)
    if not has_metric:
        return None
    
    schedule = []
    
    for stage in stages:
        start_value = getattr(stage, start_attr)
        end_value = getattr(stage, end_attr)
        
        # Get fade mode and step parameters if applicable
        fade_mode = FadeMode.LINEAR
        step_at_year = None
        if fade_mode_attr:
            fade_mode = getattr(stage, fade_mode_attr, FadeMode.LINEAR) or FadeMode.LINEAR
        if step_at_year_attr:
            step_at_year = getattr(stage, step_at_year_attr, None)
        
        if start_value is None:
            # No value for this stage - use None placeholders
            schedule.extend([None] * stage.years)
        elif end_value is not None:
            # Fade stage - choose fade method based on mode
            if fade_mode == FadeMode.STEP and step_at_year is not None:
                stage_schedule = create_step_schedule(
                    start_value=start_value,
                    end_value=end_value,
                    years=stage.years,
                    step_at_year=step_at_year,
                )
            else:
                # Default to linear fade
                stage_schedule = create_fade_schedule(
                    start_rate=start_value,
                    end_rate=end_value,
                    years=stage.years,
                )
            schedule.extend(stage_schedule)
        else:
            # Constant value stage
            schedule.extend([start_value] * stage.years)
    
    return schedule


@dataclass
class MultiStageGrowthModel:
    """
    Multi-stage growth model for realistic DCF projections.
    
    Supports fading not just revenue growth, but also unit economics:
    - Operating margin
    - CapEx as % of revenue
    - Working capital as % of revenue
    
    Usage:
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("High Growth", years=3, growth_rate=0.20,
                           operating_margin=0.25, capex_ratio=0.12, wc_ratio=0.15),
                GrowthStage("Fade", years=4, growth_rate=0.20, end_growth_rate=0.08,
                           operating_margin=0.25, end_operating_margin=0.18,
                           capex_ratio=0.12, end_capex_ratio=0.06,
                           wc_ratio=0.15, end_wc_ratio=0.10),
                GrowthStage("Mature", years=3, growth_rate=0.05,
                           operating_margin=0.18, capex_ratio=0.06, wc_ratio=0.10),
            ],
            terminal_growth_rate=0.03,
        )
        
        projections = model.project_economics(base_revenue=1000)
    
    Note: stages is converted to tuple in __post_init__ to prevent mutation
    that would cause schedule length mismatches.
    """
    stages: List[GrowthStage]
    terminal_growth_rate: float
    _growth_schedule: List[float] = field(default_factory=list, init=False)
    _margin_schedule: Optional[List[float]] = field(default=None, init=False)
    _capex_schedule: Optional[List[float]] = field(default=None, init=False)
    _wc_schedule: Optional[List[float]] = field(default=None, init=False)
    
    def __post_init__(self):
        if not self.stages:
            raise ValueError("Multi-stage growth model requires at least one growth stage")
        
        # Convert stages to tuple to prevent mutation after schedule calculation
        # This ensures total_projection_years always matches schedule lengths
        object.__setattr__(self, 'stages', tuple(self.stages))
        
        self._growth_schedule = calculate_growth_schedule(self.stages)
        # Margin schedule supports step function for operating leverage modeling
        self._margin_schedule = calculate_economics_schedule(
            self.stages, 'operating_margin', 'end_operating_margin',
            fade_mode_attr='margin_fade_mode',
            step_at_year_attr='margin_step_at_year',
        )
        self._capex_schedule = calculate_economics_schedule(
            self.stages, 'capex_ratio', 'end_capex_ratio'
        )
        self._wc_schedule = calculate_economics_schedule(
            self.stages, 'wc_ratio', 'end_wc_ratio'
        )
    
    @property
    def total_projection_years(self) -> int:
        """Total years covered by all stages."""
        return sum(stage.years for stage in self.stages)
    
    @property
    def growth_schedule(self) -> List[float]:
        """Year-by-year growth rates."""
        return self._growth_schedule
    
    @property
    def margin_schedule(self) -> Optional[List[float]]:
        """Year-by-year operating margins, or None if not specified."""
        return self._margin_schedule
    
    @property
    def capex_schedule(self) -> Optional[List[float]]:
        """Year-by-year CapEx ratios, or None if not specified."""
        return self._capex_schedule
    
    @property
    def wc_schedule(self) -> Optional[List[float]]:
        """Year-by-year working capital ratios, or None if not specified."""
        return self._wc_schedule
    
    def project_revenue(self, base_revenue: float) -> List[float]:
        """
        Project revenue for each year using the growth schedule.
        
        Args:
            base_revenue: Starting revenue (last historical year)
            
        Returns:
            List of projected revenues for each year
        """
        revenues = []
        current_revenue = base_revenue
        
        for growth_rate in self._growth_schedule:
            current_revenue = current_revenue * (1 + growth_rate)
            revenues.append(current_revenue)
        
        return revenues
    
    def project_economics(self, base_revenue: float) -> List[Dict[str, Any]]:
        """
        Project complete economics for each year.
        
        Returns list of dicts with revenue and economics metrics for each year.
        Metrics not specified in stages will be None.
        
        Args:
            base_revenue: Starting revenue (last historical year)
            
        Returns:
            List of projection dicts with revenue, margin, capex, wc for each year
        """
        revenues = self.project_revenue(base_revenue)
        projections = []
        
        for i, revenue in enumerate(revenues):
            projection = {
                "year": i + 1,
                "revenue": revenue,
                "growth_rate": self._growth_schedule[i],
                "operating_margin": self._margin_schedule[i] if self._margin_schedule else None,
                "capex_ratio": self._capex_schedule[i] if self._capex_schedule else None,
                "wc_ratio": self._wc_schedule[i] if self._wc_schedule else None,
            }
            projections.append(projection)
        
        return projections
    
    def describe(self) -> str:
        """
        Generate human-readable description of the model.
        
        Useful for displaying in UI or reports.
        """
        parts = []
        current_year = 1
        
        for stage in self.stages:
            end_year = current_year + stage.years - 1
            
            if stage.end_growth_rate is not None:
                desc = f"Years {current_year}-{end_year}: {stage.name} ({stage.growth_rate:.1%} → {stage.end_growth_rate:.1%})"
            else:
                desc = f"Years {current_year}-{end_year}: {stage.name} ({stage.growth_rate:.1%})"
            
            parts.append(desc)
            current_year = end_year + 1
        
        parts.append(f"Terminal: {self.terminal_growth_rate:.1%} perpetual growth")
        
        return "\n".join(parts)


# Pre-built model templates for common company types
def high_growth_tech_model(terminal_rate: float = 0.03) -> MultiStageGrowthModel:
    """Pre-built model for high-growth tech companies."""
    return MultiStageGrowthModel(
        stages=[
            GrowthStage("Hypergrowth", years=2, growth_rate=0.30),
            GrowthStage("High Growth", years=3, growth_rate=0.20),
            GrowthStage("Fade to Maturity", years=3, growth_rate=0.20, end_growth_rate=0.08),
            GrowthStage("Mature", years=2, growth_rate=0.05),
        ],
        terminal_growth_rate=terminal_rate,
    )


def stable_company_model(terminal_rate: float = 0.025) -> MultiStageGrowthModel:
    """Pre-built model for stable, mature companies."""
    return MultiStageGrowthModel(
        stages=[
            GrowthStage("Current Growth", years=3, growth_rate=0.06),
            GrowthStage("Fade to Terminal", years=4, growth_rate=0.06, end_growth_rate=0.03),
            GrowthStage("Terminal Approach", years=3, growth_rate=0.03),
        ],
        terminal_growth_rate=terminal_rate,
    )


def turnaround_model(terminal_rate: float = 0.025) -> MultiStageGrowthModel:
    """Pre-built model for turnaround/recovery companies."""
    return MultiStageGrowthModel(
        stages=[
            GrowthStage("Recovery", years=2, growth_rate=-0.05, end_growth_rate=0.0),
            GrowthStage("Stabilization", years=2, growth_rate=0.02),
            GrowthStage("Growth Resumption", years=3, growth_rate=0.02, end_growth_rate=0.08),
            GrowthStage("Mature Growth", years=3, growth_rate=0.05),
        ],
        terminal_growth_rate=terminal_rate,
    )


def capital_intensive_model(
    capacity_fill_years: int = 4,
    low_margin: float = 0.06,
    high_margin: float = 0.22,
    step_at_year: int = 3,
    growth_rate: float = 0.10,
    terminal_rate: float = 0.025,
) -> MultiStageGrowthModel:
    """
    Pre-built model for capital-intensive businesses.
    
    Models operating leverage / capacity fill dynamics:
    - Margins stay low while capacity is being filled (high fixed costs, low utilization)
    - Margins jump when capacity utilization exceeds threshold
    - Then stable at high margin as operating leverage kicks in
    
    Suitable for: Airlines, Manufacturing, Utilities, Mining, Semiconductors (fab buildout)
    
    Args:
        capacity_fill_years: Years in the capacity fill phase
        low_margin: Margin while filling capacity (low utilization)
        high_margin: Margin after capacity filled (operating leverage)
        step_at_year: Year when margin jumps (capacity fills)
        growth_rate: Revenue growth during capacity fill
        terminal_rate: Terminal growth rate
    
    Example:
        A semiconductor company building a new fab:
        - Years 1-2: 6% margin (fab ramping, low utilization)
        - Year 3+: 22% margin (fab at capacity, fixed costs spread)
    """
    return MultiStageGrowthModel(
        stages=[
            GrowthStage(
                name="Capacity Fill",
                years=capacity_fill_years,
                growth_rate=growth_rate,
                operating_margin=low_margin,
                end_operating_margin=high_margin,
                margin_fade_mode=FadeMode.STEP,
                margin_step_at_year=step_at_year,
            ),
            GrowthStage(
                name="Mature Operations",
                years=3,
                growth_rate=growth_rate,
                end_growth_rate=terminal_rate + 0.02,  # Fade toward terminal
                operating_margin=high_margin,
            ),
            GrowthStage(
                name="Terminal Approach",
                years=3,
                growth_rate=terminal_rate + 0.02,
                end_growth_rate=terminal_rate,
                operating_margin=high_margin,
                end_operating_margin=high_margin * 0.9,  # Slight margin compression
            ),
        ],
        terminal_growth_rate=terminal_rate,
    )
