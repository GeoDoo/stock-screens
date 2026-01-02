"""Valuation models for different intrinsic value calculation methods."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class ValuationMethod(str, Enum):
    """Supported valuation methods."""

    GRAHAM = "graham"
    DCF = "dcf"
    ASSET_BASED = "asset_based"
    EPV = "epv"  # Earnings Power Value


class GrahamValuation(BaseModel):
    """
    Benjamin Graham's intrinsic value formula.
    
    Formula: V = EPS × (8.5 + 2g) × 4.4 / Y
    Where:
        - EPS = Earnings per share (TTM)
        - 8.5 = P/E base for no-growth company
        - g = Expected growth rate (5-7 years)
        - 4.4 = Average yield of AAA corporate bonds in 1962
        - Y = Current yield of AAA corporate bonds
    """

    eps: Decimal = Field(..., description="Earnings per share")
    growth_rate: Decimal = Field(..., description="Expected annual growth rate (as decimal, e.g., 0.07 for 7%)")
    aaa_yield: Decimal = Field(
        default=Decimal("0.05"),
        description="Current AAA corporate bond yield (as decimal)",
    )
    intrinsic_value: Optional[Decimal] = None
    
    # Graham's constants
    base_pe: Decimal = Field(default=Decimal("8.5"), description="P/E for no-growth company")
    graham_yield: Decimal = Field(default=Decimal("0.044"), description="1962 AAA bond yield")


class DCFValuation(BaseModel):
    """
    Discounted Cash Flow valuation.
    
    Projects future free cash flows and discounts them to present value.
    """

    fcf_current: Decimal = Field(..., description="Current free cash flow")
    growth_rate_high: Decimal = Field(
        ..., description="Growth rate for high-growth period (as decimal)"
    )
    growth_rate_terminal: Decimal = Field(
        default=Decimal("0.025"),
        description="Terminal/perpetual growth rate (as decimal)",
    )
    high_growth_years: int = Field(default=5, ge=1, le=10)
    discount_rate: Decimal = Field(
        default=Decimal("0.10"), description="WACC or required return (as decimal)"
    )
    shares_outstanding: int = Field(..., gt=0)
    
    # Results
    projected_fcfs: list[Decimal] = Field(default_factory=list)
    terminal_value: Optional[Decimal] = None
    total_present_value: Optional[Decimal] = None
    intrinsic_value_per_share: Optional[Decimal] = None


class AssetBasedValuation(BaseModel):
    """
    Asset-based valuation using book value.
    
    Best for:
    - Financial companies (banks, insurance)
    - Asset-heavy businesses
    - Liquidation analysis
    """

    total_assets: Decimal = Field(..., ge=0)
    total_liabilities: Decimal = Field(..., ge=0)
    intangible_assets: Decimal = Field(default=Decimal("0"), ge=0)
    shares_outstanding: int = Field(..., gt=0)
    
    # Adjustments
    asset_discount: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=1,
        description="Discount to apply to asset values (0-1)",
    )
    
    # Results
    net_asset_value: Optional[Decimal] = None
    tangible_book_value: Optional[Decimal] = None
    nav_per_share: Optional[Decimal] = None
    tbv_per_share: Optional[Decimal] = None


class EPVValuation(BaseModel):
    """
    Earnings Power Value (Bruce Greenwald method).
    
    Calculates the value of a company assuming no growth,
    based on normalized/sustainable earnings.
    """

    ebit: Decimal = Field(..., description="Earnings before interest and taxes")
    tax_rate: Decimal = Field(
        default=Decimal("0.25"), ge=0, le=1, description="Effective tax rate"
    )
    maintenance_capex: Decimal = Field(
        default=Decimal("0"), ge=0, description="Maintenance CapEx (not growth CapEx)"
    )
    cost_of_capital: Decimal = Field(
        default=Decimal("0.10"), gt=0, description="Cost of capital / WACC"
    )
    shares_outstanding: int = Field(..., gt=0)
    
    # For adjustment
    excess_cash: Decimal = Field(default=Decimal("0"), ge=0)
    total_debt: Decimal = Field(default=Decimal("0"), ge=0)
    
    # Results
    normalized_earnings: Optional[Decimal] = None
    epv_operations: Optional[Decimal] = None
    epv_equity: Optional[Decimal] = None
    epv_per_share: Optional[Decimal] = None


class MarginOfSafety(BaseModel):
    """Margin of safety calculation."""

    current_price: Decimal = Field(..., gt=0)
    intrinsic_value: Decimal = Field(..., gt=0)
    margin_of_safety: Optional[Decimal] = Field(
        None, description="Percentage discount to intrinsic value"
    )
    is_undervalued: bool = False
    
    # Thresholds
    min_margin_required: Decimal = Field(
        default=Decimal("0.25"),
        description="Minimum margin of safety required (25%)",
    )


class ValuationResult(BaseModel):
    """Complete valuation result for a stock."""

    symbol: str
    current_price: Decimal
    
    # Individual valuations
    graham: Optional[GrahamValuation] = None
    dcf: Optional[DCFValuation] = None
    asset_based: Optional[AssetBasedValuation] = None
    epv: Optional[EPVValuation] = None
    
    # Composite
    average_intrinsic_value: Optional[Decimal] = None
    median_intrinsic_value: Optional[Decimal] = None
    margin_of_safety: Optional[MarginOfSafety] = None
    
    # Recommendation
    valuation_methods_used: list[ValuationMethod] = Field(default_factory=list)
    primary_method: Optional[ValuationMethod] = Field(
        None, description="Most appropriate method for this stock type"
    )
    confidence_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Confidence in valuation based on data quality"
    )
    
    # Warnings
    warnings: list[str] = Field(default_factory=list)
    
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

