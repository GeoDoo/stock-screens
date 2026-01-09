"""
In-memory cache with TTL for stock data.

Provides simple caching to reduce external API calls. Stock data changes
infrequently during market hours (fundamental data even less so), so
caching for 5 minutes is safe and dramatically reduces API usage.

Usage:
    cache = StockDataCache(default_ttl=300)  # 5 minute default
    cache.set("AAPL", stock_data)
    data = cache.get("AAPL")  # Returns None if expired
"""
import time
from typing import Any, Dict, Optional
from collections import OrderedDict


class StockDataCache:
    """
    Simple in-memory cache with TTL and size limits.
    
    Features:
    - TTL (time-to-live) expiration
    - Max size with LRU eviction
    - Case-insensitive symbol keys
    - Hit/miss statistics
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 100):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (default 5 minutes)
            max_size: Maximum number of entries (default 100)
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0
    
    def _normalize_key(self, key: str) -> str:
        """Normalize key to uppercase for case-insensitive lookups."""
        return key.upper()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key (case-insensitive)
            
        Returns:
            Cached value or None if not found/expired
        """
        key = self._normalize_key(key)
        
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        
        # Check expiration
        if time.time() > entry["expires_at"]:
            # Entry expired, remove it
            del self._cache[key]
            self._misses += 1
            return None
        
        # Move to end for true LRU behavior (mark as recently used)
        self._cache.move_to_end(key)
        
        self._hits += 1
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache with TTL.
        
        Args:
            key: Cache key (case-insensitive)
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        key = self._normalize_key(key)
        ttl = ttl if ttl is not None else self.default_ttl
        
        # If key exists, remove it first (to update position in OrderedDict)
        if key in self._cache:
            del self._cache[key]
        
        # Evict oldest entries if at max size
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # Remove oldest
        
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
        }
    
    def invalidate(self, key: str) -> None:
        """
        Remove specific entry from cache.
        
        Args:
            key: Cache key to invalidate
        """
        key = self._normalize_key(key)
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Remove all entries from cache."""
        self._cache.clear()
    
    def stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hits, misses, and current size
        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
        }


# Global cache instance for stock data (5 minute TTL, 100 entries max)
stock_cache = StockDataCache(default_ttl=300, max_size=100)
