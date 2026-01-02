"""Technical analysis indicator models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    """Trend direction classification."""

    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


class SignalStrength(str, Enum):
    """Signal strength classification."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


class MovingAverages(BaseModel):
    """Moving average indicators."""

    # Simple Moving Averages
    sma_20: Optional[Decimal] = Field(None, description="20-day SMA")
    sma_50: Optional[Decimal] = Field(None, description="50-day SMA")
    sma_200: Optional[Decimal] = Field(None, description="200-day SMA")

    # Exponential Moving Averages
    ema_12: Optional[Decimal] = Field(None, description="12-day EMA")
    ema_26: Optional[Decimal] = Field(None, description="26-day EMA")
    ema_50: Optional[Decimal] = Field(None, description="50-day EMA")

    # Price position relative to MAs
    price_vs_sma_50: Optional[Decimal] = Field(
        None, description="% above/below 50-day SMA"
    )
    price_vs_sma_200: Optional[Decimal] = Field(
        None, description="% above/below 200-day SMA"
    )

    # Crossovers
    golden_cross: bool = Field(
        default=False, description="50-day SMA crossed above 200-day SMA"
    )
    death_cross: bool = Field(
        default=False, description="50-day SMA crossed below 200-day SMA"
    )


class MomentumIndicators(BaseModel):
    """Momentum-based technical indicators."""

    # RSI
    rsi_14: Optional[Decimal] = Field(None, ge=0, le=100, description="14-day RSI")
    rsi_signal: Optional[str] = Field(
        None, description="oversold/neutral/overbought"
    )

    # MACD
    macd_line: Optional[Decimal] = Field(None, description="MACD line (12-26 EMA)")
    macd_signal: Optional[Decimal] = Field(None, description="9-day EMA of MACD")
    macd_histogram: Optional[Decimal] = Field(None, description="MACD - Signal")
    macd_crossover: Optional[str] = Field(
        None, description="bullish/bearish/none"
    )

    # Stochastic
    stoch_k: Optional[Decimal] = Field(None, ge=0, le=100, description="Stochastic %K")
    stoch_d: Optional[Decimal] = Field(None, ge=0, le=100, description="Stochastic %D")


class VolatilityIndicators(BaseModel):
    """Volatility-based indicators."""

    # Bollinger Bands
    bb_upper: Optional[Decimal] = Field(None, description="Upper Bollinger Band")
    bb_middle: Optional[Decimal] = Field(None, description="Middle Band (20-day SMA)")
    bb_lower: Optional[Decimal] = Field(None, description="Lower Bollinger Band")
    bb_width: Optional[Decimal] = Field(None, description="Band width as % of middle")
    bb_position: Optional[Decimal] = Field(
        None, description="Price position within bands (0-1)"
    )

    # ATR
    atr_14: Optional[Decimal] = Field(None, ge=0, description="14-day ATR")
    atr_percent: Optional[Decimal] = Field(
        None, ge=0, description="ATR as % of price"
    )

    # Historical volatility
    volatility_20d: Optional[Decimal] = Field(
        None, ge=0, description="20-day historical volatility"
    )
    volatility_60d: Optional[Decimal] = Field(
        None, ge=0, description="60-day historical volatility"
    )


class VolumeIndicators(BaseModel):
    """Volume-based indicators."""

    # Basic volume
    volume: Optional[int] = Field(None, ge=0)
    volume_sma_20: Optional[Decimal] = Field(None, ge=0, description="20-day avg volume")
    volume_ratio: Optional[Decimal] = Field(
        None, ge=0, description="Current volume / avg volume"
    )

    # On-Balance Volume
    obv: Optional[Decimal] = Field(None, description="On-Balance Volume")
    obv_sma_20: Optional[Decimal] = Field(None, description="20-day OBV SMA")
    obv_trend: Optional[TrendDirection] = None

    # Accumulation/Distribution
    ad_line: Optional[Decimal] = Field(
        None, description="Accumulation/Distribution Line"
    )
    ad_trend: Optional[TrendDirection] = None

    # Money Flow
    mfi_14: Optional[Decimal] = Field(
        None, ge=0, le=100, description="14-day Money Flow Index"
    )


class TechnicalIndicators(BaseModel):
    """Complete technical analysis for a stock."""

    symbol: str
    current_price: Decimal

    # Indicator groups
    moving_averages: Optional[MovingAverages] = None
    momentum: Optional[MomentumIndicators] = None
    volatility: Optional[VolatilityIndicators] = None
    volume: Optional[VolumeIndicators] = None

    # Overall assessment
    trend_direction: Optional[TrendDirection] = None
    trend_strength: Optional[SignalStrength] = None

    # Support/Resistance (simple)
    support_level: Optional[Decimal] = None
    resistance_level: Optional[Decimal] = None

    # Summary signals
    signals: list[str] = Field(
        default_factory=list,
        description="List of notable signals (e.g., 'RSI oversold', 'Golden cross')",
    )

    calculated_at: datetime = Field(default_factory=datetime.utcnow)

