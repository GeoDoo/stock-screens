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
            
            # Check for subscription/premium-only responses (FMP returns 200 with text message)
            content_type = response.headers.get("content-type", "")
            if response.status_code == 200 and "application/json" not in content_type:
                text = response.text
                if "subscription" in text.lower() or "premium" in text.lower():
                    raise FMPClientError("Financial data not available for this ticker (may require premium subscription)")
                if "not found" in text.lower():
                    raise FMPClientError("Data not found for this ticker")
            
            # Handle HTTP errors with context-aware messages
            if response.status_code >= 400:
                # Try to get error details from response body
                error_detail = None
                try:
                    body = response.json()
                    if isinstance(body, dict):
                        error_detail = body.get("error") or body.get("message")
                except Exception:
                    error_detail = response.text[:200] if response.text else None
                
                # Map status codes to user-friendly messages
                if response.status_code == 401:
                    raise FMPClientError("Invalid API key")
                elif response.status_code == 402:
                    if error_detail and ("subscription" in error_detail.lower() or "premium" in error_detail.lower()):
                        raise FMPClientError("Financial data not available (requires premium subscription)")
                    raise FMPClientError("API limit reached or premium data required")
                elif response.status_code == 403:
                    raise FMPClientError("Access denied - check your API subscription")
                elif response.status_code == 404:
                    raise FMPClientError("Data not found")
                else:
                    raise FMPClientError(error_detail or f"API error (status {response.status_code})")
            
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
