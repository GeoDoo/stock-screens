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
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class GrowthStage:
    """
    A single growth phase in a multi-stage model.
    
    If end_* fields are provided, the stage will fade linearly
    from start to end values over the years.
    
    Economics fields (margin, capex, wc) allow modeling how a company's
    unit economics evolve as it matures - critical for accurate DCF.
    """
    name: str
    years: int
    growth_rate: float
    end_growth_rate: Optional[float] = None  # If set, fade linearly to this rate
    
    # Economics - operating margin as % of revenue
    operating_margin: Optional[float] = None
    end_operating_margin: Optional[float] = None
    
    # Economics - CapEx as % of revenue  
    capex_ratio: Optional[float] = None
    end_capex_ratio: Optional[float] = None
    
    # Economics - Working Capital as % of revenue
    wc_ratio: Optional[float] = None
    end_wc_ratio: Optional[float] = None


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
) -> Optional[List[float]]:
    """
    Calculate year-by-year schedule for an economics metric (margin, capex, wc).
    
    Args:
        stages: List of growth stages
        start_attr: Attribute name for start value (e.g., 'operating_margin')
        end_attr: Attribute name for end value (e.g., 'end_operating_margin')
    
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
        
        if start_value is None:
            # No value for this stage - use None placeholders
            schedule.extend([None] * stage.years)
        elif end_value is not None:
            # Fade stage
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
        self._margin_schedule = calculate_economics_schedule(
            self.stages, 'operating_margin', 'end_operating_margin'
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
