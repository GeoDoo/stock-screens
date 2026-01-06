import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.stock_data_client import StockDataClient
from app.services.base_provider import (
    StockData, CompanyProfile, FinancialStatement,
    StockDataProvider, ProviderError, TickerNotFoundError,
    DataNotAvailableError, RateLimitError,
)


def create_mock_stock_data(symbol: str, provider: str) -> StockData:
    """Helper to create mock StockData."""
    return StockData(
        profile=CompanyProfile(
            symbol=symbol, name=f"{symbol} Corp", price=100.0,
            market_cap=1000000000, beta=1.0, shares_outstanding=10000000,
            currency="USD",
        ),
        financials=[],
        provider=provider,
    )


class TestStockDataClient:
    @pytest.fixture
    def mock_provider_success(self):
        """Mock provider that returns data successfully."""
        provider = MagicMock(spec=StockDataProvider)
        provider.name = "mock_success"
        provider.get_stock_data = AsyncMock(return_value=create_mock_stock_data("TEST", "mock"))
        provider.get_treasury_rate = AsyncMock(return_value=0.045)
        return provider

    @pytest.fixture
    def mock_provider_not_found(self):
        """Mock provider that raises TickerNotFoundError."""
        provider = MagicMock(spec=StockDataProvider)
        provider.name = "mock_not_found"
        provider.get_stock_data = AsyncMock(side_effect=TickerNotFoundError("Not found"))
        return provider

    @pytest.fixture
    def mock_provider_rate_limited(self):
        """Mock provider that raises RateLimitError."""
        provider = MagicMock(spec=StockDataProvider)
        provider.name = "mock_rate_limited"
        provider.get_stock_data = AsyncMock(side_effect=RateLimitError("Rate limit"))
        return provider

    @pytest.fixture
    def mock_provider_error(self):
        """Mock provider that raises generic ProviderError."""
        provider = MagicMock(spec=StockDataProvider)
        provider.name = "mock_error"
        provider.get_stock_data = AsyncMock(side_effect=ProviderError("Some error"))
        return provider

    @pytest.mark.asyncio
    async def test_returns_data_from_first_provider(self, mock_provider_success):
        """Should return data from the first successful provider."""
        client = StockDataClient(providers=[mock_provider_success])
        
        result = await client.get_stock_data("TEST")
        
        assert result.profile.symbol == "TEST"
        mock_provider_success.get_stock_data.assert_called_once_with("TEST")

    @pytest.mark.asyncio
    async def test_falls_back_on_not_found(self, mock_provider_not_found, mock_provider_success):
        """Should try next provider when first returns TickerNotFoundError."""
        client = StockDataClient(providers=[mock_provider_not_found, mock_provider_success])
        
        result = await client.get_stock_data("TEST")
        
        assert result.profile.symbol == "TEST"
        mock_provider_not_found.get_stock_data.assert_called_once()
        mock_provider_success.get_stock_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_on_rate_limit(self, mock_provider_rate_limited, mock_provider_success):
        """Should try next provider when first is rate limited."""
        client = StockDataClient(providers=[mock_provider_rate_limited, mock_provider_success])
        
        result = await client.get_stock_data("TEST")
        
        assert result.profile.symbol == "TEST"

    @pytest.mark.asyncio
    async def test_falls_back_on_provider_error(self, mock_provider_error, mock_provider_success):
        """Should try next provider on generic error."""
        client = StockDataClient(providers=[mock_provider_error, mock_provider_success])
        
        result = await client.get_stock_data("TEST")
        
        assert result.profile.symbol == "TEST"

    @pytest.mark.asyncio
    async def test_raises_ticker_not_found_when_all_fail(self, mock_provider_not_found):
        """Should raise TickerNotFoundError when all providers say not found."""
        provider2 = MagicMock(spec=StockDataProvider)
        provider2.name = "mock_not_found_2"
        provider2.get_stock_data = AsyncMock(side_effect=TickerNotFoundError("Not found"))
        
        client = StockDataClient(providers=[mock_provider_not_found, provider2])
        
        with pytest.raises(TickerNotFoundError):
            await client.get_stock_data("INVALID")

    @pytest.mark.asyncio
    async def test_raises_rate_limit_when_all_rate_limited(self, mock_provider_rate_limited):
        """Should raise RateLimitError when all providers are rate limited."""
        provider2 = MagicMock(spec=StockDataProvider)
        provider2.name = "mock_rate_limited_2"
        provider2.get_stock_data = AsyncMock(side_effect=RateLimitError("Rate limit"))
        
        client = StockDataClient(providers=[mock_provider_rate_limited, provider2])
        
        with pytest.raises(RateLimitError):
            await client.get_stock_data("TEST")

    @pytest.mark.asyncio
    async def test_raises_provider_error_when_all_fail_mixed(
        self, mock_provider_error, mock_provider_rate_limited
    ):
        """Should raise ProviderError with details when mixed failures."""
        client = StockDataClient(providers=[mock_provider_error, mock_provider_rate_limited])
        
        with pytest.raises(ProviderError) as exc_info:
            await client.get_stock_data("TEST")
        
        # Error message should mention both providers
        assert "mock_error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_single_provider_clearer_error(self, mock_provider_rate_limited):
        """Single provider failures should have clearer error messages."""
        client = StockDataClient(providers=[mock_provider_rate_limited])
        
        with pytest.raises(RateLimitError) as exc_info:
            await client.get_stock_data("TEST")
        
        assert "mock_rate_limited" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_treasury_rate_success(self, mock_provider_success):
        """Should return treasury rate from provider."""
        client = StockDataClient(providers=[mock_provider_success])
        
        rate = await client.get_treasury_rate()
        
        assert rate == 0.045

    @pytest.mark.asyncio
    async def test_get_treasury_rate_fallback(self):
        """Should return default rate when all providers fail."""
        provider = MagicMock(spec=StockDataProvider)
        provider.get_treasury_rate = AsyncMock(side_effect=Exception("Failed"))
        
        client = StockDataClient(providers=[provider])
        
        rate = await client.get_treasury_rate()
        
        assert rate == 0.045  # Default fallback

    def test_provider_names(self, mock_provider_success, mock_provider_error):
        """Should list provider names."""
        client = StockDataClient(providers=[mock_provider_success, mock_provider_error])
        
        names = client.provider_names
        
        assert "mock_success" in names
        assert "mock_error" in names

    @pytest.mark.asyncio
    async def test_symbol_uppercased(self, mock_provider_success):
        """Symbol should be uppercased before query."""
        client = StockDataClient(providers=[mock_provider_success])
        
        await client.get_stock_data("aapl")
        
        mock_provider_success.get_stock_data.assert_called_with("AAPL")

