"""
Accurate rate limiting service to track API calls per provider.

Each provider has different limits and reset schedules:
- FMP: 250 calls/day (resets at midnight UTC)
- Yahoo: ~2000 calls/day (resets at midnight UTC)
- Massive/Polygon: 5 calls/minute (rolling window)
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from enum import Enum


class ResetSchedule(Enum):
    """When the rate limit resets."""
    DAILY = "daily"        # Resets at midnight UTC
    PER_MINUTE = "minute"  # Rolling 1-minute window


@dataclass
class ProviderConfig:
    """Configuration for a provider's rate limits."""
    limit: int
    reset_schedule: ResetSchedule
    

# Provider configurations
PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {
    "fmp": ProviderConfig(limit=250, reset_schedule=ResetSchedule.DAILY),
    "yahoo": ProviderConfig(limit=2000, reset_schedule=ResetSchedule.DAILY),
    "massive": ProviderConfig(limit=5, reset_schedule=ResetSchedule.PER_MINUTE),
}


# Warning threshold (percentage of limit)
WARNING_THRESHOLD = 0.8  # Warn at 80%


@dataclass
class CallRecord:
    """Record of API calls with timestamps for accurate tracking."""
    timestamps: List[datetime] = field(default_factory=list)
    
    def add_call(self, timestamp: datetime = None):
        """Record a new API call."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        self.timestamps.append(timestamp)
    
    def get_count_since(self, since: datetime) -> int:
        """Get number of calls since a given time."""
        return sum(1 for ts in self.timestamps if ts >= since)
    
    def cleanup_old(self, before: datetime):
        """Remove timestamps older than a given time to save memory."""
        self.timestamps = [ts for ts in self.timestamps if ts >= before]


@dataclass
class ApiLimitedRecord:
    """Track when a provider was marked as rate-limited."""
    limited_at: datetime
    reset_schedule: ResetSchedule
    
    def should_auto_clear(self) -> bool:
        """Check if enough time has passed to try again."""
        now = datetime.now(timezone.utc)
        
        if self.reset_schedule == ResetSchedule.DAILY:
            # Clear at next midnight UTC
            # If limited before midnight and now it's past midnight, clear
            today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return self.limited_at < today_midnight
        
        elif self.reset_schedule == ResetSchedule.PER_MINUTE:
            # Clear after 60 seconds
            return (now - self.limited_at).total_seconds() >= 60
        
        return False
    
    def time_until_reset(self) -> timedelta:
        """Get time remaining until the limit resets."""
        now = datetime.now(timezone.utc)
        
        if self.reset_schedule == ResetSchedule.DAILY:
            # Next midnight UTC
            tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return tomorrow - now
        
        elif self.reset_schedule == ResetSchedule.PER_MINUTE:
            # 60 seconds from when limited
            reset_time = self.limited_at + timedelta(seconds=60)
            remaining = reset_time - now
            return remaining if remaining.total_seconds() > 0 else timedelta(seconds=0)
        
        return timedelta(seconds=0)


class RateLimiter:
    """
    Accurately tracks API calls per provider with proper reset logic.
    Auto-clears api_limited flag when the reset window passes.
    
    Usage:
        limiter = RateLimiter()
        limiter.record_call("fmp")
        stats = limiter.get_usage_stats("fmp")
        if limiter.is_at_limit("fmp"):
            # Block request or show error
    """
    
    def __init__(self):
        self._records: Dict[str, CallRecord] = {}
        # Track when provider hit actual API rate limit (with timestamp for auto-clear)
        self._api_limited: Dict[str, ApiLimitedRecord] = {}
    
    def _get_record(self, provider: str) -> CallRecord:
        """Get or create call record for provider."""
        provider = provider.lower()
        if provider not in self._records:
            self._records[provider] = CallRecord()
        return self._records[provider]
    
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
        """
        Record an API call for a provider.
        Returns the current count in this window.
        """
        provider = provider.lower()
        record = self._get_record(provider)
        record.add_call()
        
        # Cleanup old timestamps to save memory (keep last 24 hours)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        record.cleanup_old(cutoff)
        
        return self.get_count(provider)
    
    def get_count(self, provider: str) -> int:
        """Get current call count in the active window."""
        provider = provider.lower()
        record = self._get_record(provider)
        window_start = self._get_window_start(provider)
        return record.get_count_since(window_start)
    
    def _is_api_limited(self, provider: str) -> bool:
        """Check if provider is API-limited, with auto-clear logic."""
        provider = provider.lower()
        record = self._api_limited.get(provider)
        
        if record is None:
            return False
        
        # Auto-clear if enough time has passed
        if record.should_auto_clear():
            del self._api_limited[provider]
            return False
        
        return True
    
    def get_remaining(self, provider: str) -> int:
        """Get remaining calls in the current window."""
        # If API told us we're limited (and not auto-cleared), return 0
        if self._is_api_limited(provider):
            return 0
        
        config = self._get_config(provider)
        count = self.get_count(provider)
        return max(0, config.limit - count)
    
    def is_approaching_limit(self, provider: str) -> bool:
        """Check if usage is approaching the limit (>80%)."""
        config = self._get_config(provider)
        count = self.get_count(provider)
        return count >= (config.limit * WARNING_THRESHOLD)
    
    def is_at_limit(self, provider: str) -> bool:
        """Check if at or over the limit."""
        # If API told us we're limited (and not auto-cleared), we're at limit
        if self._is_api_limited(provider):
            return True
        
        config = self._get_config(provider)
        count = self.get_count(provider)
        return count >= config.limit
    
    def mark_api_limited(self, provider: str):
        """
        Mark provider as rate-limited based on actual API error.
        This is the source of truth when API returns 429.
        Records timestamp for auto-clear logic.
        """
        provider = provider.lower()
        config = self._get_config(provider)
        self._api_limited[provider] = ApiLimitedRecord(
            limited_at=datetime.now(timezone.utc),
            reset_schedule=config.reset_schedule
        )
    
    def clear_api_limited(self, provider: str):
        """Clear the API-limited flag (e.g., manual override)."""
        provider = provider.lower()
        if provider in self._api_limited:
            del self._api_limited[provider]
    
    def get_time_until_reset(self, provider: str) -> Optional[int]:
        """Get seconds until rate limit resets (None if not limited)."""
        provider = provider.lower()
        record = self._api_limited.get(provider)
        if record is None:
            return None
        remaining = record.time_until_reset()
        return int(remaining.total_seconds())
    
    def get_usage_stats(self, provider: str) -> Dict:
        """Get accurate usage statistics for a provider."""
        provider = provider.lower()
        config = self._get_config(provider)
        count = self.get_count(provider)
        remaining = self.get_remaining(provider)
        api_limited = self._is_api_limited(provider)
        reset_in = self.get_time_until_reset(provider)
        
        return {
            "provider": provider,
            "used": count,
            "limit": config.limit,
            "remaining": remaining,
            "percentage": round((count / config.limit) * 100, 1) if config.limit > 0 else 0,
            "reset_schedule": config.reset_schedule.value,
            "api_limited": api_limited,  # True if provider returned 429 (auto-clears)
            "reset_in_seconds": reset_in,  # Seconds until can try again (None if not limited)
        }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get usage statistics for all providers."""
        return {p: self.get_usage_stats(p) for p in PROVIDER_CONFIGS.keys()}
    
    def reset(self, provider: str) -> None:
        """Manually reset a provider's count (for testing or admin)."""
        provider = provider.lower()
        self._records[provider] = CallRecord()
        if provider in self._api_limited:
            del self._api_limited[provider]
    
    def reset_all(self) -> None:
        """Reset all provider counts."""
        self._records.clear()
        self._api_limited.clear()


# Global instance for the application
rate_limiter = RateLimiter()
