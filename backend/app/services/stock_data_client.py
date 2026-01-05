from typing import List, Optional
import logging

from app.services.base_provider import (
    StockDataProvider,
    StockData,
    ProviderError,
    TickerNotFoundError,
    DataNotAvailableError,
    RateLimitError,
)
from app.services.fmp_provider import FMPProvider
from app.services.yahoo_provider import YahooProvider

logger = logging.getLogger(__name__)


class StockDataClient:
    """
    Smart stock data client with automatic fallback between providers.
    
    Tries providers in order until one succeeds. Handles different error types:
    - TickerNotFoundError: Tries next provider (might exist on another source)
    - DataNotAvailableError: Tries next provider (premium data on one, free on another)
    - RateLimitError: Tries next provider
    - Other ProviderError: Tries next provider
    """
    
    def __init__(
        self,
        fmp_api_key: Optional[str] = None,
        providers: Optional[List[StockDataProvider]] = None,
    ):
        """
        Initialize with providers.
        
        Args:
            fmp_api_key: API key for FMP (if using default providers)
            providers: Custom list of providers (overrides default)
        """
        if providers:
            self.providers = providers
        else:
            # Default provider chain: FMP first (better data), Yahoo as fallback
            self.providers = []
            if fmp_api_key:
                self.providers.append(FMPProvider(fmp_api_key))
            self.providers.append(YahooProvider())
    
    async def get_stock_data(self, symbol: str) -> StockData:
        """
        Fetch stock data, trying providers in order until one succeeds.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            StockData from the first successful provider
            
        Raises:
            TickerNotFoundError: If no provider has this ticker
            ProviderError: If all providers fail
        """
        symbol = symbol.upper()
        errors = []
        
        for provider in self.providers:
            try:
                logger.info(f"Trying {provider.name} for {symbol}")
                data = await provider.get_stock_data(symbol)
                logger.info(f"Success: {symbol} from {provider.name}")
                return data
            
            except TickerNotFoundError as e:
                logger.debug(f"{provider.name}: {symbol} not found, trying next")
                errors.append((provider.name, e))
                continue
                
            except DataNotAvailableError as e:
                logger.debug(f"{provider.name}: {symbol} data not available, trying next")
                errors.append((provider.name, e))
                continue
                
            except RateLimitError as e:
                logger.warning(f"{provider.name}: rate limited, trying next")
                errors.append((provider.name, e))
                continue
                
            except ProviderError as e:
                logger.warning(f"{provider.name}: error for {symbol}: {e}")
                errors.append((provider.name, e))
                continue
                
            except Exception as e:
                logger.error(f"{provider.name}: unexpected error for {symbol}: {e}")
                errors.append((provider.name, ProviderError(str(e))))
                continue
        
        # All providers failed
        if all(isinstance(e, TickerNotFoundError) for _, e in errors):
            raise TickerNotFoundError(f"Ticker '{symbol}' not found on any provider")
        
        # Build detailed error message
        error_details = "; ".join(f"{name}: {e}" for name, e in errors)
        raise ProviderError(f"All providers failed for {symbol}: {error_details}")
    
    async def get_treasury_rate(self) -> float:
        """
        Fetch treasury rate from first available provider.
        Falls back to default if all fail.
        """
        for provider in self.providers:
            try:
                return await provider.get_treasury_rate()
            except Exception:
                continue
        
        return 0.045  # Default fallback
    
    @property
    def provider_names(self) -> List[str]:
        """List of configured provider names."""
        return [p.name for p in self.providers]

