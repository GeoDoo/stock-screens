from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CompanyProfile:
    """Standardized company profile data."""
    symbol: str
    name: str
    price: Optional[float] = None
    market_cap: Optional[float] = None
    beta: Optional[float] = None
    shares_outstanding: Optional[float] = None
    currency: str = "USD"
    exchange: Optional[str] = None
    industry: Optional[str] = None
    sector: Optional[str] = None


@dataclass
class FinancialStatement:
    """Standardized financial statement data for one period."""
    date: str
    period: str  # "annual" or "quarterly"
    
    # Income Statement
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None  # EBIT
    net_income: Optional[float] = None
    interest_expense: Optional[float] = None
    income_tax_expense: Optional[float] = None
    selling_general_admin: Optional[float] = None  # SG&A for Beneish M-Score
    
    # Share counts (from income statement)
    weighted_avg_shares: Optional[float] = None  # Basic shares
    weighted_avg_shares_diluted: Optional[float] = None  # FDSO - required for DCF
    
    # Balance Sheet
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    total_debt: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    short_term_debt: Optional[float] = None  # For Non-Cash Working Capital
    goodwill: Optional[float] = None  # For ROTIC calculation
    intangible_assets: Optional[float] = None  # For ROTIC calculation
    retained_earnings: Optional[float] = None  # For Altman Z-Score
    net_receivables: Optional[float] = None  # For Beneish M-Score
    property_plant_equipment: Optional[float] = None  # For Beneish M-Score
    # Equity Bridge components
    minority_interest: Optional[float] = None  # Non-controlling interest
    preferred_stock: Optional[float] = None  # Preferred equity
    deferred_tax_assets: Optional[float] = None  # NOLs/tax shields
    pension_liability: Optional[float] = None  # Underfunded pension obligations
    
    # Cash Flow
    operating_cash_flow: Optional[float] = None
    capital_expenditure: Optional[float] = None
    free_cash_flow: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    dividends_paid: Optional[float] = None
    stock_based_compensation: Optional[float] = None  # For SBC-adjusted FCF


@dataclass
class ValuationRatios:
    """Valuation ratios for comparable analysis."""
    pe_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_book: Optional[float] = None
    ev_to_revenue: Optional[float] = None


@dataclass 
class StockData:
    """Complete stock data from a provider."""
    profile: CompanyProfile
    financials: List[FinancialStatement]
    provider: str  # Which provider supplied this data


@dataclass
class PriceBar:
    """Single OHLCV price bar for technical analysis."""
    timestamp: str  # ISO format date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class HistoricalPrices:
    """Historical price data from a provider."""
    symbol: str
    bars: List[PriceBar]
    provider: str


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class TickerNotFoundError(ProviderError):
    """Raised when a ticker symbol doesn't exist."""
    pass


class DataNotAvailableError(ProviderError):
    """Raised when data exists but isn't accessible (e.g., premium required)."""
    pass


class RateLimitError(ProviderError):
    """Raised when API rate limit is exceeded."""
    pass


class StockDataProvider(ABC):
    """Abstract base class for stock data providers."""
    
    name: str = "base"
    
    @abstractmethod
    async def get_stock_data(self, symbol: str) -> StockData:
        """
        Fetch complete stock data for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            StockData with profile and financial statements
            
        Raises:
            TickerNotFoundError: If symbol doesn't exist
            DataNotAvailableError: If data requires premium access
            RateLimitError: If rate limit exceeded
            ProviderError: For other provider-specific errors
        """
        pass
    
    @abstractmethod
    async def get_treasury_rate(self) -> float:
        """
        Fetch current risk-free rate (10-year treasury).
        
        Returns:
            Rate as decimal (e.g., 0.045 for 4.5%)
        """
        pass
    
    async def get_historical_prices(self, symbol: str, days: int = 365) -> HistoricalPrices:
        """
        Fetch historical OHLCV price data for technical analysis.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days of history
            
        Returns:
            HistoricalPrices with list of PriceBars
            
        Raises:
            NotImplementedError: If provider doesn't support historical prices
        """
        raise NotImplementedError(f"{self.name} does not support historical prices")
    
    @property
    def supports_fundamentals(self) -> bool:
        """Whether this provider supports fundamental analysis."""
        return True
    
    @property
    def supports_technical(self) -> bool:
        """Whether this provider supports technical analysis (historical prices)."""
        return False


