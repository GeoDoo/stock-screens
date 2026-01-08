"""Memo-related request/response schemas."""
from pydantic import BaseModel
from typing import Optional, List


class MemoAssumptions(BaseModel):
    """Assumptions snapshot for memo creation."""
    revenue_growth: float
    operating_margin: float
    terminal_growth_rate: float
    discount_rate: float
    projection_years: int
    da_ratio: Optional[float] = None
    capex_ratio: Optional[float] = None
    wc_ratio: Optional[float] = None


class MemoScenario(BaseModel):
    """Scenario data for memo creation."""
    name: str
    revenue_growth: float
    operating_margin: float
    intrinsic_value: float
    upside_percent: float


class MemoMarket(BaseModel):
    """Market data for memo creation."""
    price: float
    intrinsic_value: float
    pe_ratio: Optional[float] = None


class CreateMemoRequest(BaseModel):
    """Request to create a new investment memo."""
    symbol: str
    title: str
    thesis: str
    conviction: str  # low, medium, high
    time_horizon_months: int
    assumptions: MemoAssumptions
    scenarios: List[MemoScenario]
    initial_market: MemoMarket
    target_price: Optional[float] = None
    risks: Optional[str] = None
    catalysts: Optional[str] = None
    what_would_change_mind: Optional[str] = None


class AddPostMortemRequest(BaseModel):
    """Request to add a post-mortem."""
    note: str
    action: str  # hold, add, trim, close, review
    price_at_time: float
    iv_at_time: float


class CloseMemoRequest(BaseModel):
    """Request to close a memo."""
    status: str  # closed_win, closed_loss, closed_neutral
    reason: str
