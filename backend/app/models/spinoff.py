"""Spinoff detection and alert models."""

from datetime import datetime, date
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re


class SpinoffStatus(str, Enum):
    """Spinoff lifecycle status."""

    ANNOUNCED = "announced"  # Form 10 filed, not yet effective
    PENDING = "pending"  # Approved, waiting for distribution
    COMPLETED = "completed"  # Spinoff is now trading
    CANCELLED = "cancelled"  # Spinoff was cancelled


class Spinoff(BaseModel):
    """Corporate spinoff information."""

    id: Optional[int] = None
    
    # The new company being spun off
    spinoff_symbol: Optional[str] = Field(None, max_length=10)
    spinoff_name: str = Field(..., min_length=1, max_length=200)
    
    # The parent company
    parent_symbol: str = Field(..., max_length=10)
    parent_name: str = Field(..., max_length=200)
    
    # SEC filing info
    sec_filing_url: Optional[str] = Field(None, max_length=500)
    sec_filing_date: Optional[date] = None
    sec_filing_type: str = Field(default="10-12B", max_length=20)  # Form 10, 10-12B, etc.
    
    # Dates
    announcement_date: Optional[date] = None
    effective_date: Optional[date] = None  # When spinoff trades independently
    record_date: Optional[date] = None  # Date to own parent for spinoff shares
    
    # Details
    distribution_ratio: Optional[str] = Field(
        None,
        max_length=50,
        description="e.g., '1 share of SpinCo for every 3 shares of Parent'",
    )
    description: Optional[str] = Field(None, max_length=2000)
    sector: Optional[str] = None
    industry: Optional[str] = None
    
    # Status
    status: SpinoffStatus = Field(default=SpinoffStatus.ANNOUNCED)
    
    # Tracking
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("spinoff_symbol", "parent_symbol")
    @classmethod
    def validate_symbol(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize and validate symbol."""
        if v is None:
            return None
        v = v.strip().upper()
        if v and not re.match(r"^[A-Z]{1,5}(\.[A-Z])?$", v):
            if not re.match(r"^[A-Z]{1,5}-[A-Z]$", v):
                raise ValueError(f"Invalid stock symbol format: {v}")
        return v

    @field_validator("spinoff_name", "parent_name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Sanitize company name."""
        v = re.sub(r"<[^>]+>", "", v)  # Remove HTML tags
        return v.strip()

    @field_validator("sec_filing_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate SEC URL."""
        if v is None:
            return None
        v = v.strip()
        # Only allow SEC EDGAR URLs
        if not v.startswith("https://www.sec.gov/"):
            raise ValueError("SEC filing URL must be from sec.gov")
        return v


class SpinoffAlert(BaseModel):
    """Alert for a new spinoff detection."""

    id: Optional[int] = None
    spinoff_id: int = Field(..., gt=0)
    
    # Alert info
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    
    # Status
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None

    @field_validator("title", "message")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Sanitize alert text."""
        v = re.sub(r"<[^>]+>", "", v)  # Remove HTML tags
        return v.strip()

