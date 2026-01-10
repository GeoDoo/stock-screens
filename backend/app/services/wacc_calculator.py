from dataclasses import dataclass
from typing import List, Optional, Tuple


# Maximum beta cap for edge cases (insolvent companies, etc.)
MAX_BETA = 5.0
# Minimum beta (some defensive stocks can have very low or even negative beta)
MIN_BETA = 0.0


# Size Premium Table (based on Duff & Phelps / Ibbotson SBBI data)
# Small-cap companies have historically earned higher returns than predicted by CAPM
# This premium compensates for illiquidity, higher volatility, and business risk
#
# Format: (min_market_cap_billions, size_category, premium)
# Premium is added to cost of equity: Re = Rf + β*(Rm-Rf) + Size Premium
# Table is ordered from largest to smallest for lookup
SIZE_PREMIUM_TABLE: List[Tuple[float, str, float]] = [
    (51.0, "Large Cap (1)", 0.0000),    # > $51B: No premium
    (14.0, "Large Cap (2)", 0.0050),    # $14B - $51B: 0.50%
    (6.0, "Mid Cap (3)", 0.0080),       # $6B - $14B: 0.80%
    (2.5, "Mid Cap (4)", 0.0100),       # $2.5B - $6B: 1.00%
    (1.5, "Small Cap (5)", 0.0150),     # $1.5B - $2.5B: 1.50%
    (0.7, "Small Cap (6)", 0.0180),     # $700M - $1.5B: 1.80%
    (0.3, "Micro Cap (7)", 0.0220),     # $300M - $700M: 2.20%
    (0.1, "Micro Cap (8)", 0.0280),     # $100M - $300M: 2.80%
    (0.0, "Nano Cap (9-10)", 0.0500),   # < $100M: 5.00%
]


def get_size_premium(market_cap: float) -> Tuple[float, str]:
    """
    Get size premium based on market capitalization.
    
    Small-cap companies historically earn excess returns not explained by CAPM beta.
    This "size effect" is one of the oldest documented market anomalies.
    
    Args:
        market_cap: Market capitalization in dollars (not billions)
        
    Returns:
        Tuple of (premium as decimal, size category description)
        
    Example:
        >>> get_size_premium(500_000_000)  # $500M company
        (0.022, "Micro Cap (7)")  # 2.20% size premium
    """
    # Convert to billions for table lookup
    market_cap_billions = market_cap / 1_000_000_000
    
    # Handle edge cases
    if market_cap_billions <= 0:
        return (0.05, "Nano Cap (Unknown)")
    
    # Find the appropriate tier (table sorted largest to smallest)
    for min_cap, category, premium in SIZE_PREMIUM_TABLE:
        if market_cap_billions >= min_cap:
            return (premium, category)
    
    # Fallback for very small caps
    return (0.05, "Nano Cap (9-10)")


def _clamp_beta(beta: float) -> float:
    """Clamp beta to valid range [MIN_BETA, MAX_BETA]."""
    return max(MIN_BETA, min(MAX_BETA, beta))


def unlever_beta(
    levered_beta: float,
    debt: float,
    equity: float,
    tax_rate: float,
) -> float:
    """
    Unlever beta to remove the effect of financial leverage.
    
    Uses the Hamada equation:
        Unlevered Beta = Levered Beta / (1 + (1 - T) × (D/E))
    
    This gives the "pure" business risk beta without leverage amplification.
    
    Args:
        levered_beta: Raw beta from market data (includes leverage effect)
        debt: Total debt
        equity: Market cap (equity value)
        tax_rate: Effective tax rate (0-1)
    
    Returns:
        Unlevered (asset) beta, clamped to [0, MAX_BETA]
    """
    if equity <= 0:
        # Edge case: zero or negative equity means company is insolvent
        # Return a high beta but clamp to valid range
        return _clamp_beta(levered_beta)
    
    if debt <= 0:
        # No debt means no leverage effect, but still clamp
        return _clamp_beta(levered_beta)
    
    tax_rate = _clamp(tax_rate, 0.0, 1.0)
    debt_equity_ratio = debt / equity
    leverage_factor = 1 + (1 - tax_rate) * debt_equity_ratio
    
    unlevered = levered_beta / leverage_factor
    return _clamp_beta(unlevered)


def relever_beta(
    unlevered_beta: float,
    debt: float,
    equity: float,
    tax_rate: float,
) -> float:
    """
    Relever beta to add the effect of financial leverage.
    
    Uses the Hamada equation:
        Relevered Beta = Unlevered Beta × (1 + (1 - T) × (D/E))
    
    This adjusts the pure business risk beta for a specific capital structure.
    
    Args:
        unlevered_beta: Asset beta (pure business risk)
        debt: Total debt of target company
        equity: Market cap of target company
        tax_rate: Effective tax rate (0-1)
    
    Returns:
        Relevered (equity) beta, clamped to [0, MAX_BETA]
    """
    if equity <= 0:
        # Edge case: zero or negative equity means company is insolvent
        # Return maximum beta
        return MAX_BETA
    
    if debt <= 0:
        # No debt means no leverage effect, but still clamp
        return _clamp_beta(unlevered_beta)
    
    tax_rate = _clamp(tax_rate, 0.0, 1.0)
    debt_equity_ratio = debt / equity
    leverage_factor = 1 + (1 - tax_rate) * debt_equity_ratio
    
    relevered = unlevered_beta * leverage_factor
    
    return _clamp_beta(relevered)


def calculate_adjusted_beta(
    peer_beta: float,
    peer_debt: float,
    peer_equity: float,
    target_debt: float,
    target_equity: float,
    tax_rate: float,
) -> float:
    """
    Adjust peer/industry beta for target company's capital structure.
    
    This is the professional approach when:
    1. Company's own beta is unreliable or unavailable
    2. Using industry average beta
    3. Analyzing a private company using public comparables
    
    Process:
    1. Unlever peer beta to get pure business risk
    2. Relever for target's capital structure
    
    Args:
        peer_beta: Beta from peer/industry (levered)
        peer_debt: Peer's total debt
        peer_equity: Peer's market cap
        target_debt: Target company's total debt
        target_equity: Target company's market cap
        tax_rate: Effective tax rate (assumes same for both)
    
    Returns:
        Beta adjusted for target's leverage
    """
    # Step 1: Unlever peer beta
    unlevered = unlever_beta(peer_beta, peer_debt, peer_equity, tax_rate)
    
    # Step 2: Relever for target's capital structure
    adjusted = relever_beta(unlevered, target_debt, target_equity, tax_rate)
    
    return adjusted


def validate_wacc_inputs(
    tax_rate: float,
    total_debt: float,
    market_cap: float,
) -> List[str]:
    """
    Validate WACC inputs and return list of warnings.
    
    Returns:
        List of warning messages for invalid/unusual inputs
    """
    warnings = []
    
    if tax_rate < 0:
        warnings.append(f"Tax rate ({tax_rate:.1%}) is negative - will be treated as 0%")
    elif tax_rate > 1:
        warnings.append(f"Tax rate ({tax_rate:.1%}) exceeds 100% - will be capped at 100%")
    
    if total_debt < 0:
        warnings.append(f"Total debt ({total_debt:,.0f}) is negative - will be treated as 0 (net cash position)")
    
    if market_cap <= 0:
        warnings.append(f"Market cap ({market_cap:,.0f}) is zero or negative - WACC calculation may be invalid")
    
    return warnings


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


@dataclass
class WACCCalculator:
    """
    Weighted Average Cost of Capital calculator.
    
    WACC = (E/V) * Re + (D/V) * Rd * (1 - T)
    
    Where:
    - E = Market cap (equity value)
    - D = Total debt
    - V = E + D (total firm value)
    - Re = Cost of equity (CAPM + Size Premium)
    - Rd = Cost of debt
    - T = Tax rate
    
    Size Premium:
    Small-cap companies historically earn returns higher than predicted by CAPM.
    This is one of the oldest documented market anomalies (Banz, 1981).
    We add a size premium based on Duff & Phelps / Ibbotson SBBI data.
    """
    risk_free_rate: float      # e.g., 10-year treasury yield
    beta: float                # Stock's beta
    market_risk_premium: float # Expected market return - risk free rate
    cost_of_debt: float        # Interest rate on debt
    tax_rate: float            # Effective tax rate
    market_cap: float          # Market capitalization
    total_debt: float          # Total debt
    include_size_premium: bool = True  # Whether to add size premium to cost of equity

    def size_premium(self) -> float:
        """
        Get size premium for this company based on market cap.
        
        Returns 0 if include_size_premium is False or if large cap.
        """
        if not self.include_size_premium:
            return 0.0
        premium, _ = get_size_premium(self.market_cap)
        return premium
    
    def size_category(self) -> str:
        """Get size category description (e.g., 'Small Cap (5)')."""
        _, category = get_size_premium(self.market_cap)
        return category

    def cost_of_equity(self) -> float:
        """
        Calculate cost of equity using CAPM with Size Premium.
        
        Re = Rf + β * (Rm - Rf) + Size Premium
        
        The size premium adjusts for the empirical observation that
        small-cap stocks earn higher returns than predicted by beta alone.
        """
        capm = self.risk_free_rate + self.beta * self.market_risk_premium
        return capm + self.size_premium()

    @property
    def _effective_tax_rate(self) -> float:
        """Tax rate clamped to valid range [0, 1]."""
        return _clamp(self.tax_rate, 0.0, 1.0)
    
    @property
    def _effective_debt(self) -> float:
        """Debt clamped to non-negative (negative debt = net cash position)."""
        return max(0.0, self.total_debt)

    def after_tax_cost_of_debt(self) -> float:
        """
        Calculate after-tax cost of debt.
        Rd * (1 - T)
        
        Tax rate is clamped to [0, 1] range.
        """
        return self.cost_of_debt * (1 - self._effective_tax_rate)

    def calculate(self) -> float:
        """
        Calculate WACC.
        
        Handles edge cases:
        - Tax rate clamped to [0, 1]
        - Negative debt treated as 0 (net cash position)
        """
        effective_debt = self._effective_debt
        total_value = self.market_cap + effective_debt
        
        if total_value == 0:
            return 0.0

        equity_weight = self.market_cap / total_value
        debt_weight = effective_debt / total_value

        wacc = (
            equity_weight * self.cost_of_equity() +
            debt_weight * self.after_tax_cost_of_debt()
        )

        return wacc



