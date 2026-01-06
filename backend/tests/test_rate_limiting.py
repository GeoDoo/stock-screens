"""Tests for accurate rate limiting with time-based windows."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app.services.rate_limiter import (
    RateLimiter, 
    PROVIDER_CONFIGS, 
    ResetSchedule,
    CallRecord,
)


class TestCallRecord:
    """Tests for the CallRecord class."""
    
    def test_add_call_records_timestamp(self):
        """Adding a call should record a timestamp."""
        record = CallRecord()
        record.add_call()
        assert len(record.timestamps) == 1
    
    def test_get_count_since_filters_by_time(self):
        """Should only count calls after the given time."""
        record = CallRecord()
        now = datetime.now(timezone.utc)
        
        # Add old call
        old_time = now - timedelta(hours=2)
        record.add_call(old_time)
        
        # Add recent call
        record.add_call(now)
        
        # Count since 1 hour ago should only get the recent one
        since = now - timedelta(hours=1)
        assert record.get_count_since(since) == 1
    
    def test_cleanup_old_removes_old_timestamps(self):
        """Cleanup should remove timestamps before cutoff."""
        record = CallRecord()
        now = datetime.now(timezone.utc)
        
        # Add old and new calls
        record.add_call(now - timedelta(hours=25))  # Too old
        record.add_call(now - timedelta(hours=23))  # Within 24h
        record.add_call(now)  # Now
        
        # Cleanup anything older than 24 hours
        cutoff = now - timedelta(hours=24)
        record.cleanup_old(cutoff)
        
        assert len(record.timestamps) == 2


class TestRateLimiter:
    """Tests for the RateLimiter service."""
    
    def test_initial_count_is_zero(self):
        """New rate limiter should have zero calls."""
        limiter = RateLimiter()
        assert limiter.get_count("fmp") == 0
        assert limiter.get_count("yahoo") == 0
    
    def test_record_call_increases_count(self):
        """Recording a call should increase the count."""
        limiter = RateLimiter()
        limiter.record_call("fmp")
        assert limiter.get_count("fmp") == 1
        
        limiter.record_call("fmp")
        limiter.record_call("fmp")
        assert limiter.get_count("fmp") == 3
    
    def test_different_providers_tracked_separately(self):
        """Each provider should have its own counter."""
        limiter = RateLimiter()
        limiter.record_call("fmp")
        limiter.record_call("fmp")
        limiter.record_call("yahoo")
        
        assert limiter.get_count("fmp") == 2
        assert limiter.get_count("yahoo") == 1
    
    def test_reset_clears_count(self):
        """Reset should clear the count for a provider."""
        limiter = RateLimiter()
        limiter.record_call("fmp")
        limiter.record_call("fmp")
        limiter.reset("fmp")
        
        assert limiter.get_count("fmp") == 0
    
    def test_reset_all_clears_all_counts(self):
        """Reset all should clear all provider counts."""
        limiter = RateLimiter()
        limiter.record_call("fmp")
        limiter.record_call("yahoo")
        limiter.reset_all()
        
        assert limiter.get_count("fmp") == 0
        assert limiter.get_count("yahoo") == 0
    
    def test_is_approaching_limit(self):
        """Should detect when approaching the limit (80%)."""
        limiter = RateLimiter()
        
        # FMP: 250/day, warn at 200 (80%)
        for _ in range(200):
            limiter.record_call("fmp")
        
        assert limiter.is_approaching_limit("fmp") == True
    
    def test_not_approaching_limit_when_low(self):
        """Should not warn when usage is low."""
        limiter = RateLimiter()
        
        for _ in range(50):
            limiter.record_call("fmp")
        
        assert limiter.is_approaching_limit("fmp") == False
    
    def test_is_at_limit(self):
        """Should detect when at the limit."""
        limiter = RateLimiter()
        
        # FMP: 250/day
        for _ in range(250):
            limiter.record_call("fmp")
        
        assert limiter.is_at_limit("fmp") == True
    
    def test_get_remaining(self):
        """Should return remaining calls."""
        limiter = RateLimiter()
        
        for _ in range(100):
            limiter.record_call("fmp")
        
        assert limiter.get_remaining("fmp") == 150  # 250 - 100
    
    def test_get_usage_stats(self):
        """Should return comprehensive usage statistics."""
        limiter = RateLimiter()
        
        for _ in range(100):
            limiter.record_call("fmp")
        
        stats = limiter.get_usage_stats("fmp")
        assert stats["provider"] == "fmp"
        assert stats["used"] == 100
        assert stats["limit"] == 250
        assert stats["remaining"] == 150
        assert stats["percentage"] == 40.0
        assert stats["reset_schedule"] == "daily"
        assert stats["api_limited"] == False
    
    def test_mark_api_limited(self):
        """Marking as API-limited should affect remaining and is_at_limit."""
        limiter = RateLimiter()
        
        # Record only 10 calls (well under limit)
        for _ in range(10):
            limiter.record_call("fmp")
        
        # But API returned 429, so we're actually limited
        limiter.mark_api_limited("fmp")
        
        assert limiter.is_at_limit("fmp") == True
        assert limiter.get_remaining("fmp") == 0
        assert limiter.get_usage_stats("fmp")["api_limited"] == True
    
    def test_clear_api_limited(self):
        """Clearing API-limited flag should restore normal behavior."""
        limiter = RateLimiter()
        limiter.mark_api_limited("fmp")
        assert limiter.is_at_limit("fmp") == True
        
        limiter.clear_api_limited("fmp")
        assert limiter.is_at_limit("fmp") == False
    
    def test_daily_reset_window(self):
        """Daily limit providers should reset at midnight UTC."""
        limiter = RateLimiter()
        
        # Mock time to be 11:59 PM UTC
        yesterday = datetime.now(timezone.utc).replace(hour=23, minute=59) - timedelta(days=1)
        
        # Add a call "yesterday"
        record = limiter._get_record("fmp")
        record.add_call(yesterday)
        
        # Count should be 0 (call was before today's window)
        assert limiter.get_count("fmp") == 0
    
    def test_minute_window_for_massive(self):
        """Massive/Polygon should use per-minute rolling window."""
        limiter = RateLimiter()
        
        # Add a call 2 minutes ago
        record = limiter._get_record("massive")
        old_call = datetime.now(timezone.utc) - timedelta(minutes=2)
        record.add_call(old_call)
        
        # Count should be 0 (call was outside 1-minute window)
        assert limiter.get_count("massive") == 0
    
    def test_case_insensitive_provider_names(self):
        """Provider names should be case-insensitive."""
        limiter = RateLimiter()
        
        limiter.record_call("FMP")
        limiter.record_call("fmp")
        limiter.record_call("Fmp")
        
        assert limiter.get_count("fmp") == 3
        assert limiter.get_count("FMP") == 3


class TestProviderConfigs:
    """Tests for provider configuration."""
    
    def test_fmp_config(self):
        """FMP should be 250/day."""
        config = PROVIDER_CONFIGS["fmp"]
        assert config.limit == 250
        assert config.reset_schedule == ResetSchedule.DAILY
    
    def test_yahoo_config(self):
        """Yahoo should be 2000/day."""
        config = PROVIDER_CONFIGS["yahoo"]
        assert config.limit == 2000
        assert config.reset_schedule == ResetSchedule.DAILY
    
    def test_massive_config(self):
        """Massive should be 5/minute."""
        config = PROVIDER_CONFIGS["massive"]
        assert config.limit == 5
        assert config.reset_schedule == ResetSchedule.PER_MINUTE
