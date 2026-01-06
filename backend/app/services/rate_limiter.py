"""Rate limiting service to track API calls per provider."""
from dataclasses import dataclass
from typing import Dict
from enum import IntEnum


class ProviderLimits(IntEnum):
    """Daily API call limits per provider (free tier)."""
    FMP = 250       # FMP free tier: 250/day
    YAHOO = 2000    # Yahoo is more lenient
    MASSIVE = 5     # Polygon free tier: 5 calls/minute (very limited)


# Warning threshold (percentage of limit)
WARNING_THRESHOLD = 0.8  # Warn at 80%


class RateLimiter:
    """
    Tracks API calls per provider and warns when approaching limits.
    
    Usage:
        limiter = RateLimiter()
        limiter.increment("fmp")
        if limiter.is_approaching_limit("fmp"):
            # Show warning to user
        if limiter.is_at_limit("fmp"):
            # Block request or show error
    """
    
    def __init__(self):
        self._counts: Dict[str, int] = {}
    
    def get_count(self, provider: str) -> int:
        """Get current call count for a provider."""
        return self._counts.get(provider.lower(), 0)
    
    def increment(self, provider: str) -> int:
        """Increment call count for a provider. Returns new count."""
        provider = provider.lower()
        self._counts[provider] = self._counts.get(provider, 0) + 1
        return self._counts[provider]
    
    def reset(self, provider: str) -> None:
        """Reset call count for a provider."""
        provider = provider.lower()
        self._counts[provider] = 0
    
    def reset_all(self) -> None:
        """Reset all provider counts."""
        self._counts.clear()
    
    def _get_limit(self, provider: str) -> int:
        """Get the limit for a provider."""
        provider = provider.lower()
        limits = {
            "fmp": ProviderLimits.FMP,
            "yahoo": ProviderLimits.YAHOO,
            "massive": ProviderLimits.MASSIVE,
        }
        return limits.get(provider, 100)  # Default to 100 for unknown
    
    def is_approaching_limit(self, provider: str) -> bool:
        """Check if usage is approaching the limit (>80%)."""
        count = self.get_count(provider)
        limit = self._get_limit(provider)
        return count >= (limit * WARNING_THRESHOLD)
    
    def is_at_limit(self, provider: str) -> bool:
        """Check if at or over the limit."""
        count = self.get_count(provider)
        limit = self._get_limit(provider)
        return count >= limit
    
    def get_remaining(self, provider: str) -> int:
        """Get remaining calls for a provider."""
        count = self.get_count(provider)
        limit = self._get_limit(provider)
        return max(0, limit - count)
    
    def get_usage_stats(self, provider: str) -> Dict:
        """Get usage statistics for a provider."""
        count = self.get_count(provider)
        limit = self._get_limit(provider)
        return {
            "used": count,
            "limit": limit,
            "remaining": max(0, limit - count),
            "percentage": round((count / limit) * 100, 1) if limit > 0 else 0,
        }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get usage statistics for all tracked providers."""
        providers = ["fmp", "yahoo", "massive"]
        return {p: self.get_usage_stats(p) for p in providers}


# Global instance for the application
rate_limiter = RateLimiter()

