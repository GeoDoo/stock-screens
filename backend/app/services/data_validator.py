from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class Severity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Cannot run valuation without this
    WARNING = "warning"  # May affect accuracy, but can proceed


@dataclass
class ValidationIssue:
    """A single validation issue."""
    field: str
    message: str
    severity: Severity
    impacts: str = "dcf"  # What this affects: "wacc", "dcf", "per_share"


@dataclass
class ValidationResult:
    """Result of validating stock data."""
    issues: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        """True if there are any critical errors."""
        return any(i.severity == Severity.ERROR for i in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """True if there are any warnings."""
        return any(i.severity == Severity.WARNING for i in self.issues)
    
    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == Severity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == Severity.WARNING]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
            "errors": [
                {"field": i.field, "message": i.message, "impacts": i.impacts}
                for i in self.errors
            ],
            "warnings": [
                {"field": i.field, "message": i.message, "impacts": i.impacts}
                for i in self.warnings
            ],
        }


class DataValidator:
    """
    Validates stock data for DCF valuation.
    
    Critical fields (ERROR if missing):
    - market_cap: Required for WACC equity weight
    - beta: Required for cost of equity (CAPM)
    - shares_outstanding: Required for per-share intrinsic value
    - revenue_history: Required for FCF projections
    - ebit_history: Required for operating margin calculations
    
    Important fields (WARNING if missing):
    - total_debt: Affects WACC (can assume 0)
    - cash: Affects equity value (can assume 0)
    - tax_rate: Affects NOPAT (can use default 25%)
    - cost_of_debt: Affects WACC (can use default 5%)
    - D&A, CapEx, Working Capital: Affects FCF detail (can estimate)
    """
    
    def __init__(
        self,
        market_cap: Optional[float],
        beta: Optional[float],
        shares_outstanding: Optional[float],
        total_debt: Optional[float],
        cash: Optional[float],
        tax_rate: Optional[float],
        cost_of_debt: Optional[float],
        revenue_history: List[float],
        ebit_history: List[float],
        da_history: List[float],
        capex_history: List[float],
        working_capital_history: List[float],
    ):
        self.market_cap = market_cap
        self.beta = beta
        self.shares_outstanding = shares_outstanding
        self.total_debt = total_debt
        self.cash = cash
        self.tax_rate = tax_rate
        self.cost_of_debt = cost_of_debt
        self.revenue_history = revenue_history
        self.ebit_history = ebit_history
        self.da_history = da_history
        self.capex_history = capex_history
        self.working_capital_history = working_capital_history
    
    def validate(self) -> ValidationResult:
        """Run all validations and return result."""
        result = ValidationResult()
        
        # Critical errors - cannot run valuation without these
        if self.market_cap is None or self.market_cap <= 0:
            result.issues.append(ValidationIssue(
                field="market_cap",
                message="Market cap is missing. Required to calculate equity weight in WACC. Use custom discount rate to bypass.",
                severity=Severity.ERROR,
                impacts="wacc",
            ))
        
        if self.beta is None:
            result.issues.append(ValidationIssue(
                field="beta",
                message="Beta is missing. Required to calculate cost of equity (CAPM). Use custom discount rate to bypass.",
                severity=Severity.ERROR,
                impacts="wacc",
            ))
        
        if self.shares_outstanding is None or self.shares_outstanding <= 0:
            result.issues.append(ValidationIssue(
                field="shares_outstanding",
                message="Shares outstanding is missing. Required to calculate intrinsic value per share.",
                severity=Severity.ERROR,
                impacts="per_share",
            ))
        
        if not self.revenue_history or len(self.revenue_history) < 2:
            result.issues.append(ValidationIssue(
                field="revenue_history",
                message="Insufficient revenue history (need 2+ years). Required to project future cash flows.",
                severity=Severity.ERROR,
                impacts="dcf",
            ))
        
        if not self.ebit_history:
            result.issues.append(ValidationIssue(
                field="ebit_history",
                message="No operating income (EBIT) data. Required to calculate operating margin for projections.",
                severity=Severity.ERROR,
                impacts="dcf",
            ))
        
        # Warnings - can proceed but may affect accuracy
        if self.total_debt is None:
            result.issues.append(ValidationIssue(
                field="total_debt",
                message="Total debt is missing. WACC will assume 100% equity financing (no debt weight).",
                severity=Severity.WARNING,
                impacts="wacc",
            ))
        
        if self.cash is None:
            result.issues.append(ValidationIssue(
                field="cash",
                message="Cash position is missing. Net debt adjustment may undervalue equity.",
                severity=Severity.WARNING,
                impacts="dcf",
            ))
        
        if self.tax_rate is None:
            result.issues.append(ValidationIssue(
                field="tax_rate",
                message="Tax rate unavailable. Using default 25% for NOPAT calculation.",
                severity=Severity.WARNING,
                impacts="dcf",
            ))
        
        if self.cost_of_debt is None:
            result.issues.append(ValidationIssue(
                field="cost_of_debt",
                message="Cost of debt unavailable. WACC will use default 5% interest rate.",
                severity=Severity.WARNING,
                impacts="wacc",
            ))
        elif self.cost_of_debt == 0 and self.total_debt and self.total_debt > 0:
            result.issues.append(ValidationIssue(
                field="cost_of_debt",
                message="Cost of debt is 0% but company has debt. Interest expense may be unreported.",
                severity=Severity.WARNING,
                impacts="wacc",
            ))
        
        if not self.da_history:
            result.issues.append(ValidationIssue(
                field="da_history",
                message="No D&A data. FCF projections will estimate depreciation from revenue ratio.",
                severity=Severity.WARNING,
                impacts="dcf",
            ))
        
        if not self.capex_history:
            result.issues.append(ValidationIssue(
                field="capex_history",
                message="No CapEx data. FCF projections will estimate capital expenditure from revenue ratio.",
                severity=Severity.WARNING,
                impacts="dcf",
            ))
        
        if not self.working_capital_history:
            result.issues.append(ValidationIssue(
                field="working_capital_history",
                message="No working capital data. FCF projections will estimate WC changes from revenue ratio.",
                severity=Severity.WARNING,
                impacts="dcf",
            ))
        
        return result


