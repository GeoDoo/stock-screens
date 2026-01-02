"""
Unit tests for technical analysis calculations.

TDD: Writing tests ONE AT A TIME, running each to see it fail first.
"""

import pytest
from decimal import Decimal

from app.services.technical import TechnicalService


class TestMovingAverages:
    """Tests for moving average calculations."""

    def test_sma_basic_calculation(self):
        """
        Test Simple Moving Average calculation.
        
        SMA = sum of prices / number of periods
        
        Given prices: [10, 11, 12, 13, 14] (5 days)
        SMA(5) = (10 + 11 + 12 + 13 + 14) / 5 = 60 / 5 = 12
        """
        service = TechnicalService()
        
        prices = [Decimal("10"), Decimal("11"), Decimal("12"), Decimal("13"), Decimal("14")]
        
        result = service.calculate_sma(prices, period=5)
        
        assert result == Decimal("12")


class TestRSI:
    """Tests for Relative Strength Index calculation."""

    def test_rsi_basic_calculation(self):
        """
        Test RSI calculation.
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        
        Given 14 days of price changes:
        If avg gain = 1.0 and avg loss = 0.5
        RS = 1.0 / 0.5 = 2.0
        RSI = 100 - (100 / 3) = 66.67
        """
        service = TechnicalService()
        
        # Create prices with clear up/down pattern
        # Start at 100, alternate +2, -1 pattern for 15 days
        prices = [
            Decimal("100"), Decimal("102"), Decimal("101"),
            Decimal("103"), Decimal("102"), Decimal("104"),
            Decimal("103"), Decimal("105"), Decimal("104"),
            Decimal("106"), Decimal("105"), Decimal("107"),
            Decimal("106"), Decimal("108"), Decimal("107"),
        ]
        
        result = service.calculate_rsi(prices, period=14)
        
        assert result is not None
        assert Decimal("0") <= result <= Decimal("100")


class TestMACD:
    """Tests for MACD calculation."""

    def test_macd_basic_calculation(self):
        """
        Test MACD calculation.
        
        MACD Line = 12-day EMA - 26-day EMA
        Signal Line = 9-day EMA of MACD Line
        Histogram = MACD Line - Signal Line
        """
        service = TechnicalService()
        
        # Need at least 26 prices for MACD
        prices = [Decimal(str(100 + i)) for i in range(30)]
        
        result = service.calculate_macd(prices)
        
        assert result is not None
        assert "macd_line" in result
        assert "signal_line" in result
        assert "histogram" in result


class TestBollingerBands:
    """Tests for Bollinger Bands calculation."""

    def test_bollinger_bands_basic(self):
        """
        Test Bollinger Bands calculation.
        
        Middle Band = 20-day SMA
        Upper Band = Middle + (2 × 20-day std dev)
        Lower Band = Middle - (2 × 20-day std dev)
        """
        service = TechnicalService()
        
        # 20 prices around 100
        prices = [Decimal(str(100 + (i % 5) - 2)) for i in range(20)]
        
        result = service.calculate_bollinger_bands(prices, period=20)
        
        assert result is not None
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result
        assert result["upper"] > result["middle"] > result["lower"]


class TestATR:
    """Tests for Average True Range calculation."""

    def test_atr_basic(self):
        """
        Test ATR calculation.
        
        True Range = max of:
            - High - Low
            - |High - Previous Close|
            - |Low - Previous Close|
        ATR = Average of True Range over period
        """
        service = TechnicalService()
        
        # OHLC data: list of (high, low, close)
        ohlc = [
            (Decimal("105"), Decimal("95"), Decimal("100")),
            (Decimal("108"), Decimal("98"), Decimal("103")),
            (Decimal("110"), Decimal("100"), Decimal("105")),
            (Decimal("107"), Decimal("97"), Decimal("102")),
            (Decimal("109"), Decimal("99"), Decimal("104")),
        ]
        
        result = service.calculate_atr(ohlc, period=5)
        
        assert result is not None
        assert result > Decimal("0")

