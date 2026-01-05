"""
Technical Analysis Service.
Works with any provider that supports historical prices.
"""
from typing import List

from app.services.base_provider import StockDataProvider, PriceBar, HistoricalPrices
from app.services.technical_indicators import (
    TechnicalIndicators,
    TechnicalAnalysisResult,
    IndicatorValue,
    MACDValue,
)


class TechnicalService:
    """
    Service for running technical analysis on a stock.
    Uses any provider that supports get_historical_prices().
    """
    
    def __init__(self, provider: StockDataProvider):
        """
        Initialize with a provider that supports technical analysis.
        
        Args:
            provider: Any StockDataProvider with supports_technical=True
        """
        if not provider.supports_technical:
            raise ValueError(f"{provider.name} does not support technical analysis")
        self.provider = provider
    
    async def analyze(self, symbol: str, days: int = 365) -> TechnicalAnalysisResult:
        """
        Run full technical analysis on a stock.
        
        Args:
            symbol: Stock ticker
            days: Days of history to analyze
            
        Returns:
            TechnicalAnalysisResult with all indicators
        """
        # Fetch price data from provider
        historical = await self.provider.get_historical_prices(symbol, days=days)
        bars = historical.bars
        
        if not bars:
            raise ValueError(f"No price data for {symbol}")
        
        # Extract close prices for indicators
        closes = [bar.close for bar in bars]
        
        # Calculate indicators
        sma_20_values = TechnicalIndicators.sma(closes, 20)
        sma_50_values = TechnicalIndicators.sma(closes, 50)
        ema_12_values = TechnicalIndicators.ema(closes, 12)
        ema_26_values = TechnicalIndicators.ema(closes, 26)
        rsi_14_values = TechnicalIndicators.rsi(closes, 14)
        macd_line, signal_line, histogram = TechnicalIndicators.macd(closes)
        
        # Format for response
        def to_indicator_values(values: List, bars: List[PriceBar]) -> List[IndicatorValue]:
            result = []
            for i, val in enumerate(values):
                if val is not None:
                    result.append(IndicatorValue(
                        timestamp=bars[i].timestamp,
                        value=round(val, 2),
                    ))
            return result
        
        # Format MACD
        macd_values = []
        for i, (m, s, h) in enumerate(zip(macd_line, signal_line, histogram)):
            if m is not None and s is not None and h is not None:
                macd_values.append(MACDValue(
                    timestamp=bars[i].timestamp,
                    macd=round(m, 4),
                    signal=round(s, 4),
                    histogram=round(h, 4),
                ))
        
        # Format price data for charting
        prices = [
            {
                "timestamp": bar.timestamp,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for bar in bars
        ]
        
        # Calculate price change
        first_close = bars[0].close
        last_close = bars[-1].close
        price_change_pct = ((last_close - first_close) / first_close) * 100
        
        # Analyze signals
        trend = TechnicalIndicators.analyze_trend(sma_20_values, sma_50_values, closes)
        rsi_signal = TechnicalIndicators.analyze_rsi(rsi_14_values)
        macd_signal = TechnicalIndicators.analyze_macd(macd_line, signal_line)
        
        return TechnicalAnalysisResult(
            symbol=symbol.upper(),
            period_days=days,
            current_price=round(last_close, 2),
            price_change_pct=round(price_change_pct, 2),
            prices=prices,
            sma_20=to_indicator_values(sma_20_values, bars),
            sma_50=to_indicator_values(sma_50_values, bars),
            ema_12=to_indicator_values(ema_12_values, bars),
            ema_26=to_indicator_values(ema_26_values, bars),
            rsi_14=to_indicator_values(rsi_14_values, bars),
            macd=macd_values,
            trend=trend,
            rsi_signal=rsi_signal,
            macd_signal=macd_signal,
        )
