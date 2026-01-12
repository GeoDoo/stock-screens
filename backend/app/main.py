"""
Stock Screens API - Main entry point.

This is a thin wiring layer. Business logic lives in:
- routers/stock.py - Stock data and valuation endpoints
- routers/memos.py - Investment memo endpoints  
- routers/audit.py - Assumption audit trail endpoints
"""
import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env BEFORE any imports that read environment variables
# (routers read API keys at module level)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import stock, memos, audit, filings
from app.schemas.stock import CapitalEfficiencyRequest
from app.services.capital_efficiency import analyze_value_creation
from app.services.rate_limiter_sqlite import rate_limiter
from app.services.fmp_provider import FMPProvider
from app.services.massive_provider import MassiveProvider

app = FastAPI(title="Stock Screens API")

# CORS configuration
# For production, set CORS_ORIGINS env var to comma-separated list of allowed origins
# e.g., CORS_ORIGINS="https://yourapp.com,https://www.yourapp.com"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ORIGINS != ["*"],  # Only allow credentials with explicit origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get API keys from environment
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
MASSIVE_API_KEY = os.getenv("POLYGON_API_KEY", "")  # Polygon is now Massive


def validate_configuration() -> List[Dict[str, Any]]:
    """
    Validate startup configuration and log warnings for issues.
    
    Returns:
        List of warning dictionaries describing configuration issues.
        Each dict has 'type' or 'provider', 'message', and 'severity' keys.
    
    This function:
    - Warns if FMP_API_KEY is missing (provider will be unavailable)
    - Warns if CORS is set to wildcard (security risk in production)
    - Does NOT crash the app - issues are warnings, not errors
    """
    warnings: List[Dict[str, Any]] = []
    
    # Check FMP API key
    fmp_key = os.getenv("FMP_API_KEY", "")
    if not fmp_key:
        msg = "FMP_API_KEY not set - FMP provider will be unavailable"
        logger.warning(msg)
        warnings.append({
            "provider": "fmp",
            "message": msg,
            "severity": "warning",
        })
    
    # Check CORS configuration
    cors_env = os.getenv("CORS_ORIGINS", "")
    if not cors_env:
        msg = (
            "CORS_ORIGINS not set - defaulting to wildcard '*'. "
            "This is acceptable for local development but should be "
            "explicitly configured for production."
        )
        logger.warning(msg)
        warnings.append({
            "type": "cors_wildcard",
            "message": msg,
            "severity": "warning",
        })
    
    # Check Polygon/Massive API key (optional, just info)
    polygon_key = os.getenv("POLYGON_API_KEY", "")
    if not polygon_key:
        logger.info("POLYGON_API_KEY not set - Massive provider will be unavailable")
    
    return warnings


# Run validation on module load (startup)
_startup_warnings = validate_configuration()

# Include routers
app.include_router(stock.router)
app.include_router(memos.router)
app.include_router(audit.router)
app.include_router(filings.router)  # SEC filings with PDF download


# =============================================================================
# Standalone endpoints (kept in main.py as they're simple/standalone)
# =============================================================================

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/providers")
def get_providers():
    """
    Get list of available data providers with their capabilities.
    
    Returns providers for:
    - Fundamental analysis (financials, DCF, comparables)
    - Technical analysis (price charts, indicators)
    
    User picks one provider for each analysis type.
    """
    # Fundamental analysis providers
    fundamental_providers = [
        {
            "id": "yahoo",
            "name": "Yahoo Finance",
            "description": "Free, good coverage",
            "available": True,
            "recommended": False,
        },
        {
            "id": "fmp",
            "name": "FMP",
            "description": "Best quality fundamentals",
            "available": bool(FMP_API_KEY),
            "recommended": True,
        },
    ]
    
    # Technical analysis providers
    technical_providers = [
        {
            "id": "yahoo",
            "name": "Yahoo Finance",
            "description": "Free, good coverage",
            "available": True,
            "recommended": False,
        },
        {
            "id": "fmp",
            "name": "FMP",
            "description": "Good price data",
            "available": bool(FMP_API_KEY),
            "recommended": False,
        },
        {
            "id": "massive",
            "name": "Massive",
            "description": "Best price data quality",
            "available": bool(MASSIVE_API_KEY),
            "recommended": True,
        },
    ]
    
    return {
        "fundamental": fundamental_providers,
        "technical": technical_providers,
    }


@app.get("/api/rate-limits")
async def get_rate_limits():
    """Get current rate limit statistics for all providers."""
    return rate_limiter.get_all_stats()


@app.post("/api/rate-limits/reset")
async def reset_rate_limits():
    """Reset all rate limit counters (e.g., for a new day)."""
    rate_limiter.reset_all()
    return {"status": "ok", "message": "All rate limits reset"}


@app.post("/api/capital-efficiency")
async def analyze_capital_efficiency(request: CapitalEfficiencyRequest):
    """
    Analyze capital efficiency and value creation.
    
    Key metrics:
    - ROIC: Return on Invested Capital (profitability of capital)
    - Reinvestment Rate: % of earnings needed to fund growth
    - Value Spread: ROIC - WACC (positive = value creation)
    - Economic Profit (EVA): Dollar value created/destroyed
    
    Interpretation:
    - ROIC > WACC: Growth creates shareholder value
    - ROIC < WACC: Growth destroys shareholder value (despite earnings!)
    - High ROIC + Low reinvestment = Excellent capital efficiency
    """
    result = analyze_value_creation(
        nopat=request.nopat,
        invested_capital=request.invested_capital,
        revenue_growth=request.revenue_growth,
        wacc=request.wacc,
    )
    
    return {
        "roic": result["roic"],
        "roic_formatted": f"{result['roic']:.1%}" if result["roic"] else None,
        "reinvestment_rate": result["reinvestment_rate"],
        "reinvestment_rate_formatted": f"{result['reinvestment_rate']:.1%}" if result["reinvestment_rate"] else None,
        "value_spread": result["value_spread"],
        "value_spread_formatted": f"{result['value_spread']:.1%}" if result["value_spread"] else None,
        "economic_profit": result["economic_profit"],
        "is_value_creating": result["is_value_creating"],
        "assessment": result["assessment"],
    }
