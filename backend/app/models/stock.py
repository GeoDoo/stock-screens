"""Stock domain models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class StockPrice(BaseModel):
    """Current and historical price data."""

    current: Decimal = Field(..., description="Current stock price")
    open: Decimal = Field(..., description="Opening price")
    high: Decimal = Field(..., description="Day high")
    low: Decimal = Field(..., description="Day low")
    close: Decimal = Field(..., description="Previous close")
    volume: int = Field(..., ge=0, description="Trading volume")
    fifty_two_week_high: Optional[Decimal] = None
    fifty_two_week_low: Optional[Decimal] = None
    avg_volume_10d: Optional[int] = Field(None, ge=0)
    avg_volume_3m: Optional[int] = Field(None, ge=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StockFundamentals(BaseModel):
    """Fundamental financial data for a stock."""

    # Valuation ratios
    pe_ratio: Optional[Decimal] = Field(None, description="Price to Earnings ratio")
    forward_pe: Optional[Decimal] = Field(None, description="Forward P/E ratio")
    pb_ratio: Optional[Decimal] = Field(None, description="Price to Book ratio")
    ps_ratio: Optional[Decimal] = Field(None, description="Price to Sales ratio")
    peg_ratio: Optional[Decimal] = Field(None, description="PEG ratio")
    ev_ebitda: Optional[Decimal] = Field(None, description="EV/EBITDA")
    price_to_fcf: Optional[Decimal] = Field(None, description="Price to Free Cash Flow")

    # Per share data
    eps: Optional[Decimal] = Field(None, description="Earnings per share (TTM)")
    eps_forward: Optional[Decimal] = Field(None, description="Forward EPS estimate")
    book_value_per_share: Optional[Decimal] = None
    revenue_per_share: Optional[Decimal] = None
    fcf_per_share: Optional[Decimal] = Field(None, description="Free cash flow per share")

    # Profitability
    profit_margin: Optional[Decimal] = Field(None, ge=-100, le=100)
    operating_margin: Optional[Decimal] = Field(None, ge=-100, le=100)
    gross_margin: Optional[Decimal] = Field(None, ge=-100, le=100)
    roe: Optional[Decimal] = Field(None, description="Return on Equity")
    roa: Optional[Decimal] = Field(None, description="Return on Assets")
    roic: Optional[Decimal] = Field(None, description="Return on Invested Capital")

    # Growth
    revenue_growth: Optional[Decimal] = Field(None, description="YoY revenue growth %")
    earnings_growth: Optional[Decimal] = Field(None, description="YoY earnings growth %")
    eps_growth_5y: Optional[Decimal] = Field(None, description="5-year EPS CAGR")

    # Balance sheet
    total_debt: Optional[Decimal] = Field(None, ge=0)
    total_cash: Optional[Decimal] = Field(None, ge=0)
    debt_to_equity: Optional[Decimal] = None
    current_ratio: Optional[Decimal] = None
    quick_ratio: Optional[Decimal] = None
    interest_coverage: Optional[Decimal] = None

    # Other
    market_cap: Optional[Decimal] = Field(None, ge=0)
    enterprise_value: Optional[Decimal] = None
    shares_outstanding: Optional[int] = Field(None, ge=0)
    float_shares: Optional[int] = Field(None, ge=0)
    dividend_yield: Optional[Decimal] = Field(None, ge=0)
    payout_ratio: Optional[Decimal] = Field(None, ge=0)
    beta: Optional[Decimal] = None

    # Data quality
    data_gaps: list[str] = Field(default_factory=list, description="List of missing data fields")


class Stock(BaseModel):
    """Complete stock data model."""

    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=200)
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    currency: str = Field(default="USD", max_length=3)

    price: Optional[StockPrice] = None
    fundamentals: Optional[StockFundamentals] = None

    last_updated: datetime = Field(default_factory=datetime.utcnow)
    data_quality_score: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Percentage of available data fields"
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Sanitize and validate stock symbol."""
        v = v.strip().upper()
        if not re.match(r"^[A-Z]{1,5}(\.[A-Z])?$", v):
            # Allow symbols like BRK.A, BRK.B
            if not re.match(r"^[A-Z]{1,5}-[A-Z]$", v):
                raise ValueError(f"Invalid stock symbol format: {v}")
        return v

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Sanitize company name."""
        # Remove any HTML/script tags for security
        v = re.sub(r"<[^>]+>", "", v)
        return v.strip()

