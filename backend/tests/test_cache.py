"""
Tests for the caching service.

The cache should:
- Store stock data with TTL (time-to-live)
- Return cached data if not expired
- Return None if expired or not found
- Support manual invalidation
"""
import pytest
import time
from unittest.mock import patch

from app.services.cache import StockDataCache


class TestStockDataCache:
    """Tests for the stock data caching service."""
    
    def test_cache_stores_and_retrieves_data(self):
        """Basic get/set functionality."""
        cache = StockDataCache(default_ttl=300)
        
        data = {"symbol": "AAPL", "price": 150.0}
        cache.set("AAPL", data)
        
        result = cache.get("AAPL")
        assert result == data
    
    def test_cache_returns_none_for_missing_key(self):
        """get() returns None for keys that were never set."""
        cache = StockDataCache(default_ttl=300)
        
        result = cache.get("UNKNOWN")
        assert result is None
    
    def test_cache_expires_after_ttl(self):
        """Data should expire after TTL seconds."""
        cache = StockDataCache(default_ttl=1)  # 1 second TTL
        
        data = {"symbol": "AAPL", "price": 150.0}
        cache.set("AAPL", data)
        
        # Should exist immediately
        assert cache.get("AAPL") == data
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert cache.get("AAPL") is None
    
    def test_cache_custom_ttl_per_entry(self):
        """Individual entries can have custom TTL."""
        cache = StockDataCache(default_ttl=300)
        
        data = {"symbol": "AAPL", "price": 150.0}
        cache.set("AAPL", data, ttl=1)  # Custom 1 second TTL
        
        assert cache.get("AAPL") == data
        
        time.sleep(1.1)
        assert cache.get("AAPL") is None
    
    def test_cache_invalidate_removes_entry(self):
        """invalidate() removes specific entry."""
        cache = StockDataCache(default_ttl=300)
        
        cache.set("AAPL", {"price": 150})
        cache.set("MSFT", {"price": 400})
        
        cache.invalidate("AAPL")
        
        assert cache.get("AAPL") is None
        assert cache.get("MSFT") == {"price": 400}
    
    def test_cache_clear_removes_all_entries(self):
        """clear() removes all entries."""
        cache = StockDataCache(default_ttl=300)
        
        cache.set("AAPL", {"price": 150})
        cache.set("MSFT", {"price": 400})
        
        cache.clear()
        
        assert cache.get("AAPL") is None
        assert cache.get("MSFT") is None
    
    def test_cache_normalizes_symbol_case(self):
        """Symbols should be case-insensitive."""
        cache = StockDataCache(default_ttl=300)
        
        cache.set("aapl", {"price": 150})
        
        assert cache.get("AAPL") == {"price": 150}
        assert cache.get("aapl") == {"price": 150}
        assert cache.get("Aapl") == {"price": 150}
    
    def test_cache_stats(self):
        """Cache should track hit/miss statistics."""
        cache = StockDataCache(default_ttl=300)
        
        cache.set("AAPL", {"price": 150})
        
        cache.get("AAPL")  # Hit
        cache.get("AAPL")  # Hit
        cache.get("MSFT")  # Miss
        
        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
    
    def test_cache_size_limit(self):
        """Cache should respect max size, evicting oldest entries."""
        cache = StockDataCache(default_ttl=300, max_size=2)
        
        cache.set("AAPL", {"price": 150})
        cache.set("MSFT", {"price": 400})
        cache.set("GOOGL", {"price": 140})  # Should evict AAPL
        
        assert cache.get("AAPL") is None  # Evicted
        assert cache.get("MSFT") is not None
        assert cache.get("GOOGL") is not None
    
    def test_cache_lru_eviction_respects_access_order(self):
        """
        LRU eviction should evict least recently USED, not just oldest SET.
        
        Bug: get() must update item order, otherwise it's FIFO not LRU.
        """
        cache = StockDataCache(default_ttl=300, max_size=2)
        
        cache.set("AAPL", {"price": 150})  # Oldest
        cache.set("MSFT", {"price": 400})
        
        # Access AAPL - makes it "recently used"
        cache.get("AAPL")
        
        # Add new entry - should evict MSFT (least recently used), not AAPL
        cache.set("GOOGL", {"price": 140})
        
        assert cache.get("AAPL") is not None, "AAPL was accessed recently, should NOT be evicted"
        assert cache.get("MSFT") is None, "MSFT was least recently used, should be evicted"
        assert cache.get("GOOGL") is not None
