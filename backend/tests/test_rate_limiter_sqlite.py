"""
Tests for SQLite-based rate limiter.
TDD: Write tests first, then implement.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import tempfile
import os


class TestRateLimiterSQLite:
    """Test SQLite-based rate limiting."""
    
    @pytest.fixture
    def limiter(self):
        """Create a rate limiter with temporary database."""
        from app.services.rate_limiter_sqlite import RateLimiterSQLite
        
        # Use temp file for test isolation
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        limiter = RateLimiterSQLite(db_path=db_path)
        yield limiter
        
        # Cleanup
        limiter.close()
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_record_call_increments_count(self, limiter):
        """Recording a call should increment the count."""
        assert limiter.get_count("fmp") == 0
        
        limiter.record_call("fmp")
        assert limiter.get_count("fmp") == 1
        
        limiter.record_call("fmp")
        assert limiter.get_count("fmp") == 2
    
    def test_counts_are_per_provider(self, limiter):
        """Each provider has its own count."""
        limiter.record_call("fmp")
        limiter.record_call("fmp")
        limiter.record_call("yahoo")
        
        assert limiter.get_count("fmp") == 2
        assert limiter.get_count("yahoo") == 1
        assert limiter.get_count("massive") == 0
    
    def test_daily_limit_resets_at_midnight(self, limiter):
        """Daily provider counts should only include today's calls."""
        # Record a call "yesterday" by inserting directly
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        limiter._insert_call("fmp", yesterday)
        
        # Record a call today
        limiter.record_call("fmp")
        
        # Should only count today's call
        assert limiter.get_count("fmp") == 1
    
    def test_minute_limit_rolling_window(self, limiter):
        """Per-minute provider counts should use 60-second rolling window."""
        # Record a call "2 minutes ago" by inserting directly
        two_min_ago = datetime.now(timezone.utc) - timedelta(minutes=2)
        limiter._insert_call("massive", two_min_ago)
        
        # Record a call now
        limiter.record_call("massive")
        
        # Should only count the recent call
        assert limiter.get_count("massive") == 1
    
    def test_get_remaining_daily(self, limiter):
        """Should return correct remaining calls for daily provider."""
        # FMP has 250 daily limit
        assert limiter.get_remaining("fmp") == 250
        
        limiter.record_call("fmp")
        assert limiter.get_remaining("fmp") == 249
    
    def test_get_remaining_per_minute(self, limiter):
        """Should return correct remaining calls for per-minute provider."""
        # Massive has 5/minute limit
        assert limiter.get_remaining("massive") == 5
        
        limiter.record_call("massive")
        assert limiter.get_remaining("massive") == 4
    
    def test_is_at_limit(self, limiter):
        """Should detect when at limit."""
        assert not limiter.is_at_limit("massive")
        
        # Use up all 5 calls
        for _ in range(5):
            limiter.record_call("massive")
        
        assert limiter.is_at_limit("massive")
    
    def test_mark_api_limited(self, limiter):
        """Should track when API returns 429."""
        assert not limiter.is_api_limited("fmp")
        
        limiter.mark_api_limited("fmp")
        assert limiter.is_api_limited("fmp")
    
    def test_api_limited_auto_clears_daily(self, limiter):
        """Daily api_limited should auto-clear after midnight."""
        # Mark as limited "yesterday"
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        with patch('app.services.rate_limiter_sqlite.datetime') as mock_dt:
            mock_dt.now.return_value = yesterday
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            limiter.mark_api_limited("fmp")
        
        # Today it should be cleared
        assert not limiter.is_api_limited("fmp")
    
    def test_api_limited_auto_clears_per_minute(self, limiter):
        """Per-minute api_limited should auto-clear after 60 seconds."""
        limiter.mark_api_limited("massive")
        assert limiter.is_api_limited("massive")
        
        # Simulate time passing by updating the timestamp
        two_min_ago = datetime.now(timezone.utc) - timedelta(minutes=2)
        limiter._update_api_limited_timestamp("massive", two_min_ago)
        
        # Should be cleared now
        assert not limiter.is_api_limited("massive")
    
    def test_get_usage_stats(self, limiter):
        """Should return complete usage statistics."""
        limiter.record_call("fmp")
        limiter.record_call("fmp")
        
        stats = limiter.get_usage_stats("fmp")
        
        assert stats["provider"] == "fmp"
        assert stats["used"] == 2
        assert stats["limit"] == 250
        assert stats["remaining"] == 248
        assert stats["percentage"] == pytest.approx(0.8, rel=0.1)
        assert stats["reset_schedule"] == "daily"
        assert stats["api_limited"] is False
    
    def test_get_all_stats(self, limiter):
        """Should return stats for all providers."""
        limiter.record_call("fmp")
        limiter.record_call("yahoo")
        
        all_stats = limiter.get_all_stats()
        
        assert "fmp" in all_stats
        assert "yahoo" in all_stats
        assert "massive" in all_stats
        assert all_stats["fmp"]["used"] == 1
        assert all_stats["yahoo"]["used"] == 1
    
    def test_cleanup_old_records(self, limiter):
        """Should remove records older than 24 hours."""
        # Insert old record
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        limiter._insert_call("fmp", old_time)
        
        # Insert recent record
        limiter.record_call("fmp")
        
        # Run cleanup
        deleted = limiter.cleanup_old_records()
        
        assert deleted >= 1
        # Only recent call should remain
        assert limiter.get_count("fmp") == 1
    
    def test_persistence_across_instances(self, limiter):
        """Data should persist when creating new instance."""
        from app.services.rate_limiter_sqlite import RateLimiterSQLite
        
        # Record some calls
        limiter.record_call("fmp")
        limiter.record_call("fmp")
        db_path = limiter.db_path
        
        # Create new instance with same DB
        limiter2 = RateLimiterSQLite(db_path=db_path)
        
        # Should see the same counts
        assert limiter2.get_count("fmp") == 2
        
        limiter2.close()
    
    def test_provider_names_case_insensitive(self, limiter):
        """Provider names should be case insensitive."""
        limiter.record_call("FMP")
        limiter.record_call("fmp")
        limiter.record_call("Fmp")
        
        assert limiter.get_count("fmp") == 3
        assert limiter.get_count("FMP") == 3
    
    def test_reset_provider(self, limiter):
        """Should be able to reset a single provider."""
        limiter.record_call("fmp")
        limiter.record_call("yahoo")
        
        limiter.reset("fmp")
        
        assert limiter.get_count("fmp") == 0
        assert limiter.get_count("yahoo") == 1
    
    def test_reset_all(self, limiter):
        """Should be able to reset all providers."""
        limiter.record_call("fmp")
        limiter.record_call("yahoo")
        limiter.mark_api_limited("fmp")
        
        limiter.reset_all()
        
        assert limiter.get_count("fmp") == 0
        assert limiter.get_count("yahoo") == 0
        assert not limiter.is_api_limited("fmp")
