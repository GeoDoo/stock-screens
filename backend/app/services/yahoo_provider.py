import asyncio
from typing import List
import yfinance as yf

from app.services.base_provider import (
    StockDataProvider,
    StockData,
    CompanyProfile,
    FinancialStatement,
    ProviderError,
    TickerNotFoundError,
    DataNotAvailableError,
    HistoricalPrices,
    PriceBar,
)


class YahooProvider(StockDataProvider):
    """Yahoo Finance data provider using yfinance library."""
    
    name = "yahoo"
    
    def __init__(self):
        pass  # No API key needed
    
    async def get_stock_data(self, symbol: str) -> StockData:
        """Fetch and normalize stock data from Yahoo Finance."""
        symbol = symbol.upper()
        
        # yfinance is synchronous, run in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync, symbol)
    
    def _fetch_sync(self, symbol: str) -> StockData:
        """Synchronous fetch implementation."""
        ticker = yf.Ticker(symbol)
        
        # Get basic info
        try:
            info = ticker.info
        except Exception as e:
            raise ProviderError(f"Yahoo Finance error: {str(e)}")
        
        # Check if ticker is valid
        if not info or info.get("regularMarketPrice") is None:
            # Try to check if it's a delisted or invalid symbol
            if info.get("symbol") is None:
                raise TickerNotFoundError(f"Ticker '{symbol}' not found")
            raise DataNotAvailableError(f"No price data available for '{symbol}'")
        
        # Build profile
        profile = CompanyProfile(
            symbol=symbol,
            name=info.get("longName") or info.get("shortName") or symbol,
            price=info.get("regularMarketPrice") or info.get("currentPrice"),
            market_cap=info.get("marketCap"),
            beta=info.get("beta"),
            shares_outstanding=info.get("sharesOutstanding"),
            currency=info.get("currency", "USD"),
            exchange=info.get("exchange"),
            industry=info.get("industry"),
            sector=info.get("sector"),
        )
        
        # Fetch financial statements
        financials = self._get_financials(ticker)
        
        return StockData(
            profile=profile,
            financials=financials,
            provider=self.name,
        )
    
    def _get_financials(self, ticker: yf.Ticker) -> List[FinancialStatement]:
        """Extract and normalize financial statements."""
        financials = []
        
        try:
            # Get annual financials (yfinance returns DataFrames)
            income_df = ticker.financials  # Annual income statement
            balance_df = ticker.balance_sheet  # Annual balance sheet
            cash_df = ticker.cashflow  # Annual cash flow
            
            if income_df is None or income_df.empty:
                return financials
            
            # Columns are dates, rows are metrics
            for date_col in income_df.columns:
                date_str = date_col.strftime("%Y-%m-%d") if hasattr(date_col, "strftime") else str(date_col)
                
                # Helper to safely get value from DataFrame
                def get_val(df, *keys):
                    if df is None or df.empty:
                        return None
                    for key in keys:
                        if key in df.index and date_col in df.columns:
                            val = df.loc[key, date_col]
                            if val is not None and not (isinstance(val, float) and val != val):  # Check for NaN
                                return float(val)
                    return None
                
                stmt = FinancialStatement(
                    date=date_str,
                    period="annual",
                    # Income Statement
                    revenue=get_val(income_df, "Total Revenue", "Operating Revenue"),
                    cost_of_revenue=get_val(income_df, "Cost Of Revenue"),
                    gross_profit=get_val(income_df, "Gross Profit"),
                    operating_income=get_val(income_df, "Operating Income", "EBIT"),
                    net_income=get_val(income_df, "Net Income", "Net Income Common Stockholders"),
                    interest_expense=get_val(income_df, "Interest Expense"),
                    income_tax_expense=get_val(income_df, "Tax Provision", "Income Tax Expense"),
                    # Balance Sheet
                    total_assets=get_val(balance_df, "Total Assets"),
                    total_liabilities=get_val(balance_df, "Total Liabilities Net Minority Interest", "Total Liabilities"),
                    total_equity=get_val(balance_df, "Total Equity Gross Minority Interest", "Stockholders Equity"),
                    total_debt=get_val(balance_df, "Total Debt"),
                    cash_and_equivalents=get_val(balance_df, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"),
                    current_assets=get_val(balance_df, "Current Assets"),
                    current_liabilities=get_val(balance_df, "Current Liabilities"),
                    # Cash Flow
                    operating_cash_flow=get_val(cash_df, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities"),
                    capital_expenditure=get_val(cash_df, "Capital Expenditure"),
                    free_cash_flow=get_val(cash_df, "Free Cash Flow"),
                    depreciation_amortization=get_val(cash_df, "Depreciation And Amortization"),
                    dividends_paid=get_val(cash_df, "Cash Dividends Paid", "Common Stock Dividend Paid"),
                )
                financials.append(stmt)
                
        except Exception as e:
            # If financials fail, return empty list (profile still valid)
            pass
        
        return financials
    
    async def get_treasury_rate(self) -> float:
        """
        Fetch current 10-year treasury rate.
        Yahoo Finance has ^TNX for 10-year treasury yield.
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._get_treasury_sync)
        except Exception:
            return 0.045  # Default fallback
    
    def _get_treasury_sync(self) -> float:
        """Synchronous treasury rate fetch."""
        ticker = yf.Ticker("^TNX")
        info = ticker.info
        # ^TNX price is the yield in percentage points (e.g., 4.5 for 4.5%)
        rate = info.get("regularMarketPrice") or info.get("previousClose") or 4.5
        return rate / 100  # Convert to decimal
    
    @property
    def supports_fundamentals(self) -> bool:
        return True
    
    @property
    def supports_technical(self) -> bool:
        return True
    
    async def get_historical_prices(self, symbol: str, days: int = 365) -> HistoricalPrices:
        """Fetch historical OHLCV data from Yahoo Finance."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_history_sync, symbol, days)
    
    def _get_history_sync(self, symbol: str, days: int) -> HistoricalPrices:
        """Synchronous history fetch."""
        ticker = yf.Ticker(symbol.upper())
        
        # Fetch history
        period = f"{days}d" if days <= 365 else f"{days // 365}y"
        hist = ticker.history(period=period)
        
        if hist.empty:
            raise DataNotAvailableError(f"No historical data for {symbol}")
        
        bars = []
        for date, row in hist.iterrows():
            bars.append(PriceBar(
                timestamp=date.strftime("%Y-%m-%d"),
                open=round(row["Open"], 2),
                high=round(row["High"], 2),
                low=round(row["Low"], 2),
                close=round(row["Close"], 2),
                volume=int(row["Volume"]),
            ))
        
        return HistoricalPrices(
            symbol=symbol.upper(),
            bars=bars,
            provider=self.name,
        )


