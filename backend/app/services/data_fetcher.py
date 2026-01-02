"""Data fetcher service using Yahoo Finance."""

import asyncio
import logging
from decimal import Decimal
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

from app.models.stock import Stock, StockFundamentals, StockPrice

logger = logging.getLogger(__name__)

# Thread pool for yfinance (which is synchronous)
_executor = ThreadPoolExecutor(max_workers=5)


class DataFetcherService:
    """Service for fetching stock data from Yahoo Finance."""

    def _fetch_ticker_sync(self, symbol: str) -> Optional[dict]:
        """Synchronous fetch (runs in thread pool)."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if valid
            if not info or "symbol" not in info:
                return None
            
            return info
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None

    async def fetch_stock(self, symbol: str) -> Optional[Stock]:
        """
        Fetch stock data from Yahoo Finance.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Stock object with fundamentals, or None if not found
        """
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(_executor, self._fetch_ticker_sync, symbol)
        
        if not info:
            return None
        
        # Parse fundamentals
        data_gaps = []
        
        def get_decimal(key: str, default=None) -> Optional[Decimal]:
            val = info.get(key)
            if val is None:
                data_gaps.append(key)
                return default
            try:
                return Decimal(str(val))
            except:
                return default
        
        def get_int(key: str, default=None) -> Optional[int]:
            val = info.get(key)
            if val is None:
                data_gaps.append(key)
                return default
            try:
                return int(val)
            except:
                return default
        
        fundamentals = StockFundamentals(
            # Valuation ratios
            pe_ratio=get_decimal("trailingPE"),
            forward_pe=get_decimal("forwardPE"),
            pb_ratio=get_decimal("priceToBook"),
            ps_ratio=get_decimal("priceToSalesTrailing12Months"),
            peg_ratio=get_decimal("pegRatio"),
            ev_ebitda=get_decimal("enterpriseToEbitda"),
            
            # Per share
            eps=get_decimal("trailingEps"),
            eps_forward=get_decimal("forwardEps"),
            book_value_per_share=get_decimal("bookValue"),
            revenue_per_share=get_decimal("revenuePerShare"),
            
            # Profitability
            profit_margin=self._to_percent(get_decimal("profitMargins")),
            operating_margin=self._to_percent(get_decimal("operatingMargins")),
            gross_margin=self._to_percent(get_decimal("grossMargins")),
            roe=self._to_percent(get_decimal("returnOnEquity")),
            roa=self._to_percent(get_decimal("returnOnAssets")),
            
            # Growth
            revenue_growth=self._to_percent(get_decimal("revenueGrowth")),
            earnings_growth=self._to_percent(get_decimal("earningsGrowth")),
            
            # Balance sheet
            total_debt=get_decimal("totalDebt"),
            total_cash=get_decimal("totalCash"),
            debt_to_equity=get_decimal("debtToEquity"),
            current_ratio=get_decimal("currentRatio"),
            quick_ratio=get_decimal("quickRatio"),
            
            # Other
            market_cap=get_decimal("marketCap"),
            enterprise_value=get_decimal("enterpriseValue"),
            shares_outstanding=get_int("sharesOutstanding"),
            float_shares=get_int("floatShares"),
            dividend_yield=self._to_percent(get_decimal("dividendYield")),
            beta=get_decimal("beta"),
            
            data_gaps=data_gaps,
        )
        
        # Parse price
        price = StockPrice(
            current=get_decimal("currentPrice") or get_decimal("regularMarketPrice") or Decimal("0"),
            open=get_decimal("regularMarketOpen") or Decimal("0"),
            high=get_decimal("regularMarketDayHigh") or Decimal("0"),
            low=get_decimal("regularMarketDayLow") or Decimal("0"),
            close=get_decimal("regularMarketPreviousClose") or Decimal("0"),
            volume=get_int("regularMarketVolume") or 0,
            fifty_two_week_high=get_decimal("fiftyTwoWeekHigh"),
            fifty_two_week_low=get_decimal("fiftyTwoWeekLow"),
            avg_volume_10d=get_int("averageDailyVolume10Day"),
            avg_volume_3m=get_int("averageVolume"),
        )
        
        # Calculate data quality score
        total_fields = 30
        available_fields = total_fields - len(data_gaps)
        quality_score = Decimal(str(max(0, available_fields / total_fields * 100)))
        
        return Stock(
            symbol=info.get("symbol", symbol).upper(),
            name=info.get("shortName") or info.get("longName") or symbol,
            sector=info.get("sector"),
            industry=info.get("industry"),
            exchange=info.get("exchange"),
            currency=info.get("currency", "USD"),
            price=price,
            fundamentals=fundamentals,
            data_quality_score=quality_score,
        )

    def _to_percent(self, val: Optional[Decimal]) -> Optional[Decimal]:
        """Convert decimal ratio to percentage."""
        if val is None:
            return None
        return val * 100

    async def fetch_stocks(self, symbols: List[str]) -> List[Stock]:
        """
        Fetch multiple stocks concurrently.
        
        Args:
            symbols: List of ticker symbols
        
        Returns:
            List of Stock objects (excludes failures)
        """
        tasks = [self.fetch_stock(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    async def fetch_historical_prices(
        self,
        symbol: str,
        period: str = "1y",
    ) -> Optional[list]:
        """
        Fetch historical price data for technical analysis.
        
        Args:
            symbol: Stock ticker
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
        Returns:
            List of OHLCV data
        """
        def _fetch_history():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                if hist.empty:
                    return None
                
                return [
                    {
                        "date": str(idx.date()),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    }
                    for idx, row in hist.iterrows()
                ]
            except Exception as e:
                logger.error(f"Error fetching history for {symbol}: {e}")
                return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _fetch_history)

