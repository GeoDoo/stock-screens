"""Tests for rate limiting and request optimization."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.rate_limiter import RateLimiter, ProviderLimits


class TestRateLimiter:
    """Tests for the RateLimiter service."""
    
    def test_initial_count_is_zero(self):
        """New rate limiter should have zero calls."""
        limiter = RateLimiter()
        assert limiter.get_count("fmp") == 0
        assert limiter.get_count("yahoo") == 0
    
    def test_increment_increases_count(self):
        """Incrementing should increase the call count."""
        limiter = RateLimiter()
        limiter.increment("fmp")
        assert limiter.get_count("fmp") == 1
        
        limiter.increment("fmp")
        limiter.increment("fmp")
        assert limiter.get_count("fmp") == 3
    
    def test_different_providers_tracked_separately(self):
        """Each provider should have its own counter."""
        limiter = RateLimiter()
        limiter.increment("fmp")
        limiter.increment("fmp")
        limiter.increment("yahoo")
        
        assert limiter.get_count("fmp") == 2
        assert limiter.get_count("yahoo") == 1
    
    def test_reset_clears_count(self):
        """Reset should clear the count for a provider."""
        limiter = RateLimiter()
        limiter.increment("fmp")
        limiter.increment("fmp")
        limiter.reset("fmp")
        
        assert limiter.get_count("fmp") == 0
    
    def test_reset_all_clears_all_counts(self):
        """Reset all should clear all provider counts."""
        limiter = RateLimiter()
        limiter.increment("fmp")
        limiter.increment("yahoo")
        limiter.reset_all()
        
        assert limiter.get_count("fmp") == 0
        assert limiter.get_count("yahoo") == 0
    
    def test_is_approaching_limit(self):
        """Should detect when approaching the limit."""
        limiter = RateLimiter()
        
        # FMP free tier: 250/day, warn at 80%
        for _ in range(200):
            limiter.increment("fmp")
        
        assert limiter.is_approaching_limit("fmp") == True
        
    def test_not_approaching_limit_when_low(self):
        """Should not warn when usage is low."""
        limiter = RateLimiter()
        
        for _ in range(50):
            limiter.increment("fmp")
        
        assert limiter.is_approaching_limit("fmp") == False
    
    def test_is_at_limit(self):
        """Should detect when at the limit."""
        limiter = RateLimiter()
        
        # FMP free tier: 250/day
        for _ in range(250):
            limiter.increment("fmp")
        
        assert limiter.is_at_limit("fmp") == True
    
    def test_get_remaining(self):
        """Should return remaining calls."""
        limiter = RateLimiter()
        
        for _ in range(100):
            limiter.increment("fmp")
        
        assert limiter.get_remaining("fmp") == 150  # 250 - 100
    
    def test_get_usage_stats(self):
        """Should return usage statistics."""
        limiter = RateLimiter()
        
        for _ in range(100):
            limiter.increment("fmp")
        
        stats = limiter.get_usage_stats("fmp")
        assert stats["used"] == 100
        assert stats["limit"] == 250
        assert stats["remaining"] == 150
        assert stats["percentage"] == 40.0


class TestProviderLimits:
    """Tests for provider limit configuration."""
    
    def test_fmp_limits(self):
        """FMP should have correct limits."""
        assert ProviderLimits.FMP == 250
    
    def test_yahoo_limits(self):
        """Yahoo should have higher limits (more lenient)."""
        assert ProviderLimits.YAHOO == 2000
    
    def test_massive_limits(self):
        """Massive should have its limits."""
        assert ProviderLimits.MASSIVE == 5  # Free tier is very limited

