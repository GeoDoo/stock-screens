"""Technical analysis service."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class TechnicalService:
    """Service for calculating technical indicators."""

    def _round(self, value: Decimal, places: int = 2) -> Decimal:
        """Round decimal to specified places."""
        return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)

    def calculate_sma(self, prices: list[Decimal], period: int) -> Decimal:
        """
        Calculate Simple Moving Average.
        
        SMA = sum of prices / number of periods
        """
        if len(prices) < period:
            raise ValueError("Not enough prices for period")
        
        relevant_prices = prices[-period:]
        return sum(relevant_prices) / period

    def calculate_rsi(self, prices: list[Decimal], period: int = 14) -> Optional[Decimal]:
        """
        Calculate Relative Strength Index.
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        if len(prices) < period + 1:
            return None
        
        # Calculate price changes
        changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [max(change, Decimal("0")) for change in changes]
        losses = [abs(min(change, Decimal("0"))) for change in changes]
        
        # Calculate average gain/loss for the period
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return Decimal("100")  # No losses = maximum strength
        
        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (1 + rs))
        
        return self._round(rsi)

    def calculate_ema(self, prices: list[Decimal], period: int) -> Optional[Decimal]:
        """
        Calculate Exponential Moving Average.
        
        EMA = Price * k + EMA_prev * (1 - k)
        k = 2 / (period + 1)
        """
        if len(prices) < period:
            return None
        
        k = Decimal("2") / (period + 1)
        
        # Start with SMA for first EMA value
        ema = sum(prices[:period]) / period
        
        # Calculate EMA for remaining prices
        for price in prices[period:]:
            ema = price * k + ema * (1 - k)
        
        return self._round(ema)

    def calculate_macd(
        self,
        prices: list[Decimal],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Optional[dict]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        MACD Line = 12-day EMA - 26-day EMA
        Signal Line = 9-day EMA of MACD Line
        Histogram = MACD Line - Signal Line
        """
        if len(prices) < slow_period:
            return None
        
        # Calculate EMAs
        ema_fast = self.calculate_ema(prices, fast_period)
        ema_slow = self.calculate_ema(prices, slow_period)
        
        if ema_fast is None or ema_slow is None:
            return None
        
        macd_line = ema_fast - ema_slow
        
        # For signal line, we need MACD history
        # Simplified: calculate MACD for recent periods
        macd_history = []
        for i in range(signal_period + slow_period, len(prices) + 1):
            subset = prices[:i]
            fast = self.calculate_ema(subset, fast_period)
            slow = self.calculate_ema(subset, slow_period)
            if fast and slow:
                macd_history.append(fast - slow)
        
        if len(macd_history) < signal_period:
            signal_line = macd_line  # Fallback
        else:
            # Signal = EMA of MACD values
            k = Decimal("2") / (signal_period + 1)
            signal = sum(macd_history[:signal_period]) / signal_period
            for m in macd_history[signal_period:]:
                signal = m * k + signal * (1 - k)
            signal_line = self._round(signal)
        
        histogram = macd_line - signal_line
        
        return {
            "macd_line": self._round(macd_line),
            "signal_line": self._round(signal_line),
            "histogram": self._round(histogram),
        }

    def calculate_bollinger_bands(
        self,
        prices: list[Decimal],
        period: int = 20,
        num_std: int = 2,
    ) -> Optional[dict]:
        """
        Calculate Bollinger Bands.
        
        Middle Band = SMA
        Upper Band = Middle + (num_std × std dev)
        Lower Band = Middle - (num_std × std dev)
        """
        if len(prices) < period:
            return None
        
        relevant_prices = prices[-period:]
        
        # Middle band = SMA
        middle = sum(relevant_prices) / period
        
        # Standard deviation
        variance = sum((p - middle) ** 2 for p in relevant_prices) / period
        std_dev = variance ** Decimal("0.5")
        
        upper = middle + (num_std * std_dev)
        lower = middle - (num_std * std_dev)
        
        return {
            "upper": self._round(upper),
            "middle": self._round(middle),
            "lower": self._round(lower),
            "width": self._round((upper - lower) / middle * 100),  # Width as %
        }

    def calculate_atr(
        self,
        ohlc: list[tuple[Decimal, Decimal, Decimal]],
        period: int = 14,
    ) -> Optional[Decimal]:
        """
        Calculate Average True Range.
        
        True Range = max of:
            - High - Low
            - |High - Previous Close|
            - |Low - Previous Close|
        ATR = Average of True Range over period
        
        Args:
            ohlc: List of (high, low, close) tuples
            period: ATR period (default 14)
        """
        if len(ohlc) < period:
            return None
        
        true_ranges = []
        
        for i, (high, low, close) in enumerate(ohlc):
            if i == 0:
                # First day: TR = High - Low
                tr = high - low
            else:
                prev_close = ohlc[i - 1][2]
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close),
                )
            true_ranges.append(tr)
        
        # ATR = Average of last 'period' true ranges
        atr = sum(true_ranges[-period:]) / period
        
        return self._round(atr)

