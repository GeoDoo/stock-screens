"""Stock-related request/response schemas."""
from pydantic import BaseModel, field_validator
from typing import Optional, List

from app.constants import DEFAULT_TAX_RATE, DEFAULT_TERMINAL_GROWTH, DEFAULT_MARKET_RISK_PREMIUM
from app.schemas.common import ValidationResponse


class CompanyData(BaseModel):
    """Read-only data from FMP - user cannot change these."""
    beta: Optional[float]
    market_cap: Optional[float]
    total_debt: Optional[float]
    total_equity: Optional[float]  # For Invested Capital calculation
    cash: Optional[float]
    tax_rate: Optional[float]
    cost_of_debt: Optional[float]
    shares_outstanding: Optional[float]
    risk_free_rate: float
    wacc: Optional[float]  # Calculated from the above
    # Derived metrics
    revenue: Optional[float] = None  # Latest revenue for WC calculations
    working_capital: Optional[float] = None  # Current assets - current liabilities


class HistoricalHints(BaseModel):
    """Calculated from historical data - shown as hints for user reference."""
    revenue_growth: Optional[float]
    operating_margin: Optional[float]
    da_ratio: Optional[float]
    capex_ratio: Optional[float]
    wc_ratio: Optional[float]


class ProvenanceItem(BaseModel):
    """Provenance info for a single metric."""
    source: str  # e.g., "ttm", "fy_average", "fallback"
    description: str  # Human-readable explanation
    confidence: str  # "high", "medium", "low"


class DataProvenance(BaseModel):
    """
    Provenance information for key financial metrics.
    
    Institutional-grade transparency: analysts need to know whether
    data comes from TTM, annual averages, or fallback estimates.
    """
    tax_rate: Optional[ProvenanceItem] = None
    shares_outstanding: Optional[ProvenanceItem] = None
    revenue_source: Optional[ProvenanceItem] = None
    cost_of_debt: Optional[ProvenanceItem] = None


class StockDataResponse(BaseModel):
    """Response for /api/stock endpoint."""
    symbol: str
    company_name: Optional[str]
    industry: Optional[str]
    sector: Optional[str]
    data_provider: str  # Which provider supplied the data (fmp, yahoo, etc.)
    data: CompanyData
    hints: HistoricalHints
    validation: ValidationResponse
    is_using_ltm: bool = False  # True if using Last Twelve Months (TTM) data
    provenance: Optional[DataProvenance] = None  # Source/confidence for key metrics


class GrowthStageInput(BaseModel):
    """
    A single growth stage for multi-stage DCF.
    
    Supports fading not just revenue growth, but also unit economics:
    - Operating margin (margin expansion/compression as company matures)
    - CapEx ratio (capital intensity changes)
    - Working capital ratio (efficiency improvements)
    
    Example:
        High-growth SaaS company:
        - Stage 1: 25% growth, 15% margin (investing heavily)
        - Stage 2: 25%→10% growth, 15%→25% margin (operating leverage)
        - Stage 3: 5% growth, 25% margin (mature)
    """
    name: str
    years: int
    growth_rate: float  # e.g., 0.20 for 20%
    end_growth_rate: Optional[float] = None  # If set, fade linearly to this rate
    
    # Economics - operating margin as % of revenue
    operating_margin: Optional[float] = None  # e.g., 0.25 for 25%
    end_operating_margin: Optional[float] = None  # If set, fade to this margin
    
    # Economics - CapEx as % of revenue
    capex_ratio: Optional[float] = None  # e.g., 0.10 for 10%
    end_capex_ratio: Optional[float] = None  # If set, fade to this ratio
    
    # Economics - Working Capital as % of revenue
    wc_ratio: Optional[float] = None  # e.g., 0.15 for 15%
    end_wc_ratio: Optional[float] = None  # If set, fade to this ratio


class ValuationRequest(BaseModel):
    """User provides ALL of these - no defaults from backend."""
    revenue_growth: float  # Used only if growth_stages is not provided
    operating_margin: float
    terminal_growth_rate: float
    market_risk_premium: float
    projection_years: int  # Used only if growth_stages is not provided
    discount_rate_override: Optional[float] = None  # If set, use this instead of calculated WACC
    # FCF projection ratios - passed from frontend based on selected period (TTM or Annual)
    da_ratio: Optional[float] = None  # D&A / Revenue
    capex_ratio: Optional[float] = None  # CapEx / Revenue
    wc_ratio: Optional[float] = None  # Working Capital / Revenue
    # Advanced DCF options
    use_mid_year_discounting: bool = False  # Assumes cash flows occur mid-year
    wc_mode: str = "level"  # "level" or "incremental"
    # Multi-stage growth - if provided, overrides revenue_growth and projection_years
    growth_stages: Optional[List[GrowthStageInput]] = None
    # SBC dilution - annual share growth rate from stock-based compensation
    # E.g., 0.02 means 2% more shares issued each year (dilutes per-share value)
    annual_dilution_rate: float = 0.0
    
    @field_validator('terminal_growth_rate')
    @classmethod
    def validate_terminal_growth(cls, v: float) -> float:
        """Terminal growth must be 0-10%. Higher than GDP growth is unrealistic perpetually."""
        if v < 0:
            raise ValueError("terminal_growth_rate cannot be negative")
        if v > 0.10:
            raise ValueError("terminal_growth_rate cannot exceed 10% (0.10)")
        return v
    
    @field_validator('operating_margin')
    @classmethod
    def validate_operating_margin(cls, v: float) -> float:
        """Operating margin should be -50% to 80%. Higher is unrealistic."""
        if v < -0.50:
            raise ValueError("operating_margin cannot be below -50% (-0.50)")
        if v > 0.80:
            raise ValueError("operating_margin cannot exceed 80% (0.80)")
        return v
    
    @field_validator('projection_years')
    @classmethod
    def validate_projection_years(cls, v: int) -> int:
        """Projection years should be 1-30. Beyond 30 years is unreliable."""
        if v < 1:
            raise ValueError("projection_years must be at least 1")
        if v > 30:
            raise ValueError("projection_years cannot exceed 30")
        return v


class ScenarioInput(BaseModel):
    """A single scenario definition."""
    name: str
    revenue_growth: float  # e.g., 0.05 for 5%
    operating_margin: float  # e.g., 0.25 for 25%
    terminal_growth: float  # e.g., 0.03 for 3%
    probability: float = 0.0  # 0-1, for weighted average
    description: str = ""
    
    @field_validator('terminal_growth')
    @classmethod
    def validate_terminal_growth(cls, v: float) -> float:
        """Terminal growth must be 0-10%."""
        if v < 0:
            raise ValueError("terminal_growth cannot be negative")
        if v > 0.10:
            raise ValueError("terminal_growth cannot exceed 10% (0.10)")
        return v
    
    @field_validator('operating_margin')
    @classmethod
    def validate_operating_margin(cls, v: float) -> float:
        """Operating margin should be -50% to 80%. Higher is unrealistic."""
        if v < -0.50:
            raise ValueError("operating_margin cannot be below -50% (-0.50)")
        if v > 0.80:
            raise ValueError("operating_margin cannot exceed 80% (0.80)")
        return v
    
    @field_validator('probability')
    @classmethod
    def validate_probability(cls, v: float) -> float:
        """Probability must be 0-1."""
        if v < 0:
            raise ValueError("probability cannot be negative")
        if v > 1.0:
            raise ValueError("probability cannot exceed 1.0")
        return v


class ScenarioRequest(BaseModel):
    """Request for scenario analysis."""
    scenarios: Optional[List[ScenarioInput]] = None  # If None, use defaults
    projection_years: int = 10
    market_risk_premium: float = DEFAULT_MARKET_RISK_PREMIUM
    discount_rate_override: Optional[float] = None  # Custom discount rate (bypasses WACC)
    # Hints for default scenario generation - passed from frontend for clean TTM/Annual separation
    revenue_growth_hint: Optional[float] = None  # If provided, use this instead of annual CAGR
    operating_margin_hint: Optional[float] = None  # If provided, use this instead of annual margin
    # FCF ratios - passed from frontend for clean TTM/Annual separation
    da_ratio: Optional[float] = None
    capex_ratio: Optional[float] = None
    wc_ratio: Optional[float] = None


class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo simulation (simplified/quick mode)."""
    base_growth: float  # Base revenue growth rate (e.g., 0.10 for 10%)
    growth_std: float = 0.03  # Standard deviation for growth uncertainty
    base_margin: float  # Base operating margin (e.g., 0.20 for 20%)
    margin_std: float = 0.02  # Standard deviation for margin uncertainty
    base_discount_rate: float  # Base discount rate / WACC
    discount_std: float = 0.01  # Standard deviation for discount rate
    terminal_growth: float = DEFAULT_TERMINAL_GROWTH  # Terminal growth rate
    projection_years: int = 5
    iterations: int = 5000  # Number of simulations (default 5000 for speed)


class WACCComponentsInput(BaseModel):
    """WACC calculation from components (alternative to fixed discount rate)."""
    risk_free_rate: float  # e.g., 0.045 for 4.5%
    beta: float  # Stock's beta
    market_risk_premium: float  # e.g., 0.055 for 5.5%
    cost_of_debt: float  # e.g., 0.05 for 5%
    market_cap: float  # Market capitalization
    # Optional: std devs for sampling WACC inputs
    beta_std: Optional[float] = None  # If set, sample beta with this std dev
    market_risk_premium_std: Optional[float] = None  # If set, sample MRP


class FullMonteCarloRequest(BaseModel):
    """
    Request for Full-Model Monte Carlo simulation (decision-grade).
    
    Uses the complete DCF engine with FCF projections including:
    NOPAT, D&A, CapEx, Working Capital changes, and proper terminal value.
    
    Supports:
    - Bounded distributions and correlations between inputs
    - WACC from components (alternative to fixed discount rate)
    - Multi-stage growth (alternative to single growth rate)
    - Mid-year discounting (more realistic timing)
    """
    # Base assumptions (will be means of distributions)
    base_growth: Optional[float] = None  # Required unless growth_stages provided
    base_margin: float  # Operating margin (EBIT/Revenue)
    base_da_ratio: float  # D&A as % of revenue
    base_capex_ratio: float  # CapEx as % of revenue
    base_wc_ratio: float  # Working capital as % of revenue
    base_tax_rate: float = DEFAULT_TAX_RATE
    base_discount_rate: Optional[float] = None  # Required unless wacc_components provided
    base_terminal_growth: float = DEFAULT_TERMINAL_GROWTH
    
    # Standard deviations for sampling
    growth_std: float = 0.03  # Revenue growth uncertainty
    margin_std: float = 0.02  # Margin uncertainty
    da_ratio_std: float = 0.01  # D&A ratio uncertainty
    capex_ratio_std: float = 0.02  # CapEx ratio uncertainty
    wc_ratio_std: float = 0.02  # Working capital ratio uncertainty
    discount_std: float = 0.01  # Discount rate uncertainty
    terminal_growth_std: float = 0.005  # Terminal growth uncertainty
    
    # Simulation settings
    projection_years: int = 5
    iterations: int = 5000
    
    # Correlations (defaults based on typical market behavior)
    growth_margin_correlation: float = -0.2  # Negative: high growth often compresses margins
    growth_capex_correlation: float = 0.3  # Positive: growth requires investment
    
    # NEW: WACC from components (alternative to base_discount_rate)
    wacc_components: Optional[WACCComponentsInput] = None
    
    # NEW: Multi-stage growth (alternative to base_growth)
    growth_stages: Optional[List[GrowthStageInput]] = None
    
    # NEW: Mid-year discounting
    use_mid_year_discounting: bool = False


class CapitalEfficiencyRequest(BaseModel):
    """Request for capital efficiency analysis."""
    nopat: float  # Net Operating Profit After Tax
    invested_capital: float  # Total invested capital
    revenue_growth: float  # Expected growth rate
    wacc: float  # Weighted Average Cost of Capital


class SensitivityMatrixRequest(BaseModel):
    """
    Request for 2D sensitivity matrix (Growth × Margin or WACC × Terminal Growth).
    
    Institutional analysts use these to understand valuation sensitivity
    to key assumptions and execution risk.
    """
    # What type of matrix to generate
    matrix_type: str = "margin_growth"  # "margin_growth" or "wacc_terminal"
    
    # Base assumptions (read from backend for margin_growth)
    base_growth: Optional[float] = None  # Revenue growth rate
    base_margin: Optional[float] = None  # Operating margin
    base_discount_rate: Optional[float] = None  # WACC
    terminal_growth: float = DEFAULT_TERMINAL_GROWTH
    projection_years: int = 5
    
    # Step sizes (grid will be 5x5 centered on base values)
    growth_steps: List[float] = [-0.05, -0.025, 0, 0.025, 0.05]
    margin_steps: List[float] = [-0.05, -0.025, 0, 0.025, 0.05]
    discount_rate_steps: List[float] = [-0.02, -0.01, 0, 0.01, 0.02]
    terminal_growth_steps: List[float] = [-0.01, -0.005, 0, 0.005, 0.01]
    
    # FCF parameters (for margin_growth matrix)
    da_ratio: Optional[float] = None
    capex_ratio: Optional[float] = None
    wc_ratio: Optional[float] = None


class SensitivityMatrixResponse(BaseModel):
    """Response for sensitivity matrix endpoint."""
    matrix_type: str
    # For margin_growth matrix
    margins: Optional[List[float]] = None
    growth_rates: Optional[List[float]] = None
    # For wacc_terminal matrix
    discount_rates: Optional[List[float]] = None
    terminal_growth_rates: Optional[List[float]] = None
    # The 2D matrix of intrinsic values (row × column)
    matrix: List[List[Optional[float]]]
    # Base values (center of matrix)
    base_values: dict
