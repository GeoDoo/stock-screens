"""
Technical indicators calculator.
Calculates SMA, EMA, RSI, MACD from price data.
"""
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class IndicatorValue:
    """Single indicator data point."""
    timestamp: str  # ISO format
    value: float


@dataclass 
class MACDValue:
    """MACD indicator with signal and histogram."""
    timestamp: str
    macd: float
    signal: float
    histogram: float


@dataclass
class TechnicalAnalysisResult:
    """Complete technical analysis for a stock."""
    symbol: str
    period_days: int
    current_price: float
    price_change_pct: float  # vs period start
    
    # Price data for charting
    prices: List[dict]  # {timestamp, open, high, low, close, volume}
    
    # Moving averages
    sma_20: List[IndicatorValue]
    sma_50: List[IndicatorValue]
    ema_12: List[IndicatorValue]
    ema_26: List[IndicatorValue]
    
    # Momentum indicators
    rsi_14: List[IndicatorValue]
    macd: List[MACDValue]
    
    # Volume-weighted indicators (institutional-grade)
    vwap: List[IndicatorValue]  # Volume Weighted Average Price
    
    # Summary signals
    trend: str  # "bullish", "bearish", "neutral"
    rsi_signal: str  # "overbought", "oversold", "neutral"
    macd_signal: str  # "bullish", "bearish", "neutral"
    
    # Fields with defaults must come last
    average_volume: Optional[float] = None  # 20-day average
    relative_volume: Optional[float] = None  # Current vs average (multiplier)
    volume_confirmation: str = "neutral"  # "confirmed", "weak", "neutral"


class TechnicalIndicators:
    """Calculate technical indicators from price bars."""
    
    @staticmethod
    def sma(prices: List[float], period: int) -> List[Optional[float]]:
        """
        Simple Moving Average.
        Returns None for first (period-1) values.
        """
        result = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(None)
            else:
                window = prices[i - period + 1:i + 1]
                result.append(sum(window) / period)
        return result
    
    @staticmethod
    def ema(prices: List[float], period: int) -> List[Optional[float]]:
        """
        Exponential Moving Average.
        Uses SMA as seed for first value.
        """
        if len(prices) < period:
            return [None] * len(prices)
        
        result = [None] * (period - 1)
        
        # Seed with SMA
        sma_seed = sum(prices[:period]) / period
        result.append(sma_seed)
        
        # EMA multiplier
        multiplier = 2 / (period + 1)
        
        # Calculate EMA
        for i in range(period, len(prices)):
            ema_val = (prices[i] - result[-1]) * multiplier + result[-1]
            result.append(ema_val)
        
        return result
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
        """
        Relative Strength Index.
        Returns values between 0-100.
        """
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        # Calculate price changes
        changes = []
        for i in range(1, len(prices)):
            changes.append(prices[i] - prices[i - 1])
        
        result = [None] * period
        
        # Initial average gain/loss
        gains = [c if c > 0 else 0 for c in changes[:period]]
        losses = [-c if c < 0 else 0 for c in changes[:period]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        # First RSI
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
        
        # Subsequent RSI values using smoothed averages
        for i in range(period, len(changes)):
            change = changes[i]
            gain = change if change > 0 else 0
            loss = -change if change < 0 else 0
            
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(100 - (100 / (1 + rs)))
        
        return result
    
    @staticmethod
    def macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        """
        MACD (Moving Average Convergence Divergence).
        
        Returns:
            (macd_line, signal_line, histogram)
        """
        ema_fast = TechnicalIndicators.ema(prices, fast_period)
        ema_slow = TechnicalIndicators.ema(prices, slow_period)
        
        # MACD line = EMA(12) - EMA(26)
        macd_line = []
        for fast, slow in zip(ema_fast, ema_slow):
            if fast is None or slow is None:
                macd_line.append(None)
            else:
                macd_line.append(fast - slow)
        
        # Signal line = EMA(9) of MACD line
        # Need to handle None values
        valid_macd = [m for m in macd_line if m is not None]
        signal_ema = TechnicalIndicators.ema(valid_macd, signal_period)
        
        # Map signal back to full length
        signal_line = []
        signal_idx = 0
        for m in macd_line:
            if m is None:
                signal_line.append(None)
            else:
                if signal_idx < len(signal_ema):
                    signal_line.append(signal_ema[signal_idx])
                    signal_idx += 1
                else:
                    signal_line.append(None)
        
        # Histogram = MACD - Signal
        histogram = []
        for m, s in zip(macd_line, signal_line):
            if m is None or s is None:
                histogram.append(None)
            else:
                histogram.append(m - s)
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def analyze_trend(sma_20: List[Optional[float]], sma_50: List[Optional[float]], prices: List[float]) -> str:
        """Determine trend based on moving averages."""
        if not sma_20 or not sma_50 or not prices:
            return "neutral"
        
        # Get latest valid values
        latest_sma20 = next((v for v in reversed(sma_20) if v is not None), None)
        latest_sma50 = next((v for v in reversed(sma_50) if v is not None), None)
        latest_price = prices[-1] if prices else None
        
        if latest_sma20 is None or latest_sma50 is None or latest_price is None:
            return "neutral"
        
        # Bullish: price > SMA20 > SMA50
        if latest_price > latest_sma20 > latest_sma50:
            return "bullish"
        # Bearish: price < SMA20 < SMA50
        elif latest_price < latest_sma20 < latest_sma50:
            return "bearish"
        else:
            return "neutral"
    
    @staticmethod
    def analyze_rsi(rsi_values: List[Optional[float]]) -> str:
        """Interpret RSI signal."""
        latest_rsi = next((v for v in reversed(rsi_values) if v is not None), None)
        
        if latest_rsi is None:
            return "neutral"
        elif latest_rsi >= 70:
            return "overbought"
        elif latest_rsi <= 30:
            return "oversold"
        else:
            return "neutral"
    
    @staticmethod
    def analyze_macd(macd_line: List[Optional[float]], signal_line: List[Optional[float]]) -> str:
        """Interpret MACD signal."""
        # Get last two valid pairs for crossover detection
        valid_pairs = [(m, s) for m, s in zip(macd_line, signal_line) if m is not None and s is not None]
        
        if len(valid_pairs) < 2:
            return "neutral"
        
        curr_macd, curr_signal = valid_pairs[-1]
        prev_macd, prev_signal = valid_pairs[-2]
        
        # Bullish crossover: MACD crosses above signal
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            return "bullish"
        # Bearish crossover: MACD crosses below signal
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            return "bearish"
        # Continuation
        elif curr_macd > curr_signal:
            return "bullish"
        elif curr_macd < curr_signal:
            return "bearish"
        else:
            return "neutral"
    
    @staticmethod
    def vwap(
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
    ) -> List[Optional[float]]:
        """
        Volume Weighted Average Price (VWAP).
        
        VWAP = Σ(Typical Price × Volume) / Σ(Volume)
        Where Typical Price = (High + Low + Close) / 3
        
        Returns cumulative VWAP for each bar.
        Professional traders use VWAP to assess execution quality
        and identify support/resistance levels.
        """
        if not closes or not highs or not lows or not volumes:
            return []
        
        if len(closes) != len(highs) or len(closes) != len(lows) or len(closes) != len(volumes):
            return []
        
        result = []
        cumulative_tp_vol = 0.0
        cumulative_vol = 0.0
        
        for close, high, low, volume in zip(closes, highs, lows, volumes):
            # Typical price = (High + Low + Close) / 3
            typical_price = (high + low + close) / 3
            
            cumulative_tp_vol += typical_price * volume
            cumulative_vol += volume
            
            if cumulative_vol > 0:
                result.append(cumulative_tp_vol / cumulative_vol)
            else:
                result.append(None)
        
        return result
    
    @staticmethod
    def average_volume(volumes: List[float], period: int = 20) -> Optional[float]:
        """
        Calculate average volume over a period.
        
        Defaults to 20-day average (roughly 1 month of trading).
        """
        if not volumes or period <= 0:
            return None
        
        if len(volumes) < period:
            return sum(volumes) / len(volumes) if volumes else None
        
        return sum(volumes[-period:]) / period
    
    @staticmethod
    def relative_volume(volumes: List[float], period: int = 20) -> Optional[float]:
        """
        Calculate relative volume (current vs average).
        
        Returns a multiplier:
        - 1.0 = average volume
        - 2.0 = 2x average volume
        - 0.5 = half average volume
        
        High relative volume confirms price movements.
        Low relative volume suggests "fake-outs".
        """
        if not volumes or len(volumes) < 2:
            return None
        
        current_volume = volumes[-1]
        
        # Use all but the last bar for average
        avg = TechnicalIndicators.average_volume(volumes[:-1], period)
        
        if avg is None or avg <= 0:
            return None
        
        return current_volume / avg
    
    @staticmethod
    def volume_confirms_trend(
        volumes: List[float],
        trend: str,
        period: int = 20,
    ) -> str:
        """
        Check if volume confirms the trend signal.
        
        Returns:
        - "confirmed": High volume (>1.2x average) supports the signal
        - "weak": Low volume (<0.8x average) suggests unreliable signal
        - "neutral": Average volume or neutral trend
        
        Professional insight: A breakout on high volume is more likely
        to continue. A breakout on low volume is often a "fake-out".
        """
        if trend == "neutral":
            return "neutral"
        
        rel_vol = TechnicalIndicators.relative_volume(volumes, period)
        
        if rel_vol is None:
            return "neutral"
        
        if rel_vol >= 1.2:
            return "confirmed"
        elif rel_vol <= 0.8:
            return "weak"
        else:
            return "neutral"


