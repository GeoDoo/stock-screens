import asyncio
import httpx
from typing import Any, List, Optional

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
    TransientProviderError,
)

from app.constants import DEFAULT_TREASURY_RATE
from app.services.logging_config import logger # Use structlog logger
from app.services.resilience import retry_on_api_error


class FMPProvider(StockDataProvider):
    """Financial Modeling Prep data provider."""
    
    name = "fmp"
    BASE_URL = "https://financialmodelingprep.com/stable"
    
    def __init__(self, api_key: str, client: Optional[httpx.AsyncClient] = None):
        """
        Initialize FMPProvider.
        
        Args:
            api_key: FMP API key
            client: Optional shared httpx.AsyncClient for connection pooling.
                    If provided, reuses TCP/TLS connections saving ~100ms per call.
                    If None, creates a new client per request (backward compat).
        """
        self.api_key = api_key
        self._client = client  # NOTES2.md IV.1: Connection pooling
    
    @retry_on_api_error(retries=3, exceptions=(httpx.HTTPError, TransientProviderError))
    async def _request(self, endpoint: str, **params) -> Any:
        params["apikey"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        
        logger.debug("api_request_start", provider="fmp", endpoint=endpoint)
        
        # NOTES2.md IV.1: Use shared client if available, else create per-request
        if self._client is not None:
            response = await self._client.get(url, params=params)
            return self._process_response(response, endpoint)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                # Process response INSIDE context to avoid accessing closed connection
                return self._process_response(response, endpoint)
    
    def _process_response(self, response: httpx.Response, endpoint: str) -> Any:
        """
        Process HTTP response: check for errors and parse JSON.
        
        Must be called while the client connection is still open
        (inside async with block for per-request clients).
        """
        logger.debug("api_response_received", provider="fmp", endpoint=endpoint, status_code=response.status_code)
        
        # Check for subscription/premium-only responses (FMP returns 200 with text)
        content_type = response.headers.get("content-type", "")
        if response.status_code == 200 and "application/json" not in content_type:
            text = response.text
            if "subscription" in text.lower() or "premium" in text.lower():
                logger.error("api_premium_required", provider="fmp", endpoint=endpoint)
                raise DataNotAvailableError("Data requires premium FMP subscription")
            if "not found" in text.lower():
                logger.warning("api_ticker_not_found", provider="fmp", endpoint=endpoint)
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
            
            logger.error("api_error", provider="fmp", endpoint=endpoint, status_code=response.status_code, error=error_detail)
            
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
            if response.status_code == 429:
                # Note: We don't await rate_limiter here as this is a sync helper.
                # The RateLimitError will be caught by the caller who can then format it.
                raise RateLimitError(f"Rate limit exceeded for {self.name}.")
            elif response.status_code >= 500:
                raise TransientProviderError(error_detail or f"FMP server error ({response.status_code})")
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
        
        # P1.4 Performance: Fetch all financial statements in parallel
        # This reduces latency from ~1.2s (3 sequential requests) to ~300ms
        income_stmt, balance_sheet, cash_flow = await asyncio.gather(
            self._request("/income-statement", symbol=symbol, limit=5),
            self._request("/balance-sheet-statement", symbol=symbol, limit=5),
            self._request("/cash-flow-statement", symbol=symbol, limit=5),
        )
        
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
        
        # P0 Fix: "Quarterly Trap" - Reconstruct TTM if not available
        # If FMP doesn't return TTM and we have quarterly data, reconstruct it
        # to avoid using 3-month revenue as "Latest Revenue" (catastrophic)
        if not self._has_ttm(financials):
            ttm_stmt = self._reconstruct_ttm_from_quarterly(financials)
            if ttm_stmt:
                # Insert TTM at the beginning (most recent)
                financials.insert(0, ttm_stmt)
        
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
            
            # Map FMP period to standardized period
            # FMP typically returns: "FY" (fiscal year), "Q1-Q4" (quarterly)
            # We handle TTM/LTM explicitly for future-proofing
            raw_period = (inc.get("period") or "").upper()
            if raw_period == "FY":
                period = "annual"
            elif raw_period in ("TTM", "LTM"):
                period = "ttm"  # Preserve TTM semantics
            else:
                period = "quarterly"
            
            stmt = FinancialStatement(
                date=date,
                period=period,
                # Income Statement
                revenue=inc.get("revenue"),
                cost_of_revenue=inc.get("costOfRevenue"),
                gross_profit=inc.get("grossProfit"),
                gross_profit_ratio=inc.get("grossProfitRatio"),
                operating_income=inc.get("operatingIncome"),
                net_income=inc.get("netIncome"),
                interest_expense=inc.get("interestExpense"),
                income_tax_expense=inc.get("incomeTaxExpense"),
                selling_general_admin=inc.get("sellingGeneralAndAdministrativeExpenses"),
                research_development=inc.get("researchAndDevelopmentExpenses"),
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
                net_receivables=bal.get("netReceivables"),
                property_plant_equipment=bal.get("propertyPlantEquipmentNet"),
                inventory=bal.get("inventory"),
                accounts_payable=bal.get("accountPayables"),
                # Equity Bridge components
                minority_interest=bal.get("minorityInterest"),
                preferred_stock=bal.get("preferredStock"),
                deferred_tax_assets=bal.get("deferredTaxAssetsNonCurrent"),
                pension_liability=bal.get("pensionLiabilities"),
                # Cash Flow
                operating_cash_flow=cf.get("operatingCashFlow"),
                capital_expenditure=cf.get("capitalExpenditure"),
                free_cash_flow=cf.get("freeCashFlow"),
                depreciation_amortization=cf.get("depreciationAndAmortization"),
                dividends_paid=cf.get("commonDividendsPaid") or cf.get("netDividendsPaid"),
                stock_based_compensation=cf.get("stockBasedCompensation"),
                share_repurchases=cf.get("commonStockRepurchased") or cf.get("purchaseOfCommonStock"),
            )
            financials.append(stmt)
        
        return financials
    
    def _has_ttm(self, financials: List[FinancialStatement]) -> bool:
        """Check if there's already a TTM statement in the list."""
        return any(f.period == "ttm" for f in financials)
    
    def _reconstruct_ttm_from_quarterly(
        self, 
        financials: List[FinancialStatement]
    ) -> Optional[FinancialStatement]:
        """
        Reconstruct TTM (Trailing Twelve Months) from quarterly data.
        
        P0 Fix: The "Quarterly Trap" - if FMP doesn't return TTM data and
        a company just filed a 10-Q, we might use 3-month revenue as
        "Latest Revenue" (catastrophic data integrity issue).
        
        Solution:
        - Income/Cash flow items: Sum last 4 quarters
        - Balance sheet items: Use most recent quarter
        
        Returns None if we don't have at least 4 quarterly statements.
        """
        # Get quarterly statements only
        quarterly = [f for f in financials if f.period == "quarterly"]
        
        if len(quarterly) < 4:
            return None
        
        # Sort by date descending (most recent first)
        quarterly_sorted = sorted(quarterly, key=lambda f: f.date or "", reverse=True)
        
        # Take the 4 most recent quarters
        last_4_quarters = quarterly_sorted[:4]
        
        # Most recent quarter for balance sheet items
        latest_quarter = quarterly_sorted[0]
        
        # Helper to sum a field across 4 quarters
        def sum_field(field_name: str) -> Optional[float]:
            values = []
            for q in last_4_quarters:
                val = getattr(q, field_name, None)
                if val is not None:
                    values.append(val)
            if len(values) == 4:
                return sum(values)
            return None
        
        # Helper to get latest quarter value
        def latest_field(field_name: str) -> Optional[float]:
            return getattr(latest_quarter, field_name, None)
        
        rev = sum_field("revenue")
        gp = sum_field("gross_profit")

        # Construct TTM statement
        return FinancialStatement(
            date="TTM",
            period="ttm",
            # Income Statement - SUM 4 quarters
            revenue=rev,
            cost_of_revenue=sum_field("cost_of_revenue"),
            gross_profit=gp,
            gross_profit_ratio=(gp / rev) if gp is not None and rev else None,
            operating_income=sum_field("operating_income"),
            net_income=sum_field("net_income"),
            interest_expense=sum_field("interest_expense"),
            income_tax_expense=sum_field("income_tax_expense"),
            selling_general_admin=sum_field("selling_general_admin"),
            research_development=sum_field("research_development"),
            # Share counts - use latest (not summed)
            weighted_avg_shares=latest_field("weighted_avg_shares"),
            weighted_avg_shares_diluted=latest_field("weighted_avg_shares_diluted"),
            # Balance Sheet - LATEST quarter
            total_assets=latest_field("total_assets"),
            total_liabilities=latest_field("total_liabilities"),
            total_equity=latest_field("total_equity"),
            total_debt=latest_field("total_debt"),
            cash_and_equivalents=latest_field("cash_and_equivalents"),
            current_assets=latest_field("current_assets"),
            current_liabilities=latest_field("current_liabilities"),
            short_term_debt=latest_field("short_term_debt"),
            goodwill=latest_field("goodwill"),
            intangible_assets=latest_field("intangible_assets"),
            retained_earnings=latest_field("retained_earnings"),
            net_receivables=latest_field("net_receivables"),
            property_plant_equipment=latest_field("property_plant_equipment"),
            inventory=latest_field("inventory"),
            accounts_payable=latest_field("accounts_payable"),
            # Equity Bridge components - LATEST quarter
            minority_interest=latest_field("minority_interest"),
            preferred_stock=latest_field("preferred_stock"),
            deferred_tax_assets=latest_field("deferred_tax_assets"),
            pension_liability=latest_field("pension_liability"),
            # Cash Flow - SUM 4 quarters
            operating_cash_flow=sum_field("operating_cash_flow"),
            capital_expenditure=sum_field("capital_expenditure"),
            free_cash_flow=sum_field("free_cash_flow"),
            depreciation_amortization=sum_field("depreciation_amortization"),
            dividends_paid=sum_field("dividends_paid"),
            stock_based_compensation=sum_field("stock_based_compensation"),
            share_repurchases=sum_field("share_repurchases"),
        )
    
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
    
    async def get_stock_peers(self, symbol: str) -> List[str]:
        """
        Get list of peer company symbols for a stock using FMP's /stock-peers.
        
        NOTES2.md: Dynamic peer discovery based on SIC/NAICS codes.
        This helps avoid survivorship bias in hardcoded peer lists.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            List of peer ticker symbols, or empty list if unavailable
        """
        try:
            result = await self._request("/stock_peers", symbol=symbol)
            if not result:
                return []
            
            # Handle both response formats:
            # 1. Array: [{"symbol": "AAPL", "peersList": ["MSFT", "GOOGL"]}]
            # 2. Object: {"symbol": "AAPL", "peersList": ["MSFT", "GOOGL"]}
            if isinstance(result, list) and len(result) > 0:
                # Array format - get first element's peersList
                return result[0].get("peersList", [])
            elif isinstance(result, dict):
                # Object format - get peersList directly
                return result.get("peersList", [])
            
        except Exception as e:
            logger.warning(f"Failed to fetch peers for {symbol}: {e}")
        return []


