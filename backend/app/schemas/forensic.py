from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class RedFlagCategory(BaseModel):
    """Score and evidence for a specific red flag category."""
    category: str = Field(..., description="The forensic category (e.g., 'Revenue', 'Expenses')")
    score: int = Field(..., ge=1, le=10, description="Risk score from 1 (Safe) to 10 (High Danger)")
    severity: str = Field(..., description="Severity level: 'Low', 'Medium', 'High', 'Critical'")
    findings: List[str] = Field(default_factory=list, description="Specific forensic findings")
    evidence_quotes: List[str] = Field(default_factory=list, description="Direct quotes from the filing")

class EPSAdjustment(BaseModel):
    """Specific adjustment to reported earnings."""
    reason: str = Field(..., description="Why the adjustment is being made (e.g., 'Aggressive Revenue Recognition')")
    amount: float = Field(..., description="Per-share adjustment amount (can be negative for reductions)")
    impact: str = Field(..., description="Description of the impact on economic reality")

class ForensicAnalysisLLM(BaseModel):
    """The subset of the forensic report that the LLM is responsible for generating."""
    accounting_consistency_score: int = Field(..., ge=1, le=100, description="Overall stability of accounting policies (100 = Perfect)")
    red_flags: List[RedFlagCategory] = Field(
        ..., 
        description="Heatmap data for forensic categories"
    )
    summary: str = Field(..., description="Executive summary of forensic findings")
    reported_eps: Optional[float] = Field(None, description="The reported EPS from the filing")
    forensic_eps_adjustment: float = Field(0.0, description="Total estimated adjustment to EPS")
    adjustments: List[EPSAdjustment] = Field(default_factory=list, description="Breakdown of specific EPS adjustments")

class QuantitativeAudit(BaseModel):
    """Quantitative forensic metrics from financial statements."""
    sloan_ratio: Optional[float] = Field(None, description="Accrual quality metric")
    altman_z_score: Optional[float] = Field(None, description="Bankruptcy risk score")
    beneish_m_score: Optional[float] = Field(None, description="Earnings manipulation risk")
    
    # Detailed Ratios
    liquidity_ratios: Dict[str, Optional[float]] = Field(default_factory=dict)
    solvency_ratios: Dict[str, Optional[float]] = Field(default_factory=dict)
    efficiency_ratios: Dict[str, Optional[float]] = Field(default_factory=dict)
    profitability_ratios: Dict[str, Optional[float]] = Field(default_factory=dict)
    
    # Corrections / Adjustments
    accounting_corrections: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Input Provenance (NOTES2.md / Finance Guardrails)
    input_provenance: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Source info for critical inputs like tax_rate")
    
    margin_growth_sensitivity: Optional[Dict[str, Any]] = Field(None, description="Sensitivity matrix for execution risk")
    findings: List[str] = Field(default_factory=list, description="Automated numerical findings")

class ForensicReport(BaseModel):
    """Structured forensic analysis report."""
    accounting_consistency_score: int
    red_flags: List[RedFlagCategory]
    summary: str
    reported_eps: Optional[float] = None
    forensic_eps_adjustment: float = 0.0
    adjustments: List[EPSAdjustment] = Field(default_factory=list)
    quantitative_audit: Optional[QuantitativeAudit] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model: str = ""

class FilingForensicResponse(BaseModel):
    """API response for forensic analysis."""
    ticker: str
    report: ForensicReport
