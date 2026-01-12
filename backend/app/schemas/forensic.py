from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class RedFlagCategory(BaseModel):
    """Score and evidence for a specific red flag category."""
    score: int = Field(..., ge=1, le=10, description="Risk score from 1 (Safe) to 10 (High Danger)")
    severity: str = Field(..., description="Severity level: 'Low', 'Medium', 'High', 'Critical'")
    findings: List[str] = Field(default_factory=list, description="Specific forensic findings")
    evidence_quotes: List[str] = Field(default_factory=list, description="Direct quotes from the filing")

class EPSAdjustment(BaseModel):
    """Specific adjustment to reported earnings."""
    reason: str = Field(..., description="Why the adjustment is being made (e.g., 'Aggressive Revenue Recognition')")
    amount: float = Field(..., description="Per-share adjustment amount (can be negative for reductions)")
    impact: str = Field(..., description="Description of the impact on economic reality")

class ForensicReport(BaseModel):
    """Structured forensic analysis report."""
    accounting_consistency_score: int = Field(..., ge=1, le=100, description="Overall stability of accounting policies (100 = Perfect)")
    red_flags: Dict[str, RedFlagCategory] = Field(
        ..., 
        description="Heatmap data for: Revenue, Expenses, Assets, Liabilities, CashFlow, Disclosures, Management"
    )
    summary: str = Field(..., description="Executive summary of forensic findings")
    reported_eps: Optional[float] = Field(None, description="The reported EPS from the filing")
    forensic_eps_adjustment: float = Field(0.0, description="Total estimated adjustment to EPS")
    adjustments: List[EPSAdjustment] = Field(default_factory=list, description="Breakdown of specific EPS adjustments")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model: str = Field(..., description="LLM model used for analysis")

class FilingForensicResponse(BaseModel):
    """API response for forensic analysis."""
    ticker: str
    report: ForensicReport
