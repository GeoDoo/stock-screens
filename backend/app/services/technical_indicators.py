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
    
    # NEW: Enhanced volume-weighted indicators
    vwma_20: Optional[List[IndicatorValue]] = None  # Volume-Weighted Moving Average
    obv: Optional[List[IndicatorValue]] = None  # On-Balance Volume
    mfi_14: Optional[List[IndicatorValue]] = None  # Money Flow Index
    mfi_signal: str = "neutral"  # "overbought", "oversold", "neutral"
    obv_trend: str = "neutral"  # "accumulation", "distribution", "neutral"
    
    # NEW: Momentum Bridge (Value + Momentum convergence)
    vwma_200: Optional[List[IndicatorValue]] = None  # 200-day VWMA for long-term trend
    vwma_trend: Optional[str] = None  # "uptrend", "downtrend", "flat", or None if insufficient data


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
    
    @staticmethod
    def vwma(prices: List[float], volumes: List[float], period: int = 20) -> List[Optional[float]]:
        """
        Volume Weighted Moving Average.
        
        VWMA = Σ(Price × Volume) / Σ(Volume) over the period.
        
        Unlike SMA which treats all prices equally, VWMA gives
        more weight to prices traded at higher volume.
        
        Professional use: VWMA above SMA suggests buyers are more
        aggressive; VWMA below SMA suggests sellers are dominant.
        """
        if not prices or not volumes or len(prices) != len(volumes):
            return []
        
        result = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(None)
            else:
                window_prices = prices[i - period + 1:i + 1]
                window_volumes = volumes[i - period + 1:i + 1]
                
                pv_sum = sum(p * v for p, v in zip(window_prices, window_volumes))
                v_sum = sum(window_volumes)
                
                if v_sum > 0:
                    result.append(pv_sum / v_sum)
                else:
                    result.append(None)
        
        return result
    
    @staticmethod
    def obv(prices: List[float], volumes: List[float]) -> List[float]:
        """
        On-Balance Volume (OBV).
        
        Cumulative sum of volume, adding on up days and subtracting on down days.
        
        OBV rising with price = bullish (smart money accumulating)
        OBV falling with price = bearish (smart money distributing)
        OBV divergence = potential reversal
        
        Created by Joe Granville as "crowd wisdom" indicator.
        """
        if not prices or not volumes or len(prices) != len(volumes):
            return []
        
        result = [0.0]  # Start at 0
        
        for i in range(1, len(prices)):
            if prices[i] > prices[i - 1]:
                # Price up - add volume
                result.append(result[-1] + volumes[i])
            elif prices[i] < prices[i - 1]:
                # Price down - subtract volume
                result.append(result[-1] - volumes[i])
            else:
                # Price unchanged - no change
                result.append(result[-1])
        
        return result
    
    @staticmethod
    def mfi(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        period: int = 14,
    ) -> List[Optional[float]]:
        """
        Money Flow Index (MFI) - Volume-weighted RSI.
        
        MFI combines price and volume to measure buying/selling pressure.
        
        Typical Price = (High + Low + Close) / 3
        Money Flow = Typical Price × Volume
        Money Flow Ratio = Positive MF / Negative MF
        MFI = 100 - (100 / (1 + Money Flow Ratio))
        
        MFI > 80 = overbought (with volume confirmation)
        MFI < 20 = oversold (with volume confirmation)
        
        More reliable than RSI because it includes volume.
        """
        if not all([highs, lows, closes, volumes]):
            return []
        
        n = len(closes)
        if n != len(highs) or n != len(lows) or n != len(volumes):
            return []
        
        if n < period + 1:
            return [None] * n
        
        # Calculate typical prices
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        
        # Calculate raw money flows
        money_flows = [tp * vol for tp, vol in zip(typical_prices, volumes)]
        
        result = [None] * period
        
        for i in range(period, n):
            positive_mf = 0.0
            negative_mf = 0.0
            
            for j in range(i - period + 1, i + 1):
                if j > 0 and typical_prices[j] > typical_prices[j - 1]:
                    positive_mf += money_flows[j]
                elif j > 0 and typical_prices[j] < typical_prices[j - 1]:
                    negative_mf += money_flows[j]
            
            if positive_mf == 0 and negative_mf == 0:
                # No price movement - neutral
                result.append(50.0)
            elif negative_mf == 0:
                # All positive flow - overbought
                result.append(100.0)
            else:
                mf_ratio = positive_mf / negative_mf
                result.append(100 - (100 / (1 + mf_ratio)))
        
        return result
    
    @staticmethod
    def analyze_mfi(mfi_values: List[Optional[float]]) -> str:
        """Interpret Money Flow Index signal."""
        latest_mfi = next((v for v in reversed(mfi_values) if v is not None), None)
        
        if latest_mfi is None:
            return "neutral"
        elif latest_mfi >= 80:
            return "overbought"
        elif latest_mfi <= 20:
            return "oversold"
        else:
            return "neutral"
    
    @staticmethod
    def obv_trend(obv_values: List[float], period: int = 20) -> str:
        """
        Analyze OBV trend direction.
        
        Returns:
        - "accumulation": OBV trending up (buyers dominant)
        - "distribution": OBV trending down (sellers dominant)
        - "neutral": No clear trend
        """
        if len(obv_values) < period:
            return "neutral"
        
        # Compare OBV slope over the period
        recent = obv_values[-period:]
        
        # Simple linear regression slope direction
        n = len(recent)
        x_sum = sum(range(n))
        y_sum = sum(recent)
        xy_sum = sum(i * v for i, v in enumerate(recent))
        xx_sum = sum(i * i for i in range(n))
        
        denominator = n * xx_sum - x_sum * x_sum
        if denominator == 0:
            return "neutral"
        
        slope = (n * xy_sum - x_sum * y_sum) / denominator
        
        # Normalize slope by OBV RANGE (not mean) to handle zero-crossing
        # When OBV goes from positive to negative, mean can be ~0 but range captures magnitude
        obv_range = max(recent) - min(recent)
        if obv_range == 0:
            return "neutral"
        
        # Slope per period as fraction of total range
        # slope * period gives total change over the period
        total_change = slope * (n - 1)
        normalized_change = total_change / obv_range
        
        if normalized_change > 0.3:  # OBV moved >30% of its range upward
            return "accumulation"
        elif normalized_change < -0.3:  # OBV moved >30% of its range downward
            return "distribution"
        else:
            return "neutral"
    
    @staticmethod
    def analyze_vwma_trend(
        vwma_values: List[Optional[float]], 
        period: int = 200,
        lookback: int = 20,
    ) -> str:
        """
        Analyze the trend of the 200-day VWMA.
        
        This is the "Momentum Bridge" - a key convergence signal for
        combining Value (DCF) with Momentum (trend).
        
        A cheap valuation should only trigger a "Buy" if the VWMA
        is flattening or trending up. Buying into a downtrend is
        "catching a falling knife" and creates "Dead Money" risk.
        
        Args:
            vwma_values: 200-day VWMA values (with None for initial period)
            period: VWMA period (default 200)
            lookback: Days to check trend slope (default 20)
        
        Returns:
            "uptrend": VWMA rising - momentum supports entry
            "downtrend": VWMA falling - wait for reversal
            "flat": VWMA relatively stable - cautiously acceptable
        """
        # Get valid VWMA values (exclude None)
        valid_values = [v for v in vwma_values if v is not None]
        
        if len(valid_values) < lookback:
            return "flat"  # Not enough data - assume neutral
        
        # Use last 'lookback' values to determine slope
        recent = valid_values[-lookback:]
        
        # Calculate percentage change over the lookback period
        start_val = recent[0]
        end_val = recent[-1]
        
        if start_val == 0:
            return "flat"
        
        pct_change = (end_val - start_val) / start_val
        
        # Threshold: ±1% over 20 days is considered "flat"
        # More than +1% = uptrend, less than -1% = downtrend
        if pct_change > 0.01:  # >1% rise over lookback
            return "uptrend"
        elif pct_change < -0.01:  # >1% fall over lookback
            return "downtrend"
        else:
            return "flat"
    
    @staticmethod
    def momentum_bridge_signal(
        intrinsic_value: float,
        current_price: float,
        vwma_trend: str,
        undervalued_threshold: float = 0.15,  # 15% margin of safety
        overvalued_threshold: float = -0.10,  # 10% overvalued
    ) -> str:
        """
        Momentum Bridge: Combine Value and Momentum for entry signal.
        
        This bridges the gap between Intrinsic Value (DCF) and Market
        Psychology (trend). Buying cheap stocks in downtrends often
        leads to "Dead Money" - value traps that take years to recover.
        
        Signal Logic:
        - BUY: Undervalued AND (uptrend OR flat) - momentum supports entry
        - WAIT: Undervalued AND downtrend - don't catch falling knife
        - HOLD: Fair value (within ±15%) - no strong action
        - AVOID: Overvalued - don't buy regardless of trend
        
        Args:
            intrinsic_value: Calculated DCF value per share
            current_price: Current market price
            vwma_trend: "uptrend", "downtrend", or "flat"
            undervalued_threshold: % below which stock is "cheap" (default 15%)
            overvalued_threshold: % above which stock is "expensive" (default -10%)
        
        Returns:
            "buy": Value + Momentum aligned for entry
            "wait": Value says cheap, momentum says wait
            "hold": Fair value, no strong signal
            "avoid": Overvalued, don't buy
        """
        if current_price <= 0 or intrinsic_value <= 0:
            return "hold"
        
        # Calculate margin of safety (positive = undervalued)
        margin = (intrinsic_value - current_price) / current_price
        
        # Overvalued - avoid regardless of trend
        if margin < overvalued_threshold:
            return "avoid"
        
        # Undervalued - check momentum
        if margin > undervalued_threshold:
            if vwma_trend in ("uptrend", "flat"):
                return "buy"  # Value + Momentum aligned
            else:
                return "wait"  # Cheap but don't catch falling knife
        
        # Fair value range
        return "hold"


