"""
Shared constants for the stock-screens backend.
Single source of truth for magic numbers and configuration values.
"""

# Default risk-free rate when treasury API fails (4.5%)
# Used as fallback by all providers
DEFAULT_TREASURY_RATE = 0.045

# Default tax rate when company data is missing
DEFAULT_TAX_RATE = 0.25

# Rate limit warning threshold (warn at 80% usage)
RATE_LIMIT_WARNING_THRESHOLD = 0.8

