"""Audit-related request/response schemas."""
from pydantic import BaseModel
from typing import Optional


class AuditRequest(BaseModel):
    """Request to record assumption changes."""
    assumptions: dict  # Field name -> value
    note: Optional[str] = None
    # Market context at time of recording (for thesis tracking)
    price_at_time: Optional[float] = None
    intrinsic_value_at_time: Optional[float] = None
    pe_ratio_at_time: Optional[float] = None
