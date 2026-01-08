"""
SQLite-based rate limiter for tracking API calls per provider.

Benefits over file-based JSON:
- ACID compliant
- Handles concurrent access
- Efficient queries for time-based counts
- Auto-cleanup of old records

Each provider has different limits and reset schedules:
- FMP: 250 calls/day (resets at midnight UTC)
- Yahoo: ~2000 calls/day (resets at midnight UTC)
- Massive/Polygon: 5 calls/minute (rolling window)
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from enum import Enum

from app.services.database import get_connection, DEFAULT_DB_PATH


class ResetSchedule(Enum):
    """When the rate limit resets."""
    DAILY = "daily"        # Resets at midnight UTC
    PER_MINUTE = "minute"  # Rolling 1-minute window


class ProviderConfig:
    """Configuration for a provider's rate limits."""
    def __init__(self, limit: int, reset_schedule: ResetSchedule):
        self.limit = limit
        self.reset_schedule = reset_schedule


# Provider configurations
PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {
    "fmp": ProviderConfig(limit=250, reset_schedule=ResetSchedule.DAILY),
    "yahoo": ProviderConfig(limit=2000, reset_schedule=ResetSchedule.DAILY),
    "massive": ProviderConfig(limit=5, reset_schedule=ResetSchedule.PER_MINUTE),
}


class RateLimiterSQLite:
    """
    SQLite-based rate limiter with proper time window handling.
    
    Usage:
        limiter = RateLimiterSQLite()
        limiter.record_call("fmp")
        stats = limiter.get_usage_stats("fmp")
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize with database path."""
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with get_connection(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_provider_timestamp 
                ON api_calls (provider, timestamp)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_limited (
                    provider TEXT PRIMARY KEY,
                    limited_at TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def _get_config(self, provider: str) -> ProviderConfig:
        """Get configuration for a provider."""
        provider = provider.lower()
        return PROVIDER_CONFIGS.get(
            provider,
            ProviderConfig(limit=100, reset_schedule=ResetSchedule.DAILY)
        )
    
    def _get_window_start(self, provider: str) -> datetime:
        """Get the start of the current rate limit window."""
        config = self._get_config(provider)
        now = datetime.now(timezone.utc)
        
        if config.reset_schedule == ResetSchedule.DAILY:
            # Start of today (midnight UTC)
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif config.reset_schedule == ResetSchedule.PER_MINUTE:
            # 1 minute ago (rolling window)
            return now - timedelta(minutes=1)
        else:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def record_call(self, provider: str) -> int:
        """Record an API call. Returns current count in window."""
        provider = provider.lower()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO api_calls (provider, timestamp) VALUES (?, ?)",
                (provider, timestamp)
            )
            conn.commit()
        
        return self.get_count(provider)
    
    def _insert_call(self, provider: str, timestamp: datetime):
        """Insert a call with specific timestamp (for testing)."""
        provider = provider.lower()
        with get_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO api_calls (provider, timestamp) VALUES (?, ?)",
                (provider, timestamp.isoformat())
            )
            conn.commit()
    
    def get_count(self, provider: str) -> int:
        """Get call count in the current window."""
        provider = provider.lower()
        window_start = self._get_window_start(provider)
        
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM api_calls WHERE provider = ? AND timestamp >= ?",
                (provider, window_start.isoformat())
            )
            return cursor.fetchone()[0]
    
    def get_remaining(self, provider: str) -> int:
        """Get remaining calls in the current window."""
        if self.is_api_limited(provider):
            return 0
        
        config = self._get_config(provider)
        count = self.get_count(provider)
        return max(0, config.limit - count)
    
    def is_at_limit(self, provider: str) -> bool:
        """Check if at or over the limit."""
        if self.is_api_limited(provider):
            return True
        
        config = self._get_config(provider)
        count = self.get_count(provider)
        return count >= config.limit
    
    def mark_api_limited(self, provider: str):
        """Mark provider as rate-limited (API returned 429)."""
        provider = provider.lower()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with get_connection(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO api_limited (provider, limited_at) 
                   VALUES (?, ?)""",
                (provider, timestamp)
            )
            conn.commit()
    
    def _update_api_limited_timestamp(self, provider: str, timestamp: datetime):
        """Update api_limited timestamp (for testing)."""
        provider = provider.lower()
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE api_limited SET limited_at = ? WHERE provider = ?",
                (timestamp.isoformat(), provider)
            )
            conn.commit()
    
    def is_api_limited(self, provider: str) -> bool:
        """Check if provider is API-limited, with auto-clear logic."""
        provider = provider.lower()
        
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT limited_at FROM api_limited WHERE provider = ?",
                (provider,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return False
            
            limited_at = datetime.fromisoformat(row[0])
            config = self._get_config(provider)
            now = datetime.now(timezone.utc)
            
            # Check if should auto-clear
            if config.reset_schedule == ResetSchedule.DAILY:
                today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                if limited_at < today_midnight:
                    # Clear it
                    conn.execute("DELETE FROM api_limited WHERE provider = ?", (provider,))
                    conn.commit()
                    return False
            elif config.reset_schedule == ResetSchedule.PER_MINUTE:
                if (now - limited_at).total_seconds() >= 60:
                    conn.execute("DELETE FROM api_limited WHERE provider = ?", (provider,))
                    conn.commit()
                    return False
            
            return True
    
    def get_time_until_reset(self, provider: str) -> Optional[int]:
        """Get seconds until rate limit resets (None if not limited)."""
        provider = provider.lower()
        
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT limited_at FROM api_limited WHERE provider = ?",
                (provider,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            limited_at = datetime.fromisoformat(row[0])
            config = self._get_config(provider)
            now = datetime.now(timezone.utc)
            
            if config.reset_schedule == ResetSchedule.DAILY:
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                return int((tomorrow - now).total_seconds())
            elif config.reset_schedule == ResetSchedule.PER_MINUTE:
                reset_time = limited_at + timedelta(seconds=60)
                remaining = (reset_time - now).total_seconds()
                return int(max(0, remaining))
            
            return None
    
    def get_usage_stats(self, provider: str) -> Dict:
        """Get usage statistics for a provider."""
        provider = provider.lower()
        config = self._get_config(provider)
        count = self.get_count(provider)
        remaining = self.get_remaining(provider)
        api_limited = self.is_api_limited(provider)
        reset_in = self.get_time_until_reset(provider)
        
        return {
            "provider": provider,
            "used": count,
            "limit": config.limit,
            "remaining": remaining,
            "percentage": round((count / config.limit) * 100, 1) if config.limit > 0 else 0,
            "reset_schedule": config.reset_schedule.value,
            "api_limited": api_limited,
            "reset_in_seconds": reset_in,
        }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get usage statistics for all providers."""
        return {p: self.get_usage_stats(p) for p in PROVIDER_CONFIGS.keys()}
    
    def cleanup_old_records(self, hours: int = 24) -> int:
        """Remove records older than specified hours. Returns count deleted."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM api_calls WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )
            conn.commit()
            return cursor.rowcount
    
    def reset(self, provider: str):
        """Reset a provider's counts and api_limited status."""
        provider = provider.lower()
        
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM api_calls WHERE provider = ?", (provider,))
            conn.execute("DELETE FROM api_limited WHERE provider = ?", (provider,))
            conn.commit()
    
    def reset_all(self):
        """Reset all providers."""
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM api_calls")
            conn.execute("DELETE FROM api_limited")
            conn.commit()
    
    def close(self):
        """Close any resources (for cleanup in tests)."""
        pass  # Connections are closed after each operation


# Global instance for the application
rate_limiter = RateLimiterSQLite()
