"""
Massive (formerly Polygon.io) provider for historical price data.
Technical analysis specialist - excellent OHLCV data quality.
Does NOT support fundamental analysis.
"""
import httpx
from datetime import datetime, timedelta
from typing import Optional, Any

from app.constants import DEFAULT_TREASURY_RATE
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
    TransientProviderError,
)
from app.services.logging_config import logger # Use structlog logger
from app.services.resilience import retry_on_api_error


class MassiveProvider(StockDataProvider):
    """
    Massive (Polygon.io) data provider.
    Specialized for technical analysis - best quality price data.
    Does NOT support fundamental analysis.
    """
    
    name = "massive"
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: str, client: Optional[httpx.AsyncClient] = None):
        self.api_key = api_key
        self._client = client
    
    @property
    def supports_fundamentals(self) -> bool:
        return False  # Massive doesn't have detailed fundamentals
    
    @property
    def supports_technical(self) -> bool:
        return True
    
    @retry_on_api_error(retries=3, exceptions=(httpx.HTTPError, TransientProviderError))
    async def _request(self, endpoint: str, **params) -> Any:
        """Make authenticated request to Massive/Polygon API."""
        params["apiKey"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        
        logger.debug("api_request_start", provider="massive", endpoint=endpoint)
        
        if self._client is not None:
            response = await self._client.get(url, params=params, timeout=30.0)
            return self._process_response(response, endpoint)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                return self._process_response(response, endpoint)

    def _process_response(self, response: httpx.Response, endpoint: str) -> Any:
        """Process HTTP response."""
        logger.debug("api_response_received", provider="massive", endpoint=endpoint, status_code=response.status_code)
        
        if response.status_code == 401:
            logger.error("api_auth_error", provider="massive")
            raise ProviderError("Invalid Massive API key")
        elif response.status_code == 403:
            logger.error("api_access_denied", provider="massive")
            raise ProviderError("Massive API access denied")
        elif response.status_code == 429:
            logger.warning("api_rate_limit_hit", provider="massive")
            raise RateLimitError(f"Rate limit exceeded for {self.name}.")
        elif response.status_code >= 500:
            logger.error("api_server_error", provider="massive", status_code=response.status_code)
            raise TransientProviderError(f"Massive server error: {response.status_code}")
        elif response.status_code >= 400:
            logger.error("api_error", provider="massive", status_code=response.status_code)
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
        return DEFAULT_TREASURY_RATE
    
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


