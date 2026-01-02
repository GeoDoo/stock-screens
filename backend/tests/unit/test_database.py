"""
Unit tests for database repositories.

TDD: Writing tests ONE AT A TIME.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.db.repositories import WatchlistRepository, SpinoffRepository, NoteRepository
from app.models.watchlist import WatchlistItem, Note
from app.models.spinoff import Spinoff, SpinoffAlert, SpinoffStatus


class TestWatchlistRepository:
    """Tests for watchlist persistence."""

    @pytest.mark.asyncio
    async def test_add_to_watchlist(self, test_db):
        """Test adding a stock to watchlist."""
        repo = WatchlistRepository(test_db)
        
        item = WatchlistItem(
            symbol="AAPL",
            target_price=150.0,
        )
        
        result = await repo.add(item)
        
        assert result is not None
        assert result.id is not None
        assert result.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_watchlist(self, test_db):
        """Test retrieving all watchlist items."""
        repo = WatchlistRepository(test_db)
        
        # Add a few items
        await repo.add(WatchlistItem(symbol="AAPL"))
        await repo.add(WatchlistItem(symbol="MSFT"))
        
        result = await repo.get_all()
        
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_remove_from_watchlist(self, test_db):
        """Test removing a stock from watchlist."""
        repo = WatchlistRepository(test_db)
        
        item = await repo.add(WatchlistItem(symbol="TSLA"))
        
        await repo.remove(item.id)
        
        result = await repo.get_by_symbol("TSLA")
        assert result is None

