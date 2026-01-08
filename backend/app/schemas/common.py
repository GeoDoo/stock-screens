"""Common schemas used across multiple routers."""
from pydantic import BaseModel
from typing import List


class ValidationIssueResponse(BaseModel):
    """A single validation issue."""
    field: str
    message: str


class ValidationResponse(BaseModel):
    """Validation results for stock data."""
    has_errors: bool
    has_warnings: bool
    errors: List[ValidationIssueResponse]
    warnings: List[ValidationIssueResponse]
