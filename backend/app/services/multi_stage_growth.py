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
from typing import List, Optional


@dataclass
class GrowthStage:
    """
    A single growth phase in a multi-stage model.
    
    If end_growth_rate is provided, the stage will fade linearly
    from growth_rate to end_growth_rate over the years.
    """
    name: str
    years: int
    growth_rate: float
    end_growth_rate: Optional[float] = None  # If set, fade linearly to this rate


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


@dataclass
class MultiStageGrowthModel:
    """
    Multi-stage growth model for realistic DCF projections.
    
    Usage:
        model = MultiStageGrowthModel(
            stages=[
                GrowthStage("High Growth", years=3, growth_rate=0.20),
                GrowthStage("Fade", years=4, growth_rate=0.20, end_growth_rate=0.08),
                GrowthStage("Mature", years=3, growth_rate=0.05),
            ],
            terminal_growth_rate=0.03,
        )
        
        revenues = model.project_revenue(base_revenue=1000)
    """
    stages: List[GrowthStage]
    terminal_growth_rate: float
    _growth_schedule: List[float] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        if not self.stages:
            raise ValueError("Multi-stage growth model requires at least one growth stage")
        self._growth_schedule = calculate_growth_schedule(self.stages)
    
    @property
    def total_projection_years(self) -> int:
        """Total years covered by all stages."""
        return sum(stage.years for stage in self.stages)
    
    @property
    def growth_schedule(self) -> List[float]:
        """Year-by-year growth rates."""
        return self._growth_schedule
    
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
