"""
Scenario Analysis Calculator

Runs multiple DCF valuations with different assumption sets (Bear/Base/Bull)
to understand the range of possible outcomes.
"""
from dataclasses import dataclass
from typing import List, Optional
from app.services.fcf_projector import FCFProjector


@dataclass
class Scenario:
    """A single scenario with its assumptions."""
    name: str
    revenue_growth: float  # e.g., 0.05 for 5%
    operating_margin: float  # e.g., 0.25 for 25%
    terminal_growth: float  # e.g., 0.03 for 3%
    discount_rate: Optional[float] = None  # If None, use calculated WACC
    probability: float = 0.0  # 0-1, for weighted average (0 = not weighted)
    description: str = ""


@dataclass
class ScenarioResult:
    """Result of running a scenario."""
    name: str
    intrinsic_value: float
    enterprise_value: float
    equity_value: float
    probability: float
    revenue_growth: float
    operating_margin: float
    terminal_growth: float
    discount_rate: float
    description: str
    projections: List[dict]


@dataclass
class ScenarioAnalysisResult:
    """Complete scenario analysis output."""
    symbol: str
    current_price: Optional[float]
    scenarios: List[ScenarioResult]
    probability_weighted_value: Optional[float]  # Computed from (normalized) probabilities
    upside_range: tuple  # (min%, max%) vs current price
    probabilities_normalized: bool = False  # True if probabilities were auto-normalized to sum to 1.0
    

class ScenarioCalculator:
    """
    Calculates intrinsic values for multiple scenarios.
    """
    
    # Default scenario presets
    DEFAULT_SCENARIOS = {
        "bear": Scenario(
            name="Bear",
            revenue_growth=0.02,
            operating_margin=0.15,
            terminal_growth=0.02,
            probability=0.25,
            description="Weak economy, competitive pressure, margin compression"
        ),
        "base": Scenario(
            name="Base",
            revenue_growth=0.06,
            operating_margin=0.22,
            terminal_growth=0.025,
            probability=0.50,
            description="Business as usual, steady growth"
        ),
        "bull": Scenario(
            name="Bull",
            revenue_growth=0.12,
            operating_margin=0.30,
            terminal_growth=0.03,
            probability=0.25,
            description="Strong execution, market tailwinds, expanding margins"
        ),
    }
    
    def __init__(
        self,
        historical_revenue: List[float],
        historical_ebit: List[float],
        historical_da: List[float],
        historical_capex: List[float],
        historical_working_capital: List[float],
        tax_rate: float,
        shares_outstanding: float,
        total_debt: float,
        cash: float,
        base_wacc: float,
        projection_years: int = 10,
        current_price: Optional[float] = None,
        # FCF ratio overrides - for clean TTM/Annual separation
        da_ratio: Optional[float] = None,
        capex_ratio: Optional[float] = None,
        wc_ratio: Optional[float] = None,
    ):
        self.historical_revenue = historical_revenue
        self.historical_ebit = historical_ebit
        self.historical_da = historical_da
        self.historical_capex = historical_capex
        self.historical_working_capital = historical_working_capital
        self.tax_rate = tax_rate
        self.shares_outstanding = shares_outstanding
        self.total_debt = total_debt
        self.cash = cash
        self.base_wacc = base_wacc
        self.projection_years = projection_years
        self.current_price = current_price
        # FCF ratio overrides
        self.da_ratio = da_ratio
        self.capex_ratio = capex_ratio
        self.wc_ratio = wc_ratio
    
    def get_default_scenarios(self, hints: dict) -> List[Scenario]:
        """
        Get default scenarios adjusted to the company's historical performance.
        
        Args:
            hints: Dict with historical metrics (revenue_growth, operating_margin, etc.)
        """
        hist_growth = hints.get("revenue_growth") or 0.06
        hist_margin = hints.get("operating_margin") or 0.20
        
        return [
            Scenario(
                name="Bear",
                revenue_growth=max(0, hist_growth * 0.3),  # 30% of historical
                operating_margin=max(0.05, hist_margin * 0.6),  # 60% of historical
                terminal_growth=0.02,
                probability=0.25,
                description="Weak economy, competitive pressure, margin compression"
            ),
            Scenario(
                name="Base",
                revenue_growth=hist_growth * 0.8,  # 80% of historical (conservative)
                operating_margin=hist_margin * 0.9,  # 90% of historical
                terminal_growth=0.025,
                probability=0.50,
                description="Business as usual, steady growth"
            ),
            Scenario(
                name="Bull",
                revenue_growth=hist_growth * 1.2,  # 120% of historical
                operating_margin=min(0.40, hist_margin * 1.2),  # 120% capped at 40%
                terminal_growth=0.03,
                probability=0.25,
                description="Strong execution, market tailwinds, expanding margins"
            ),
        ]
    
    def run_scenario(self, scenario: Scenario) -> ScenarioResult:
        """Run DCF for a single scenario."""
        
        # Use scenario discount rate or fall back to WACC
        discount_rate = scenario.discount_rate if scenario.discount_rate is not None else self.base_wacc
        
        # Guard: r > g is required for valid terminal value
        if discount_rate <= scenario.terminal_growth:
            raise ValueError(
                f"Invalid scenario '{scenario.name}': discount rate ({discount_rate:.2%}) "
                f"must be greater than terminal growth ({scenario.terminal_growth:.2%})"
            )
        
        # Project FCF
        fcf_projector = FCFProjector(
            historical_revenue=self.historical_revenue,
            historical_ebit=self.historical_ebit,
            historical_da=self.historical_da,
            historical_capex=self.historical_capex,
            historical_working_capital=self.historical_working_capital,
            tax_rate=self.tax_rate,
        )
        
        projections = fcf_projector.project(
            years=self.projection_years,
            revenue_growth=scenario.revenue_growth,
            operating_margin=scenario.operating_margin,
            da_ratio=self.da_ratio,
            capex_ratio=self.capex_ratio,
            wc_ratio=self.wc_ratio,
        )
        
        projected_fcfs = [p["fcf"] for p in projections]
        
        # Calculate PV of FCFs
        pv_fcf = sum(
            fcf / ((1 + discount_rate) ** year)
            for year, fcf in enumerate(projected_fcfs, start=1)
        )
        
        # Terminal value
        final_fcf = projected_fcfs[-1]
        terminal_value = final_fcf * (1 + scenario.terminal_growth) / (discount_rate - scenario.terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** self.projection_years)
        
        enterprise_value = pv_fcf + pv_terminal
        
        # Net debt adjustment
        net_debt = self.total_debt - self.cash
        equity_value = enterprise_value - net_debt
        
        # Intrinsic value per share
        intrinsic_value = equity_value / self.shares_outstanding if self.shares_outstanding > 0 else 0
        
        return ScenarioResult(
            name=scenario.name,
            intrinsic_value=intrinsic_value,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            probability=scenario.probability,
            revenue_growth=scenario.revenue_growth,
            operating_margin=scenario.operating_margin,
            terminal_growth=scenario.terminal_growth,
            discount_rate=discount_rate,
            description=scenario.description,
            projections=projections,
        )
    
    def run_analysis(self, scenarios: List[Scenario]) -> ScenarioAnalysisResult:
        """Run all scenarios and compile results."""
        
        results = [self.run_scenario(s) for s in scenarios]
        
        # Calculate total probability
        total_prob = sum(r.probability for r in results)
        
        # Normalize probabilities if they don't sum to 1.0
        weighted_value = None
        probabilities_normalized = False
        
        if total_prob > 0:
            # Check if normalization is needed (not already ~1.0)
            if not (0.99 <= total_prob <= 1.01):
                # Normalize: scale each probability so they sum to 1.0
                probabilities_normalized = True
                for result in results:
                    result.probability = result.probability / total_prob
            
            # Now probabilities sum to 1.0, calculate weighted value
            weighted_value = sum(r.intrinsic_value * r.probability for r in results)
        # If total_prob == 0, can't normalize, weighted_value stays None
        
        # Calculate upside range vs current price
        values = [r.intrinsic_value for r in results]
        min_val, max_val = min(values), max(values)
        
        if self.current_price and self.current_price > 0:
            min_upside = ((min_val - self.current_price) / self.current_price) * 100
            max_upside = ((max_val - self.current_price) / self.current_price) * 100
            upside_range = (min_upside, max_upside)
        else:
            upside_range = (0, 0)
        
        return ScenarioAnalysisResult(
            symbol="",  # Set by caller
            current_price=self.current_price,
            scenarios=results,
            probability_weighted_value=weighted_value,
            upside_range=upside_range,
            probabilities_normalized=probabilities_normalized,
        )



