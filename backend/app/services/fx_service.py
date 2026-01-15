import httpx
import structlog
from typing import Dict, List, Optional
from app.services.logging_config import logger

class FXService:
    """
    Service for fetching and managing exchange rates.
    Normalizes all amounts to a base currency (default USD).
    """
    
    # Fallback rates (as of Jan 2026) - units of currency per 1 USD
    FALLBACK_RATES = {
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.78,
        "JPY": 145.0,
        "CAD": 1.35,
        "AUD": 1.50,
        "CHF": 0.86,
        "CNY": 7.15,
        "HKD": 7.80,
        "INR": 83.0,
    }

    def __init__(self):
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self._cache = {}

    async def get_rates(self, currencies: List[str]) -> Dict[str, float]:
        """
        Get exchange rates for a list of currencies vs USD.
        Returns a dict mapping currency code to rate (units per 1 USD).
        """
        currencies = [c.upper() for c in currencies]
        unique_currencies = set(currencies)
        unique_currencies.add("USD")
        
        try:
            live_rates = await self._fetch_live_rates(list(unique_currencies))
            if live_rates:
                return {**self.FALLBACK_RATES, **live_rates}
        except Exception as e:
            logger.warning("fx_live_fetch_failed", error=str(e))
            
        return self.FALLBACK_RATES

    async def _fetch_live_rates(self, currencies: List[str]) -> Dict[str, float]:
        """
        Fetch live rates from FMP API.
        This is a placeholder for actual API call.
        """
        # In a real scenario, we would use the API key and httpx
        # For now, we'll just return None to trigger fallback in tests 
        # unless it's patched.
        return None

    async def convert(self, amount: float, from_currency: str, to_currency: str = "USD") -> float:
        """
        Convert an amount from one currency to another.
        """
        if from_currency == to_currency:
            return amount
            
        rates = await self.get_rates([from_currency, to_currency])
        
        # Rate is units per 1 USD
        # value_usd = amount / rate_from
        # value_to = value_usd * rate_to
        
        rate_from = rates.get(from_currency.upper(), self.FALLBACK_RATES.get(from_currency.upper(), 1.0))
        rate_to = rates.get(to_currency.upper(), self.FALLBACK_RATES.get(to_currency.upper(), 1.0))
        
        value_usd = amount / rate_from
        return value_usd * rate_to
