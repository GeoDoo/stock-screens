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


class TestVWAP:
    """
    Tests for VWAP (Volume Weighted Average Price).
    
    From Gemini review: Professional technical analysis requires volume confirmation.
    VWAP = Σ(Typical Price × Volume) / Σ(Volume)
    Where Typical Price = (High + Low + Close) / 3
    """
    
    def test_vwap_basic_calculation(self):
        """VWAP should weight prices by volume."""
        closes = [100.0, 110.0, 90.0, 100.0]
        highs = [105.0, 115.0, 95.0, 105.0]
        lows = [95.0, 105.0, 85.0, 95.0]
        volumes = [1000, 2000, 500, 1500]  # High volume at $110
        
        vwap = TechnicalIndicators.vwap(closes, highs, lows, volumes)
        
        # High volume at $110 should pull VWAP higher than simple average
        simple_avg = sum(closes) / len(closes)  # = 100
        assert vwap[-1] > simple_avg, "VWAP should be higher due to high volume at $110"
    
    def test_vwap_equal_volume(self):
        """With equal volume, VWAP should equal simple average of typical price."""
        closes = [100.0, 110.0, 90.0, 100.0]
        highs = [105.0, 115.0, 95.0, 105.0]
        lows = [95.0, 105.0, 85.0, 95.0]
        volumes = [1000, 1000, 1000, 1000]  # Equal volume
        
        vwap = TechnicalIndicators.vwap(closes, highs, lows, volumes)
        
        # Typical prices
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        avg_typical = sum(typical_prices) / len(typical_prices)
        
        assert vwap[-1] == pytest.approx(avg_typical, rel=0.01)
    
    def test_vwap_returns_series(self):
        """VWAP should return cumulative values for each bar."""
        closes = [100.0, 110.0, 105.0]
        highs = [105.0, 115.0, 110.0]
        lows = [95.0, 105.0, 100.0]
        volumes = [1000, 2000, 1500]
        
        vwap = TechnicalIndicators.vwap(closes, highs, lows, volumes)
        
        assert len(vwap) == 3
        # All values should be non-None
        assert all(v is not None for v in vwap)
    
    def test_vwap_empty_data(self):
        """VWAP should handle empty data."""
        vwap = TechnicalIndicators.vwap([], [], [], [])
        assert vwap == []


class TestVolumeMetrics:
    """Tests for volume analysis metrics."""
    
    def test_average_volume_calculation(self):
        """Average volume should be calculated correctly."""
        volumes = [1000, 2000, 1500, 2500, 1000]
        
        avg = TechnicalIndicators.average_volume(volumes, period=5)
        
        assert avg == pytest.approx(1600.0, rel=0.01)  # (1000+2000+1500+2500+1000)/5
    
    def test_relative_volume(self):
        """Relative volume compares current to average."""
        volumes = [1000, 1000, 1000, 1000, 3000]  # Last bar has 3x volume
        
        rel_vol = TechnicalIndicators.relative_volume(volumes, period=4)
        
        # Current (3000) vs avg of first 4 (1000) = 3.0x
        assert rel_vol == pytest.approx(3.0, rel=0.01)
    
    def test_relative_volume_below_average(self):
        """Relative volume < 1.0 indicates below average."""
        volumes = [2000, 2000, 2000, 2000, 500]  # Last bar is 1/4 of average
        
        rel_vol = TechnicalIndicators.relative_volume(volumes, period=4)
        
        assert rel_vol == pytest.approx(0.25, rel=0.01)


class TestVolumeConfirmation:
    """
    Tests for volume confirmation of signals.
    
    A breakout on high volume is more reliable than one on low volume.
    """
    
    def test_volume_confirms_bullish_signal(self):
        """High volume should confirm bullish trend."""
        volumes = [1000, 1000, 1000, 3000]  # Surge in volume
        trend = "bullish"
        
        confirmation = TechnicalIndicators.volume_confirms_trend(volumes, trend, period=3)
        
        assert confirmation == "confirmed", "High relative volume should confirm bullish"
    
    def test_volume_weak_signal(self):
        """Low volume should mark signal as weak."""
        volumes = [2000, 2000, 2000, 500]  # Volume drops
        trend = "bullish"
        
        confirmation = TechnicalIndicators.volume_confirms_trend(volumes, trend, period=3)
        
        assert confirmation == "weak", "Low relative volume should mark as weak"
    
    def test_neutral_trend_no_confirmation(self):
        """Neutral trend doesn't need volume confirmation."""
        volumes = [1000, 1000, 1000, 1000]
        trend = "neutral"
        
        confirmation = TechnicalIndicators.volume_confirms_trend(volumes, trend, period=3)
        
        assert confirmation == "neutral"


class TestVWMA:
    """Tests for Volume Weighted Moving Average."""
    
    def test_vwma_basic(self):
        """VWMA should weight prices by volume."""
        prices = [10, 20]
        volumes = [100, 300]  # Second price has 3x volume
        
        result = TechnicalIndicators.vwma(prices, volumes, period=2)
        
        # VWMA = (10*100 + 20*300) / (100 + 300) = (1000 + 6000) / 400 = 17.5
        assert result[-1] == pytest.approx(17.5, rel=0.01)
    
    def test_vwma_vs_sma_high_volume_at_higher_price(self):
        """VWMA > SMA when high volume at higher prices."""
        prices = [10, 20, 30]
        volumes = [100, 100, 500]  # High volume at highest price
        
        vwma = TechnicalIndicators.vwma(prices, volumes, period=3)
        sma = TechnicalIndicators.sma(prices, period=3)
        
        # VWMA should be pulled toward 30 (high volume price)
        assert vwma[-1] > sma[-1]
    
    def test_vwma_returns_none_initially(self):
        """VWMA should return None for initial period."""
        prices = [10, 20, 30, 40, 50]
        volumes = [100, 100, 100, 100, 100]
        
        result = TechnicalIndicators.vwma(prices, volumes, period=3)
        
        assert result[0] is None
        assert result[1] is None
        assert result[2] is not None


class TestOBV:
    """Tests for On-Balance Volume."""
    
    def test_obv_up_days(self):
        """OBV should add volume on up days."""
        prices = [10, 12]  # Up day
        volumes = [100, 200]
        
        result = TechnicalIndicators.obv(prices, volumes)
        
        # Starts at 0, adds 200 on up day
        assert result[0] == 0
        assert result[1] == 200
    
    def test_obv_down_days(self):
        """OBV should subtract volume on down days."""
        prices = [10, 8]  # Down day
        volumes = [100, 200]
        
        result = TechnicalIndicators.obv(prices, volumes)
        
        # Starts at 0, subtracts 200 on down day
        assert result[0] == 0
        assert result[1] == -200
    
    def test_obv_accumulation_pattern(self):
        """OBV should increase with consistent accumulation."""
        prices = [10, 11, 12, 13, 14]  # All up
        volumes = [100, 100, 100, 100, 100]
        
        result = TechnicalIndicators.obv(prices, volumes)
        
        # Cumulative: 0, 100, 200, 300, 400
        assert result[-1] == 400
    
    def test_obv_trend_detection(self):
        """Should detect OBV trend direction."""
        # Strong accumulation pattern
        obv_accumulating = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
                           1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        
        trend = TechnicalIndicators.obv_trend(obv_accumulating, period=20)
        
        assert trend == "accumulation"
    
    def test_obv_distribution_pattern(self):
        """Should detect distribution pattern."""
        # Strong distribution pattern (declining OBV)
        obv_distributing = [1000, 900, 800, 700, 600, 500, 400, 300, 200, 100,
                           0, -100, -200, -300, -400, -500, -600, -700, -800, -900]
        
        trend = TechnicalIndicators.obv_trend(obv_distributing, period=20)
        
        assert trend == "distribution"
    
    def test_obv_trend_zero_crossing(self):
        """Should detect trend even when OBV crosses zero (mean is ~0)."""
        # OBV goes from positive to negative - mean is close to 0
        # but there's a clear distribution pattern
        obv_crossing = [500, 400, 300, 200, 100, 0, -100, -200, -300, -400,
                        -500, -600, -700, -800, -900, -1000, -1100, -1200, -1300, -1400]
        
        trend = TechnicalIndicators.obv_trend(obv_crossing, period=20)
        
        # Should detect distribution, NOT neutral (bug was returning neutral)
        assert trend == "distribution", f"Zero-crossing OBV should detect distribution, got {trend}"
    
    def test_obv_trend_accumulation_from_negative(self):
        """Should detect accumulation when OBV rises from negative to positive."""
        obv_rising = [-1400, -1300, -1200, -1100, -1000, -900, -800, -700, -600, -500,
                      -400, -300, -200, -100, 0, 100, 200, 300, 400, 500]
        
        trend = TechnicalIndicators.obv_trend(obv_rising, period=20)
        
        assert trend == "accumulation"


class TestMFI:
    """Tests for Money Flow Index (volume-weighted RSI)."""
    
    def test_mfi_basic_calculation(self):
        """MFI should produce values between 0-100."""
        # Create simple test data
        highs = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
        lows = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        closes = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
        volumes = [1000] * 15
        
        result = TechnicalIndicators.mfi(highs, lows, closes, volumes, period=14)
        
        # Should have valid values after period
        valid_values = [v for v in result if v is not None]
        assert len(valid_values) > 0
        
        for v in valid_values:
            assert 0 <= v <= 100
    
    def test_mfi_high_buying_pressure(self):
        """MFI should be high when consistent buying pressure."""
        # All prices rising = positive money flow
        highs = list(range(20, 35))
        lows = list(range(18, 33))
        closes = list(range(19, 34))
        volumes = [1000] * 15
        
        result = TechnicalIndicators.mfi(highs, lows, closes, volumes, period=14)
        
        # Last value should be high (strong buying)
        last_mfi = result[-1]
        assert last_mfi is not None
        assert last_mfi > 50, "Rising prices should produce MFI > 50"
    
    def test_mfi_signal_overbought(self):
        """MFI >= 80 should signal overbought."""
        mfi_values = [None] * 14 + [85.0]
        
        signal = TechnicalIndicators.analyze_mfi(mfi_values)
        
        assert signal == "overbought"
    
    def test_mfi_signal_oversold(self):
        """MFI <= 20 should signal oversold."""
        mfi_values = [None] * 14 + [15.0]
        
        signal = TechnicalIndicators.analyze_mfi(mfi_values)
        
        assert signal == "oversold"
    
    def test_mfi_signal_neutral(self):
        """MFI between 20-80 should be neutral."""
        mfi_values = [None] * 14 + [50.0]
        
        signal = TechnicalIndicators.analyze_mfi(mfi_values)
        
        assert signal == "neutral"
    
    def test_mfi_no_price_movement_is_neutral(self):
        """MFI should be 50 (neutral) when no price movement."""
        # All prices the same = no positive or negative flow
        highs = [20] * 15
        lows = [18] * 15
        closes = [19] * 15  # All same price
        volumes = [1000] * 15
        
        result = TechnicalIndicators.mfi(highs, lows, closes, volumes, period=14)
        
        # Should be 50 (neutral), not 100 (overbought)
        last_mfi = result[-1]
        assert last_mfi == 50.0, f"No price movement should give MFI=50, got {last_mfi}"
