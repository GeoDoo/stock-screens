"""
Investment Memo models for thesis tracking and post-mortems.

A memo captures an investment thesis at a point in time, tracks its performance,
and allows for periodic post-mortem updates as reality unfolds.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum


class Conviction(Enum):
    """Conviction level for an investment thesis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MemoStatus(Enum):
    """Status of an investment memo."""
    ACTIVE = "active"      # Still tracking
    CLOSED_WIN = "closed_win"    # Thesis played out successfully
    CLOSED_LOSS = "closed_loss"  # Thesis was wrong
    CLOSED_NEUTRAL = "closed_neutral"  # Closed for other reasons


class PostMortemAction(Enum):
    """Action taken during a post-mortem review."""
    HOLD = "hold"          # Maintaining position/thesis
    ADD = "add"            # Adding to position
    TRIM = "trim"          # Reducing position
    CLOSE = "close"        # Closing position entirely
    REVIEW = "review"      # Just a review, no action


@dataclass
class AssumptionsSnapshot:
    """
    Snapshot of DCF assumptions at memo creation time.
    Captures exactly what the analyst believed when forming the thesis.
    """
    revenue_growth: float
    operating_margin: float
    terminal_growth_rate: float
    discount_rate: float
    projection_years: int
    da_ratio: Optional[float] = None
    capex_ratio: Optional[float] = None
    wc_ratio: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "revenue_growth": self.revenue_growth,
            "operating_margin": self.operating_margin,
            "terminal_growth_rate": self.terminal_growth_rate,
            "discount_rate": self.discount_rate,
            "projection_years": self.projection_years,
            "da_ratio": self.da_ratio,
            "capex_ratio": self.capex_ratio,
            "wc_ratio": self.wc_ratio,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssumptionsSnapshot":
        return cls(
            revenue_growth=data["revenue_growth"],
            operating_margin=data["operating_margin"],
            terminal_growth_rate=data["terminal_growth_rate"],
            discount_rate=data["discount_rate"],
            projection_years=data["projection_years"],
            da_ratio=data.get("da_ratio"),
            capex_ratio=data.get("capex_ratio"),
            wc_ratio=data.get("wc_ratio"),
        )


@dataclass
class ScenarioSnapshot:
    """Snapshot of a single scenario (bull/base/bear)."""
    name: str
    revenue_growth: float
    operating_margin: float
    intrinsic_value: float
    upside_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "revenue_growth": self.revenue_growth,
            "operating_margin": self.operating_margin,
            "intrinsic_value": self.intrinsic_value,
            "upside_percent": self.upside_percent,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioSnapshot":
        return cls(
            name=data["name"],
            revenue_growth=data["revenue_growth"],
            operating_margin=data["operating_margin"],
            intrinsic_value=data["intrinsic_value"],
            upside_percent=data["upside_percent"],
        )


@dataclass
class MarketSnapshot:
    """Market data at a point in time."""
    price: float
    intrinsic_value: float
    pe_ratio: Optional[float] = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "price": self.price,
            "intrinsic_value": self.intrinsic_value,
            "pe_ratio": self.pe_ratio,
            "captured_at": self.captured_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketSnapshot":
        return cls(
            price=data["price"],
            intrinsic_value=data["intrinsic_value"],
            pe_ratio=data.get("pe_ratio"),
            captured_at=datetime.fromisoformat(data["captured_at"]) if data.get("captured_at") else datetime.now(timezone.utc),
        )


@dataclass
class PostMortem:
    """
    A post-mortem review of the investment thesis.
    Captures periodic reflections on how reality is tracking vs expectations.
    """
    id: Optional[int]
    memo_id: int
    created_at: datetime
    note: str
    action: PostMortemAction
    price_at_time: float
    iv_at_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memo_id": self.memo_id,
            "created_at": self.created_at.isoformat(),
            "note": self.note,
            "action": self.action.value,
            "price_at_time": self.price_at_time,
            "iv_at_time": self.iv_at_time,
        }


@dataclass 
class InvestmentMemo:
    """
    A complete investment memo tracking a thesis over time.
    
    Captures:
    - The original thesis and reasoning
    - Assumptions and scenarios at creation
    - Market context when thesis was formed
    - Performance tracking over time
    - Post-mortem reflections
    """
    id: Optional[int]
    symbol: str
    title: str  # e.g., "AI iPhone Cycle"
    thesis: str  # The investment thesis narrative
    conviction: Conviction
    time_horizon_months: int
    created_at: datetime
    
    # Snapshots at creation
    assumptions: AssumptionsSnapshot
    scenarios: List[ScenarioSnapshot]
    initial_market: MarketSnapshot
    
    # Target
    target_price: Optional[float] = None
    
    # Risks and catalysts
    risks: Optional[str] = None
    catalysts: Optional[str] = None
    what_would_change_mind: Optional[str] = None
    
    # Status tracking
    status: MemoStatus = MemoStatus.ACTIVE
    closed_at: Optional[datetime] = None
    closed_reason: Optional[str] = None
    
    # Performance tracking (populated separately)
    market_snapshots: List[MarketSnapshot] = field(default_factory=list)
    post_mortems: List[PostMortem] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "title": self.title,
            "thesis": self.thesis,
            "conviction": self.conviction.value,
            "time_horizon_months": self.time_horizon_months,
            "created_at": self.created_at.isoformat(),
            "assumptions": self.assumptions.to_dict(),
            "scenarios": [s.to_dict() for s in self.scenarios],
            "initial_market": self.initial_market.to_dict(),
            "target_price": self.target_price,
            "risks": self.risks,
            "catalysts": self.catalysts,
            "what_would_change_mind": self.what_would_change_mind,
            "status": self.status.value,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "closed_reason": self.closed_reason,
            "market_snapshots": [s.to_dict() for s in self.market_snapshots],
            "post_mortems": [p.to_dict() for p in self.post_mortems],
            # Computed fields
            "current_performance": self._calculate_performance(),
        }
    
    def _calculate_performance(self) -> Dict[str, Any]:
        """Calculate current performance vs thesis."""
        if not self.market_snapshots:
            latest_price = self.initial_market.price
            latest_iv = self.initial_market.intrinsic_value
        else:
            latest = self.market_snapshots[-1]
            latest_price = latest.price
            latest_iv = latest.intrinsic_value
        
        initial_price = self.initial_market.price
        initial_iv = self.initial_market.intrinsic_value
        
        price_change = ((latest_price - initial_price) / initial_price) * 100 if initial_price else 0
        iv_change = ((latest_iv - initial_iv) / initial_iv) * 100 if initial_iv else 0
        
        # Original expected upside
        original_upside = ((initial_iv - initial_price) / initial_price) * 100 if initial_price else 0
        
        # How much of the thesis has played out?
        thesis_realized = (price_change / original_upside) * 100 if original_upside else 0
        
        return {
            "price_change_percent": round(price_change, 2),
            "iv_change_percent": round(iv_change, 2),
            "original_upside_percent": round(original_upside, 2),
            "thesis_realized_percent": round(thesis_realized, 2),
            "latest_price": latest_price,
            "latest_iv": latest_iv,
        }
