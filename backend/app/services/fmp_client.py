import httpx
from typing import Any


class FMPClientError(Exception):
    """Custom exception for FMP API errors."""
    pass


class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/stable"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _request(self, endpoint: str, **params) -> Any:
        async with httpx.AsyncClient() as client:
            params["apikey"] = self.api_key
            response = await client.get(f"{self.BASE_URL}{endpoint}", params=params)
            
            # Handle common HTTP errors with clean messages
            if response.status_code == 401:
                raise FMPClientError("Invalid API key")
            elif response.status_code == 402:
                raise FMPClientError("API limit reached or invalid subscription")
            elif response.status_code == 403:
                raise FMPClientError("Access denied - check your API subscription")
            elif response.status_code == 404:
                raise FMPClientError("Data not found")
            elif response.status_code >= 400:
                raise FMPClientError(f"API error (status {response.status_code})")
            
            return response.json()

    async def get_profile(self, symbol: str) -> dict:
        result = await self._request("/profile", symbol=symbol)
        return result[0] if result else {}

    async def get_income_statement(self, symbol: str, limit: int = 5) -> list:
        return await self._request("/income-statement", symbol=symbol, limit=limit)

    async def get_balance_sheet(self, symbol: str, limit: int = 5) -> list:
        return await self._request("/balance-sheet-statement", symbol=symbol, limit=limit)

    async def get_cash_flow(self, symbol: str, limit: int = 5) -> list:
        return await self._request("/cash-flow-statement", symbol=symbol, limit=limit)

    async def get_treasury_rate(self) -> float:
        """
        Fetch current 10-year treasury rate (risk-free rate).
        Returns rate as decimal (e.g., 0.045 for 4.5%).
        """
        try:
            result = await self._request("/treasury", from_="2024-01-01")
            if result and len(result) > 0:
                rate = result[0].get("year10", 4.5)
                return rate / 100
        except Exception:
            pass
        return 0.045  # Default fallback

    async def get_stock_data(self, symbol: str) -> dict:
        """Fetch all data needed for DCF valuation."""
        profile = await self.get_profile(symbol)
        
        # If profile is empty, the ticker doesn't exist
        if not profile:
            raise FMPClientError(f"Ticker '{symbol}' not found")
        
        return {
            "profile": profile,
            "income_statement": await self.get_income_statement(symbol),
            "balance_sheet": await self.get_balance_sheet(symbol),
            "cash_flow": await self.get_cash_flow(symbol),
        }
