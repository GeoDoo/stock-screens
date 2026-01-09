import pytest
from app.services.technical_indicators import TechnicalIndicators


class TestSMA:
    def test_sma_basic(self):
        """SMA should calculate correct average."""
        prices = [10, 20, 30, 40, 50]
        result = TechnicalIndicators.sma(prices, period=3)
        
        # First 2 values should be None (need 3 for period)
        assert result[0] is None
        assert result[1] is None
        # Third value: (10+20+30)/3 = 20
        assert result[2] == 20
        # Fourth value: (20+30+40)/3 = 30
        assert result[3] == 30
        # Fifth value: (30+40+50)/3 = 40
        assert result[4] == 40

    def test_sma_returns_same_length(self):
        """SMA output should be same length as input."""
        prices = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = TechnicalIndicators.sma(prices, period=5)
        
        assert len(result) == len(prices)

    def test_sma_period_larger_than_data(self):
        """Should return all None if period > data length."""
        prices = [10, 20, 30]
        result = TechnicalIndicators.sma(prices, period=5)
        
        assert all(v is None for v in result)


class TestEMA:
    def test_ema_basic(self):
        """EMA should calculate values after initial period."""
        prices = [10, 11, 12, 13, 14, 15]
        result = TechnicalIndicators.ema(prices, period=3)
        
        # First 2 values should be None
        assert result[0] is None
        assert result[1] is None
        # Third value is SMA seed: (10+11+12)/3 = 11
        assert result[2] == 11

    def test_ema_returns_same_length(self):
        """EMA output should be same length as input."""
        prices = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = TechnicalIndicators.ema(prices, period=5)
        
        assert len(result) == len(prices)

    def test_ema_more_responsive_than_sma(self):
        """EMA should react faster to recent price changes."""
        # Prices with sudden jump
        prices = [10, 10, 10, 10, 10, 20, 20, 20]
        
        sma = TechnicalIndicators.sma(prices, period=5)
        ema = TechnicalIndicators.ema(prices, period=5)
        
        # After the jump, EMA should be closer to current price than SMA
        # Compare at last position
        assert ema[-1] > sma[-1]

    def test_ema_insufficient_data(self):
        """Should return all None if data < period."""
        prices = [10, 20]
        result = TechnicalIndicators.ema(prices, period=5)
        
        assert all(v is None for v in result)


class TestRSI:
    def test_rsi_range_0_to_100(self):
        """RSI values should be between 0 and 100."""
        prices = [44, 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 
                  45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
        result = TechnicalIndicators.rsi(prices, period=14)
        
        for val in result:
            if val is not None:
                assert 0 <= val <= 100

    def test_rsi_returns_same_length(self):
        """RSI output should be same length as input."""
        prices = list(range(1, 31))
        result = TechnicalIndicators.rsi(prices, period=14)
        
        assert len(result) == len(prices)

    def test_rsi_first_n_values_none(self):
        """First period values should be None."""
        prices = list(range(1, 31))
        result = TechnicalIndicators.rsi(prices, period=14)
        
        # First 14 values should be None
        for i in range(14):
            assert result[i] is None

    def test_rsi_strong_uptrend(self):
        """Strong uptrend should have RSI > 50."""
        # Steady upward prices
        prices = list(range(100, 130))
        result = TechnicalIndicators.rsi(prices, period=14)
        
        # Get last RSI value
        last_rsi = next(v for v in reversed(result) if v is not None)
        assert last_rsi > 50

    def test_rsi_strong_downtrend(self):
        """Strong downtrend should have RSI < 50."""
        # Steady downward prices
        prices = list(range(130, 100, -1))
        result = TechnicalIndicators.rsi(prices, period=14)
        
        last_rsi = next(v for v in reversed(result) if v is not None)
        assert last_rsi < 50

    def test_rsi_all_gains_is_100(self):
        """RSI should be 100 when all changes are gains."""
        # Strictly increasing prices
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
        result = TechnicalIndicators.rsi(prices, period=14)
        
        last_rsi = next(v for v in reversed(result) if v is not None)
        assert last_rsi == 100.0


class TestMACD:
    def test_macd_returns_three_lists(self):
        """MACD should return macd_line, signal_line, histogram."""
        prices = list(range(100, 150))
        macd_line, signal_line, histogram = TechnicalIndicators.macd(prices)
        
        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)
        assert len(histogram) == len(prices)

    def test_macd_line_calculation(self):
        """MACD line should be EMA(12) - EMA(26)."""
        prices = list(range(100, 150))
        macd_line, _, _ = TechnicalIndicators.macd(prices)
        
        ema_12 = TechnicalIndicators.ema(prices, 12)
        ema_26 = TechnicalIndicators.ema(prices, 26)
        
        # Check at a point where both EMAs have values
        for i in range(26, len(prices)):
            if ema_12[i] is not None and ema_26[i] is not None and macd_line[i] is not None:
                expected = ema_12[i] - ema_26[i]
                assert abs(macd_line[i] - expected) < 0.001

    def test_histogram_is_macd_minus_signal(self):
        """Histogram should be MACD - Signal."""
        prices = list(range(100, 150))
        macd_line, signal_line, histogram = TechnicalIndicators.macd(prices)
        
        for m, s, h in zip(macd_line, signal_line, histogram):
            if m is not None and s is not None and h is not None:
                assert abs(h - (m - s)) < 0.001


class TestTrendAnalysis:
    def test_bullish_trend(self):
        """Price > SMA20 > SMA50 should be bullish."""
        # Create data where this condition holds
        sma_20 = [None] * 19 + [100.0]
        sma_50 = [None] * 49 + [90.0]
        prices = [110.0] * 50
        
        result = TechnicalIndicators.analyze_trend(sma_20, sma_50, prices)
        assert result == "bullish"

    def test_bearish_trend(self):
        """Price < SMA20 < SMA50 should be bearish."""
        sma_20 = [None] * 19 + [90.0]
        sma_50 = [None] * 49 + [100.0]
        prices = [80.0] * 50
        
        result = TechnicalIndicators.analyze_trend(sma_20, sma_50, prices)
        assert result == "bearish"

    def test_neutral_trend(self):
        """Mixed signals should be neutral."""
        sma_20 = [100.0]
        sma_50 = [100.0]
        prices = [100.0]
        
        result = TechnicalIndicators.analyze_trend(sma_20, sma_50, prices)
        assert result == "neutral"

    def test_empty_data_neutral(self):
        """Empty data should return neutral."""
        result = TechnicalIndicators.analyze_trend([], [], [])
        assert result == "neutral"


class TestRSIAnalysis:
    def test_overbought(self):
        """RSI >= 70 should be overbought."""
        rsi_values = [None] * 13 + [75.0]
        result = TechnicalIndicators.analyze_rsi(rsi_values)
        assert result == "overbought"

    def test_oversold(self):
        """RSI <= 30 should be oversold."""
        rsi_values = [None] * 13 + [25.0]
        result = TechnicalIndicators.analyze_rsi(rsi_values)
        assert result == "oversold"

    def test_neutral_rsi(self):
        """RSI between 30 and 70 should be neutral."""
        rsi_values = [None] * 13 + [50.0]
        result = TechnicalIndicators.analyze_rsi(rsi_values)
        assert result == "neutral"

    def test_empty_rsi_neutral(self):
        """Empty RSI should return neutral."""
        result = TechnicalIndicators.analyze_rsi([None, None, None])
        assert result == "neutral"


class TestMACDAnalysis:
    def test_bullish_crossover(self):
        """MACD crossing above signal should be bullish."""
        macd_line = [None] * 25 + [-1.0, 1.0]  # crosses from below to above
        signal_line = [None] * 25 + [0.0, 0.0]
        
        result = TechnicalIndicators.analyze_macd(macd_line, signal_line)
        assert result == "bullish"

    def test_bearish_crossover(self):
        """MACD crossing below signal should be bearish."""
        macd_line = [None] * 25 + [1.0, -1.0]  # crosses from above to below
        signal_line = [None] * 25 + [0.0, 0.0]
        
        result = TechnicalIndicators.analyze_macd(macd_line, signal_line)
        assert result == "bearish"

    def test_bullish_continuation(self):
        """MACD above signal (no crossover) should still be bullish."""
        macd_line = [None] * 25 + [2.0, 3.0]  # staying above
        signal_line = [None] * 25 + [1.0, 1.0]
        
        result = TechnicalIndicators.analyze_macd(macd_line, signal_line)
        assert result == "bullish"

    def test_insufficient_data_neutral(self):
        """Insufficient data should return neutral."""
        macd_line = [1.0]
        signal_line = [0.5]
        
        result = TechnicalIndicators.analyze_macd(macd_line, signal_line)
        assert result == "neutral"


class TestTechnicalServiceEdgeCases:
    """
    Tests for TechnicalService edge cases.
    
    P0 Bug: price_change_pct calculation divides by first_close.
    If first_close == 0 (bad data), this causes ZeroDivisionError.
    """
    
    @pytest.mark.asyncio
    async def test_zero_first_close_handled_gracefully(self):
        """
        When first bar has close=0, should not crash with ZeroDivisionError.
        """
        from unittest.mock import AsyncMock, MagicMock
        from app.services.technical_service import TechnicalService
        from app.services.base_provider import PriceBar, HistoricalPrices
        from datetime import datetime
        
        # Create mock provider
        mock_provider = MagicMock()
        mock_provider.supports_technical = True
        mock_provider.name = "MockProvider"
        
        # Create bars with first close = 0 (edge case / bad data)
        bars = [
            PriceBar(
                timestamp=datetime(2024, 1, 1).isoformat(),
                open=0, high=0, low=0, close=0, volume=1000  # Zero close!
            ),
            PriceBar(
                timestamp=datetime(2024, 1, 2).isoformat(),
                open=100, high=105, low=95, close=100, volume=2000
            ),
        ]
        
        mock_provider.get_historical_prices = AsyncMock(
            return_value=HistoricalPrices(symbol="TEST", bars=bars, provider="Mock")
        )
        
        service = TechnicalService(mock_provider)
        
        # This should NOT raise ZeroDivisionError
        result = await service.analyze("TEST", days=30)
        
        # Should handle gracefully - price_change_pct should be exactly 0.0
        assert result is not None
        assert result.price_change_pct == 0.0
    
    @pytest.mark.asyncio
    async def test_normal_price_change_calculation(self):
        """
        Normal price change calculation should work correctly.
        """
        from unittest.mock import AsyncMock, MagicMock
        from app.services.technical_service import TechnicalService
        from app.services.base_provider import PriceBar, HistoricalPrices
        from datetime import datetime
        
        mock_provider = MagicMock()
        mock_provider.supports_technical = True
        mock_provider.name = "MockProvider"
        
        # Create bars with normal prices
        bars = [
            PriceBar(
                timestamp=datetime(2024, 1, 1).isoformat(),
                open=100, high=105, low=95, close=100, volume=1000
            ),
            PriceBar(
                timestamp=datetime(2024, 1, 2).isoformat(),
                open=100, high=115, low=95, close=110, volume=2000
            ),
        ]
        
        mock_provider.get_historical_prices = AsyncMock(
            return_value=HistoricalPrices(symbol="TEST", bars=bars, provider="Mock")
        )
        
        service = TechnicalService(mock_provider)
        result = await service.analyze("TEST", days=30)
        
        # Price went from 100 to 110 = 10% gain
        assert result.price_change_pct == pytest.approx(10.0, rel=0.01)
