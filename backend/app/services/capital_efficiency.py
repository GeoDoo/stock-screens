"""
Capital Efficiency Analysis Module.

Provides ROIC, reinvestment rate, and value creation analysis.

ROIC (Return on Invested Capital) = NOPAT / Invested Capital
Reinvestment Rate = Growth / ROIC

Key insight: Growth only creates value when ROIC > WACC.
If ROIC < WACC, every dollar reinvested destroys shareholder value.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class CapitalEfficiencyCalculator:
    """
    Calculator for capital efficiency metrics.
    
    Key metrics:
    - ROIC: Return on Invested Capital (how efficiently capital is deployed)
    - Incremental ROIC: Return on NEW capital invested (quality of reinvestment)
    - Reinvestment Rate: Portion of earnings reinvested for growth
    - Value Spread: ROIC - WACC (positive = value creation)
    - Economic Profit (EVA): Excess return × Capital
    """
    nopat: float  # Net Operating Profit After Tax
    invested_capital: float  # Equity + Debt - Excess Cash
    revenue_growth: float  # Expected growth rate
    # Prior period data for incremental ROIC calculation
    prior_nopat: Optional[float] = None
    prior_invested_capital: Optional[float] = None
    
    def roic(self) -> Optional[float]:
        """
        Return on Invested Capital = NOPAT / Invested Capital.
        
        Interpretation:
        - > 20%: Exceptional (strong competitive advantage)
        - 15-20%: Good
        - 10-15%: Average
        - < 10%: Below cost of capital for most companies
        
        Returns None if invested capital is zero or negative.
        """
        if self.invested_capital <= 0:
            return None
        return self.nopat / self.invested_capital
    
    def incremental_roic(self) -> Optional[float]:
        """
        Incremental ROIC = ΔNOPAT / ΔInvested Capital.
        
        Measures the return on NEW capital invested, which is critical
        for assessing whether a company's reinvestment is creating value.
        
        Interpretation:
        - Incremental ROIC > ROIC: Improving returns (bullish)
        - Incremental ROIC ≈ ROIC: Stable returns
        - Incremental ROIC < ROIC: Diminishing returns (bearish - red flag!)
        
        Returns None if:
        - Prior period data is not available
        - Change in invested capital is zero
        """
        if self.prior_nopat is None or self.prior_invested_capital is None:
            return None
        
        delta_nopat = self.nopat - self.prior_nopat
        delta_ic = self.invested_capital - self.prior_invested_capital
        
        if delta_ic == 0:
            return None
        
        return delta_nopat / delta_ic
    
    def reinvestment_rate(self) -> Optional[float]:
        """
        Reinvestment Rate = Growth / ROIC.
        
        Shows what fraction of earnings must be reinvested to achieve growth.
        
        High ROIC companies can grow with lower reinvestment.
        Low ROIC companies must reinvest heavily to grow.
        
        Example:
        - ROIC 20%, Growth 10% → Reinvest 50% of earnings
        - ROIC 10%, Growth 10% → Reinvest 100% of earnings
        - ROIC 5%, Growth 10% → Reinvest 200% (unsustainable!)
        """
        roic = self.roic()
        if roic is None or roic == 0:
            return None
        if self.revenue_growth == 0:
            return 0.0
        return self.revenue_growth / roic
    
    def is_value_creating(self, wacc: float) -> bool:
        """
        Is growth creating or destroying shareholder value?
        
        Growth creates value when ROIC > WACC.
        Growth destroys value when ROIC < WACC.
        """
        roic = self.roic()
        if roic is None:
            return False
        return roic > wacc
    
    def value_spread(self, wacc: float) -> Optional[float]:
        """
        Value Spread = ROIC - WACC.
        
        Positive spread = value creation per dollar invested.
        Negative spread = value destruction per dollar invested.
        """
        roic = self.roic()
        if roic is None:
            return None
        return roic - wacc
    
    def economic_profit(self, wacc: float) -> Optional[float]:
        """
        Economic Profit (EVA) = (ROIC - WACC) × Invested Capital.
        
        Dollar amount of value created or destroyed.
        Also known as Economic Value Added (EVA).
        """
        spread = self.value_spread(wacc)
        if spread is None:
            return None
        return spread * self.invested_capital


def analyze_value_creation(
    nopat: float,
    invested_capital: float,
    revenue_growth: float,
    wacc: float,
    prior_nopat: Optional[float] = None,
    prior_invested_capital: Optional[float] = None,
) -> dict:
    """
    Comprehensive value creation analysis.
    
    Returns:
        Dictionary with:
        - roic: Return on Invested Capital
        - incremental_roic: Return on new capital invested
        - reinvestment_rate: % of earnings needed for growth
        - value_spread: ROIC - WACC
        - economic_profit: Dollar value created/destroyed
        - is_value_creating: Boolean
        - assessment: Human-readable analysis
        - incremental_assessment: Assessment of reinvestment quality
    """
    calc = CapitalEfficiencyCalculator(
        nopat=nopat,
        invested_capital=invested_capital,
        revenue_growth=revenue_growth,
        prior_nopat=prior_nopat,
        prior_invested_capital=prior_invested_capital,
    )
    
    roic = calc.roic()
    inc_roic = calc.incremental_roic()
    rr = calc.reinvestment_rate()
    spread = calc.value_spread(wacc)
    eva = calc.economic_profit(wacc)
    is_creating = calc.is_value_creating(wacc)
    
    # Generate main assessment
    if roic is None:
        assessment = "Unable to calculate ROIC (invalid invested capital)"
    elif spread is not None:
        if spread > 0.10:  # > 10% spread
            assessment = f"Strong value creator: ROIC ({roic:.1%}) significantly exceeds WACC ({wacc:.1%})"
        elif spread > 0.02:  # > 2% spread
            assessment = f"Modest value creator: ROIC ({roic:.1%}) exceeds WACC ({wacc:.1%})"
        elif spread > -0.02:  # Within 2% of WACC
            assessment = f"Value neutral: ROIC ({roic:.1%}) approximately equals WACC ({wacc:.1%})"
        else:
            assessment = f"Value destroyer: ROIC ({roic:.1%}) below WACC ({wacc:.1%}). Growth reduces shareholder value."
    else:
        assessment = "Unable to assess value creation"
    
    # Generate incremental ROIC assessment
    incremental_assessment = None
    if inc_roic is not None and roic is not None and roic > 0:
        ratio = inc_roic / roic
        if ratio > 1.2:
            incremental_assessment = f"Improving returns: Incremental ROIC ({inc_roic:.1%}) exceeds ROIC ({roic:.1%}). New investments are more productive."
        elif ratio > 0.8:
            incremental_assessment = f"Stable returns: Incremental ROIC ({inc_roic:.1%}) similar to ROIC ({roic:.1%}). Consistent investment quality."
        elif ratio > 0.5:
            incremental_assessment = f"⚠️ Declining returns: Incremental ROIC ({inc_roic:.1%}) below ROIC ({roic:.1%}). Reinvestment quality deteriorating."
        else:
            incremental_assessment = f"🚨 Diminishing returns: Incremental ROIC ({inc_roic:.1%}) much lower than ROIC ({roic:.1%}). Growth may not be sustainable."
    
    return {
        "roic": roic,
        "incremental_roic": inc_roic,
        "reinvestment_rate": rr,
        "value_spread": spread,
        "economic_profit": eva,
        "is_value_creating": is_creating,
        "assessment": assessment,
        "incremental_assessment": incremental_assessment,
    }
