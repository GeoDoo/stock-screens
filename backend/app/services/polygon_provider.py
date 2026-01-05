"""
Polygon (Massive) provider for historical price data.
Used for technical analysis - OHLCV bars.
"""
import httpx
from typing import List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class PriceBar:
    """Single OHLCV price bar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class PolygonProviderError(Exception):
    """Error from Polygon API."""
    pass


class PolygonProvider:
    """
    Polygon.io (now Massive) data provider for historical prices.
    """
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def _request(self, endpoint: str, **params) -> dict:
        """Make authenticated request to Polygon API."""
        async with httpx.AsyncClient() as client:
            params["apiKey"] = self.api_key
            response = await client.get(
                f"{self.BASE_URL}{endpoint}",
                params=params,
                timeout=30.0,
            )
            
            if response.status_code == 401:
                raise PolygonProviderError("Invalid Polygon API key")
            elif response.status_code == 403:
                raise PolygonProviderError("Polygon API access denied")
            elif response.status_code == 429:
                raise PolygonProviderError("Polygon rate limit exceeded")
            elif response.status_code >= 400:
                raise PolygonProviderError(f"Polygon API error: {response.status_code}")
            
            return response.json()
    
    async def get_daily_bars(
        self,
        symbol: str,
        days: int = 365,
        end_date: Optional[datetime] = None,
    ) -> List[PriceBar]:
        """
        Fetch daily OHLCV bars for a symbol.
        
        Args:
            symbol: Stock ticker (e.g., "AAPL")
            days: Number of days of history
            end_date: End date (defaults to today)
            
        Returns:
            List of PriceBar objects, oldest first
        """
        if end_date is None:
            end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format dates as YYYY-MM-DD
        from_date = start_date.strftime("%Y-%m-%d")
        to_date = end_date.strftime("%Y-%m-%d")
        
        # Polygon aggregates endpoint
        endpoint = f"/v2/aggs/ticker/{symbol.upper()}/range/1/day/{from_date}/{to_date}"
        
        data = await self._request(
            endpoint,
            adjusted="true",
            sort="asc",
            limit=50000,
        )
        
        if data.get("status") == "ERROR":
            raise PolygonProviderError(data.get("error", "Unknown error"))
        
        results = data.get("results", [])
        if not results:
            raise PolygonProviderError(f"No price data found for {symbol}")
        
        bars = []
        for r in results:
            bars.append(PriceBar(
                timestamp=datetime.fromtimestamp(r["t"] / 1000),  # ms to seconds
                open=r["o"],
                high=r["h"],
                low=r["l"],
                close=r["c"],
                volume=r["v"],
            ))
        
        return bars
    
    async def get_intraday_bars(
        self,
        symbol: str,
        multiplier: int = 5,
        timespan: str = "minute",
        days: int = 5,
    ) -> List[PriceBar]:
        """
        Fetch intraday OHLCV bars.
        
        Args:
            symbol: Stock ticker
            multiplier: Bar size multiplier (e.g., 5 for 5-minute bars)
            timespan: "minute", "hour"
            days: Days of history (max ~5-7 for minute data)
            
        Returns:
            List of PriceBar objects
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        from_date = start_date.strftime("%Y-%m-%d")
        to_date = end_date.strftime("%Y-%m-%d")
        
        endpoint = f"/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        
        data = await self._request(
            endpoint,
            adjusted="true",
            sort="asc",
            limit=50000,
        )
        
        results = data.get("results", [])
        if not results:
            raise PolygonProviderError(f"No intraday data found for {symbol}")
        
        bars = []
        for r in results:
            bars.append(PriceBar(
                timestamp=datetime.fromtimestamp(r["t"] / 1000),
                open=r["o"],
                high=r["h"],
                low=r["l"],
                close=r["c"],
                volume=r["v"],
            ))
        
        return bars

