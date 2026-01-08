"""
Assumption Audit Trail Models

Tracks changes to DCF valuation assumptions over time.
Enables investment process documentation and thesis evolution tracking.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class AssumptionField(str, Enum):
    """Trackable assumption fields."""
    REVENUE_GROWTH = "revenue_growth"
    OPERATING_MARGIN = "operating_margin"
    TERMINAL_GROWTH = "terminal_growth"
    DISCOUNT_RATE = "discount_rate"
    PROJECTION_YEARS = "projection_years"
    MARKET_RISK_PREMIUM = "market_risk_premium"


@dataclass
class AssumptionChange:
    """A single change to an assumption field."""
    field: AssumptionField
    old_value: Optional[float]
    new_value: float


@dataclass
class AuditEntry:
    """
    A commit-style audit entry capturing multiple assumption changes.
    
    Like a git commit - groups related changes with a timestamp and optional note.
    """
    id: Optional[int]
    symbol: str
    timestamp: datetime
    changes: List[AssumptionChange]
    note: Optional[str]
    is_initial: bool  # True if this is the first analysis (baseline)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "changes": [
                {
                    "field": change.field.value,
                    "old_value": change.old_value,
                    "new_value": change.new_value,
                }
                for change in self.changes
            ],
            "note": self.note,
            "is_initial": self.is_initial,
        }


@dataclass
class AssumptionSnapshot:
    """
    Current state of all assumptions for a symbol.
    Used to detect what changed since last commit.
    """
    symbol: str
    revenue_growth: Optional[float] = None
    operating_margin: Optional[float] = None
    terminal_growth: Optional[float] = None
    discount_rate: Optional[float] = None
    projection_years: Optional[int] = None
    market_risk_premium: Optional[float] = None
    
    def diff(self, new_values: dict) -> List[AssumptionChange]:
        """
        Compare current snapshot with new values and return list of changes.
        
        Args:
            new_values: Dict with field names and new values
            
        Returns:
            List of AssumptionChange for fields that changed
        """
        changes = []
        
        field_mapping = {
            "revenue_growth": (AssumptionField.REVENUE_GROWTH, self.revenue_growth),
            "operating_margin": (AssumptionField.OPERATING_MARGIN, self.operating_margin),
            "terminal_growth": (AssumptionField.TERMINAL_GROWTH, self.terminal_growth),
            "discount_rate": (AssumptionField.DISCOUNT_RATE, self.discount_rate),
            "projection_years": (AssumptionField.PROJECTION_YEARS, self.projection_years),
            "market_risk_premium": (AssumptionField.MARKET_RISK_PREMIUM, self.market_risk_premium),
        }
        
        for field_name, (field_enum, old_value) in field_mapping.items():
            if field_name in new_values:
                new_value = new_values[field_name]
                # Check if value actually changed (handle float comparison)
                if old_value is None or new_value is None:
                    if old_value != new_value:
                        changes.append(AssumptionChange(
                            field=field_enum,
                            old_value=old_value,
                            new_value=new_value,
                        ))
                elif abs(float(old_value) - float(new_value)) > 0.0001:
                    changes.append(AssumptionChange(
                        field=field_enum,
                        old_value=float(old_value),
                        new_value=float(new_value),
                    ))
        
        return changes
    
    def apply_changes(self, changes: List[AssumptionChange]) -> 'AssumptionSnapshot':
        """Apply changes to create a new snapshot."""
        new_snapshot = AssumptionSnapshot(symbol=self.symbol)
        
        # Copy current values
        new_snapshot.revenue_growth = self.revenue_growth
        new_snapshot.operating_margin = self.operating_margin
        new_snapshot.terminal_growth = self.terminal_growth
        new_snapshot.discount_rate = self.discount_rate
        new_snapshot.projection_years = self.projection_years
        new_snapshot.market_risk_premium = self.market_risk_premium
        
        # Apply changes
        for change in changes:
            if change.field == AssumptionField.REVENUE_GROWTH:
                new_snapshot.revenue_growth = change.new_value
            elif change.field == AssumptionField.OPERATING_MARGIN:
                new_snapshot.operating_margin = change.new_value
            elif change.field == AssumptionField.TERMINAL_GROWTH:
                new_snapshot.terminal_growth = change.new_value
            elif change.field == AssumptionField.DISCOUNT_RATE:
                new_snapshot.discount_rate = change.new_value
            elif change.field == AssumptionField.PROJECTION_YEARS:
                new_snapshot.projection_years = int(change.new_value)
            elif change.field == AssumptionField.MARKET_RISK_PREMIUM:
                new_snapshot.market_risk_premium = change.new_value
        
        return new_snapshot

