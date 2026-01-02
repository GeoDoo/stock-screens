"""Application configuration with security defaults."""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with secure defaults."""

    # App
    app_name: str = "Stock Screener"
    debug: bool = False

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./stock_screener.db",
        description="Database connection string",
    )

    # Data refresh settings
    refresh_interval_hours: int = Field(
        default=24, ge=1, le=168, description="Hours between scheduled data refreshes"
    )

    # SEC EDGAR settings
    sec_user_agent: str = Field(
        default="StockScreener/1.0 (Personal Use)",
        description="User agent for SEC EDGAR API (required by SEC)",
    )
    sec_rate_limit_seconds: float = Field(
        default=0.1, ge=0.1, description="Minimum seconds between SEC API calls"
    )

    # Paths
    base_dir: Path = Path(__file__).parent.parent

    # Security
    max_symbols_per_request: int = Field(
        default=100, ge=1, le=500, description="Maximum symbols allowed per API request"
    )
    max_filter_conditions: int = Field(
        default=20, ge=1, le=50, description="Maximum filter conditions per screen"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()



