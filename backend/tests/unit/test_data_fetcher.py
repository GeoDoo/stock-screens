"""
Unit tests for data fetcher service.

TDD: Writing tests first.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.services.data_fetcher import DataFetcherService


class TestDataFetcher:
    """Tests for Yahoo Finance data fetching."""

    @pytest.mark.asyncio
    async def test_fetch_stock_basic_info(self):
        """
        Test fetching basic stock info.
        """
        service = DataFetcherService()
        
        # Mock yfinance Ticker
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "symbol": "AAPL",
            "shortName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "currentPrice": 150.0,
            "trailingPE": 25.0,
            "priceToBook": 35.0,
            "trailingEps": 6.0,
        }
        
        with patch("app.services.data_fetcher.yf.Ticker", return_value=mock_ticker):
            result = await service.fetch_stock("AAPL")
        
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.name == "Apple Inc."

    @pytest.mark.asyncio
    async def test_fetch_stock_returns_none_for_invalid_symbol(self):
        """
        Should return None for invalid/unknown symbols.
        """
        service = DataFetcherService()
        
        mock_ticker = MagicMock()
        mock_ticker.info = {}  # Empty info = invalid symbol
        
        with patch("app.services.data_fetcher.yf.Ticker", return_value=mock_ticker):
            result = await service.fetch_stock("INVALID")
        
        assert result is None

