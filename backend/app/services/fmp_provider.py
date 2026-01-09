import logging
import httpx
from typing import Any, List

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

from app.constants import DEFAULT_TREASURY_RATE

logger = logging.getLogger(__name__)


class FMPProvider(StockDataProvider):
    """Financial Modeling Prep data provider."""
    
    name = "fmp"
    BASE_URL = "https://financialmodelingprep.com/stable"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def _request(self, endpoint: str, **params) -> Any:
        async with httpx.AsyncClient() as client:
            params["apikey"] = self.api_key
            response = await client.get(f"{self.BASE_URL}{endpoint}", params=params)
            
            # Check for subscription/premium-only responses (FMP returns 200 with text)
            content_type = response.headers.get("content-type", "")
            if response.status_code == 200 and "application/json" not in content_type:
                text = response.text
                if "subscription" in text.lower() or "premium" in text.lower():
                    raise DataNotAvailableError("Data requires premium FMP subscription")
                if "not found" in text.lower():
                    raise TickerNotFoundError("Ticker not found")
            
            # Handle HTTP errors
            if response.status_code >= 400:
                error_detail = None
                try:
                    body = response.json()
                    if isinstance(body, dict):
                        error_detail = body.get("error") or body.get("message")
                except Exception:
                    error_detail = response.text[:200] if response.text else None
                
                if response.status_code == 401:
                    raise ProviderError("Invalid FMP API key")
                elif response.status_code == 402:
                    if error_detail and ("subscription" in error_detail.lower() or "premium" in error_detail.lower()):
                        raise DataNotAvailableError("Data requires premium FMP subscription")
                    raise RateLimitError("FMP daily API limit reached")
                elif response.status_code == 403:
                    raise ProviderError("FMP access denied")
                elif response.status_code == 404:
                    raise TickerNotFoundError("Ticker not found")
                elif response.status_code == 429:
                    raise RateLimitError("FMP rate limit exceeded")
                else:
                    raise ProviderError(error_detail or f"FMP API error ({response.status_code})")
            
            return response.json()
    
    async def get_stock_data(self, symbol: str) -> StockData:
        """Fetch and normalize stock data from FMP."""
        symbol = symbol.upper()
        
        # Get profile first to validate ticker exists
        profile_data = await self._request("/profile", symbol=symbol)
        if not profile_data:
            raise TickerNotFoundError(f"Ticker '{symbol}' not found")
        
        profile_raw = profile_data[0] if isinstance(profile_data, list) else profile_data
        
        # Fetch financial statements
        income_stmt = await self._request("/income-statement", symbol=symbol, limit=5)
        balance_sheet = await self._request("/balance-sheet-statement", symbol=symbol, limit=5)
        cash_flow = await self._request("/cash-flow-statement", symbol=symbol, limit=5)
        
        # Build standardized profile
        profile = CompanyProfile(
            symbol=symbol,
            name=profile_raw.get("companyName", symbol),
            price=profile_raw.get("price"),
            market_cap=profile_raw.get("marketCap"),
            beta=profile_raw.get("beta"),
            shares_outstanding=profile_raw.get("sharesOutstanding") or (
                profile_raw.get("marketCap", 0) / profile_raw.get("price", 1) 
                if profile_raw.get("price") else None
            ),
            currency=profile_raw.get("currency", "USD"),
            exchange=profile_raw.get("exchange"),
            industry=profile_raw.get("industry"),
            sector=profile_raw.get("sector"),
        )
        
        # Build standardized financials (merge income, balance, cash flow by date)
        financials = self._merge_financials(income_stmt, balance_sheet, cash_flow)
        
        return StockData(
            profile=profile,
            financials=financials,
            provider=self.name,
        )
    
    def _merge_financials(
        self, 
        income: List[dict], 
        balance: List[dict], 
        cash_flow: List[dict]
    ) -> List[FinancialStatement]:
        """Merge financial statements by date into standardized format."""
        # Index by date for merging
        balance_by_date = {b.get("date"): b for b in balance}
        cash_by_date = {c.get("date"): c for c in cash_flow}
        
        financials = []
        for inc in income:
            date = inc.get("date")
            bal = balance_by_date.get(date, {})
            cf = cash_by_date.get(date, {})
            
            stmt = FinancialStatement(
                date=date,
                period="annual" if inc.get("period") == "FY" else "quarterly",
                # Income Statement
                revenue=inc.get("revenue"),
                cost_of_revenue=inc.get("costOfRevenue"),
                gross_profit=inc.get("grossProfit"),
                operating_income=inc.get("operatingIncome"),
                net_income=inc.get("netIncome"),
                interest_expense=inc.get("interestExpense"),
                income_tax_expense=inc.get("incomeTaxExpense"),
                # Share counts
                weighted_avg_shares=inc.get("weightedAverageShsOut"),
                weighted_avg_shares_diluted=inc.get("weightedAverageShsOutDil"),
                # Balance Sheet
                total_assets=bal.get("totalAssets"),
                total_liabilities=bal.get("totalLiabilities"),
                total_equity=bal.get("totalStockholdersEquity"),
                total_debt=bal.get("totalDebt"),
                cash_and_equivalents=bal.get("cashAndCashEquivalents"),
                current_assets=bal.get("totalCurrentAssets"),
                current_liabilities=bal.get("totalCurrentLiabilities"),
                short_term_debt=bal.get("shortTermDebt"),
                goodwill=bal.get("goodwill"),
                intangible_assets=bal.get("intangibleAssets"),
                retained_earnings=bal.get("retainedEarnings"),
                # Cash Flow
                operating_cash_flow=cf.get("operatingCashFlow"),
                capital_expenditure=cf.get("capitalExpenditure"),
                free_cash_flow=cf.get("freeCashFlow"),
                depreciation_amortization=cf.get("depreciationAndAmortization"),
                dividends_paid=cf.get("commonDividendsPaid") or cf.get("netDividendsPaid"),
                stock_based_compensation=cf.get("stockBasedCompensation"),
            )
            financials.append(stmt)
        
        return financials
    
    async def get_treasury_rate(self) -> float:
        """Fetch current 10-year treasury rate."""
        try:
            result = await self._request("/treasury", from_="2024-01-01")
            if result and len(result) > 0:
                rate = result[0].get("year10", 4.5)
                return rate / 100
        except Exception as e:
            logger.warning(f"Failed to fetch treasury rate from FMP: {e}")
        return DEFAULT_TREASURY_RATE
    
    @property
    def supports_fundamentals(self) -> bool:
        return True
    
    @property
    def supports_technical(self) -> bool:
        return True
    
    async def get_historical_prices(self, symbol: str, days: int = 365) -> HistoricalPrices:
        """Fetch historical OHLCV data from FMP."""
        symbol = symbol.upper()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # FMP historical price endpoint
        result = await self._request(
            f"/historical-price-eod/full",
            symbol=symbol,
            from_=start_date.strftime("%Y-%m-%d"),
            to=end_date.strftime("%Y-%m-%d"),
        )
        
        if not result:
            raise DataNotAvailableError(f"No historical data for {symbol}")
        
        # FMP returns data in reverse chronological order
        prices = result if isinstance(result, list) else result.get("historical", [])
        
        bars = []
        for p in reversed(prices):  # Reverse to get oldest first
            bars.append(PriceBar(
                timestamp=p.get("date"),
                open=round(p.get("open", 0), 2),
                high=round(p.get("high", 0), 2),
                low=round(p.get("low", 0), 2),
                close=round(p.get("close", 0), 2),
                volume=int(p.get("volume", 0)),
            ))
        
        if not bars:
            raise DataNotAvailableError(f"No historical data for {symbol}")
        
        return HistoricalPrices(
            symbol=symbol,
            bars=bars,
            provider=self.name,
        )


