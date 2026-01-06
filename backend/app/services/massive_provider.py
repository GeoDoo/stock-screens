"""
Massive (formerly Polygon.io) provider for historical price data.
Technical analysis specialist - excellent OHLCV data quality.
Does NOT support fundamental analysis.
"""
import httpx
from datetime import datetime, timedelta

from app.services.base_provider import (
    StockDataProvider,
    StockData,
    CompanyProfile,
    FinancialStatement,
    ProviderError,
    TickerNotFoundError,
    DataNotAvailableError,
    RateLimitError,
    HistoricalPrices,
    PriceBar,
)


class MassiveProvider(StockDataProvider):
    """
    Massive (Polygon.io) data provider.
    Specialized for technical analysis - best quality price data.
    Does NOT support fundamental analysis.
    """
    
    name = "massive"
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    @property
    def supports_fundamentals(self) -> bool:
        return False  # Massive doesn't have detailed fundamentals
    
    @property
    def supports_technical(self) -> bool:
        return True
    
    async def _request(self, endpoint: str, **params) -> dict:
        """Make authenticated request to Massive/Polygon API."""
        async with httpx.AsyncClient() as client:
            params["apiKey"] = self.api_key
            response = await client.get(
                f"{self.BASE_URL}{endpoint}",
                params=params,
                timeout=30.0,
            )
            
            if response.status_code == 401:
                raise ProviderError("Invalid Massive API key")
            elif response.status_code == 403:
                raise ProviderError("Massive API access denied")
            elif response.status_code == 429:
                raise RateLimitError("Massive rate limit exceeded")
            elif response.status_code >= 400:
                raise ProviderError(f"Massive API error: {response.status_code}")
            
            return response.json()
    
    async def get_stock_data(self, symbol: str) -> StockData:
        """
        Massive doesn't support full fundamental data.
        Raises NotImplementedError - use Yahoo or FMP for fundamentals.
        """
        raise NotImplementedError(
            "Massive provider does not support fundamental analysis. "
            "Use Yahoo Finance or FMP for fundamentals."
        )
    
    async def get_treasury_rate(self) -> float:
        """Massive doesn't have treasury data, return default."""
        return 0.045
    
    async def get_historical_prices(self, symbol: str, days: int = 365) -> HistoricalPrices:
        """Fetch historical OHLCV data from Massive (Polygon)."""
        symbol = symbol.upper()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        from_date = start_date.strftime("%Y-%m-%d")
        to_date = end_date.strftime("%Y-%m-%d")
        
        # Polygon aggregates endpoint
        endpoint = f"/v2/aggs/ticker/{symbol}/range/1/day/{from_date}/{to_date}"
        
        data = await self._request(
            endpoint,
            adjusted="true",
            sort="asc",
            limit=50000,
        )
        
        if data.get("status") == "ERROR":
            error_msg = data.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                raise TickerNotFoundError(f"Ticker '{symbol}' not found")
            raise ProviderError(error_msg)
        
        results = data.get("results", [])
        if not results:
            raise DataNotAvailableError(f"No price data for {symbol}")
        
        bars = []
        for r in results:
            bars.append(PriceBar(
                timestamp=datetime.fromtimestamp(r["t"] / 1000).strftime("%Y-%m-%d"),
                open=round(r["o"], 2),
                high=round(r["h"], 2),
                low=round(r["l"], 2),
                close=round(r["c"], 2),
                volume=int(r["v"]),
            ))
        
        return HistoricalPrices(
            symbol=symbol,
            bars=bars,
            provider=self.name,
        )


