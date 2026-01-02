"""Watchlist and notes models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re
import bleach


class Note(BaseModel):
    """User note attached to a stock."""

    id: Optional[int] = None
    symbol: str = Field(..., min_length=1, max_length=10)
    content: str = Field(..., min_length=1, max_length=5000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Sanitize symbol."""
        return v.strip().upper()

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Sanitize note content to prevent XSS."""
        # Allow only basic formatting tags
        allowed_tags = ["b", "i", "u", "p", "br", "ul", "ol", "li"]
        cleaned = bleach.clean(v, tags=allowed_tags, strip=True)
        return cleaned.strip()


class WatchlistItem(BaseModel):
    """Stock in user's watchlist."""

    id: Optional[int] = None
    symbol: str = Field(..., min_length=1, max_length=10)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    
    # User-defined fields
    target_price: Optional[float] = Field(None, gt=0, description="User's target buy price")
    notes: list[Note] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, max_length=10)
    
    # Alert settings
    alert_on_price_drop: bool = Field(default=False)
    alert_threshold_percent: Optional[float] = Field(None, ge=0, le=100)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Sanitize and validate symbol."""
        v = v.strip().upper()
        if not re.match(r"^[A-Z]{1,5}(\.[A-Z])?$", v):
            if not re.match(r"^[A-Z]{1,5}-[A-Z]$", v):
                raise ValueError(f"Invalid stock symbol format: {v}")
        return v

    @field_validator("tags")
    @classmethod
    def sanitize_tags(cls, v: list[str]) -> list[str]:
        """Sanitize tags."""
        cleaned = []
        for tag in v[:10]:  # Max 10 tags
            # Only allow alphanumeric and basic punctuation
            tag = re.sub(r"[^a-zA-Z0-9\-_\s]", "", tag)
            tag = tag.strip()[:50]  # Max 50 chars per tag
            if tag:
                cleaned.append(tag)
        return cleaned

