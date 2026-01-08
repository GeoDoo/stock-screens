import os
from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from dotenv import load_dotenv

from app.services.stock_data_client import StockDataClient
from app.services.data_adapter import stock_data_to_legacy
from app.services.base_provider import ProviderError, TickerNotFoundError, DataNotAvailableError, RateLimitError
from app.services.data_extractor import DataExtractor
from app.services.valuation_service import ValuationService
from app.services.fcf_projector import FCFProjector
from app.services.data_validator import DataValidator
from app.services.wacc_calculator import WACCCalculator
from app.services.scenario_calculator import ScenarioCalculator, Scenario
from app.services.comparable_analyzer import ComparableAnalyzer
from app.services.ratio_calculator import RatioCalculator
from app.services.dividend_analyzer import DividendAnalyzer, DividendPayment
from app.services.historical_valuation import HistoricalValuationAnalyzer
from app.services.fmp_client import FMPClient
from app.services.technical_service import TechnicalService
from app.services.fmp_provider import FMPProvider
from app.services.yahoo_provider import YahooProvider
from app.services.massive_provider import MassiveProvider
from app.services.rate_limiter import rate_limiter
from app.services.audit_repository import AuditRepository, get_audit_repository
from app.models.assumption_audit import (
    AssumptionField,
    AssumptionChange,
    AuditEntry,
    AssumptionSnapshot,
)

load_dotenv()

app = FastAPI(title="Stock Screens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get API keys from environment
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
MASSIVE_API_KEY = os.getenv("POLYGON_API_KEY", "")  # Polygon is now Massive


# Response models
class CompanyData(BaseModel):
    """Read-only data from FMP - user cannot change these."""
    beta: Optional[float]
    market_cap: Optional[float]
    total_debt: Optional[float]
    cash: Optional[float]
    tax_rate: Optional[float]
    cost_of_debt: Optional[float]
    shares_outstanding: Optional[float]
    risk_free_rate: float
    wacc: Optional[float]  # Calculated from the above


class HistoricalHints(BaseModel):
    """Calculated from historical data - shown as hints for user reference."""
    revenue_growth: Optional[float]
    operating_margin: Optional[float]
    da_ratio: Optional[float]
    capex_ratio: Optional[float]
    wc_ratio: Optional[float]


class ValidationIssueResponse(BaseModel):
    """A single validation issue."""
    field: str
    message: str


class ValidationResponse(BaseModel):
    """Validation results for stock data."""
    has_errors: bool
    has_warnings: bool
    errors: List[ValidationIssueResponse]
    warnings: List[ValidationIssueResponse]


class StockDataResponse(BaseModel):
    """Response for /api/stock endpoint."""
    symbol: str
    company_name: Optional[str]
    industry: Optional[str]
    sector: Optional[str]
    data_provider: str  # Which provider supplied the data (fmp, yahoo, etc.)
    data: CompanyData
    hints: HistoricalHints
    validation: ValidationResponse


class ValuationRequest(BaseModel):
    """User provides ALL of these - no defaults from backend."""
    revenue_growth: float
    operating_margin: float
    terminal_growth_rate: float
    market_risk_premium: float
    projection_years: int
    discount_rate_override: Optional[float] = None  # If set, use this instead of calculated WACC


class ScenarioInput(BaseModel):
    """A single scenario definition."""
    name: str
    revenue_growth: float  # e.g., 0.05 for 5%
    operating_margin: float  # e.g., 0.25 for 25%
    terminal_growth: float  # e.g., 0.03 for 3%
    probability: float = 0.0  # 0-1, for weighted average
    description: str = ""


class ScenarioRequest(BaseModel):
    """Request for scenario analysis."""
    scenarios: Optional[List[ScenarioInput]] = None  # If None, use defaults
    projection_years: int = 10
    market_risk_premium: float = 0.06
    discount_rate_override: Optional[float] = None  # Custom discount rate (bypasses WACC)


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


def get_fundamental_provider(provider: str):
    """Get a provider for fundamental analysis."""
    if provider == "fmp":
        if not FMP_API_KEY:
            raise HTTPException(status_code=400, detail="FMP provider requires API key")
        return FMPProvider(FMP_API_KEY)
    elif provider == "yahoo":
        return YahooProvider()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown fundamental provider: {provider}")


def get_technical_provider(provider: str):
    """Get a provider for technical analysis."""
    if provider == "massive":
        if not MASSIVE_API_KEY:
            raise HTTPException(status_code=400, detail="Massive provider requires API key")
        return MassiveProvider(MASSIVE_API_KEY)
    elif provider == "fmp":
        if not FMP_API_KEY:
            raise HTTPException(status_code=400, detail="FMP provider requires API key")
        return FMPProvider(FMP_API_KEY)
    elif provider == "yahoo":
        return YahooProvider()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown technical provider: {provider}")


def get_client_for_provider(provider: str) -> StockDataClient:
    """Get a StockDataClient configured for a specific provider only (for fundamental)."""
    if provider == "fmp":
        if not FMP_API_KEY:
            raise HTTPException(status_code=400, detail="FMP provider requires API key")
        return StockDataClient(providers=[FMPProvider(FMP_API_KEY)])
    elif provider == "yahoo":
        return StockDataClient(providers=[YahooProvider()])
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@app.get("/api/stock/{symbol}", response_model=StockDataResponse)
async def get_stock(symbol: str, provider: str):
    """
    Get stock data and historical hints.
    
    Args:
        symbol: Stock ticker symbol
        provider: Data provider to use (fmp or yahoo) - REQUIRED
    
    Returns:
    - data: Read-only values (beta, debt, cash, etc.)
    - hints: Historical averages for reference (user decides what to use)
    """
    client = get_client_for_provider(provider)
    
    # Record API call for rate limiting
    rate_limiter.record_call(provider)
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
        risk_free_rate = await client.get_treasury_rate()
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RateLimitError as e:
        rate_limiter.mark_api_limited(provider)
        raise HTTPException(status_code=429, detail=str(e))
    except DataNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock data: {str(e)}")

    # Convert to legacy format for DataExtractor
    data = stock_data_to_legacy(stock_data)
    extractor = DataExtractor(data)

    # Run validation
    validator = DataValidator(
        market_cap=extractor.market_cap(),
        beta=extractor.beta(),
        shares_outstanding=extractor.shares_outstanding(),
        total_debt=extractor.total_debt(),
        cash=extractor.cash(),
        tax_rate=extractor.tax_rate(),
        cost_of_debt=extractor.cost_of_debt(),
        revenue_history=extractor.revenue_history(),
        ebit_history=extractor.ebit_history(),
        da_history=extractor.da_history(),
        capex_history=extractor.capex_history(),
        working_capital_history=extractor.working_capital_history(),
    )
    validation_result = validator.validate()

    # Calculate historical hints
    fcf_projector = FCFProjector(
        historical_revenue=extractor.revenue_history() or [0],
        historical_ebit=extractor.ebit_history() or [0],
        historical_da=extractor.da_history() or [0],
        historical_capex=extractor.capex_history() or [0],
        historical_working_capital=extractor.working_capital_history() or [0],
        tax_rate=extractor.tax_rate() or 0.25,
    )

    # Calculate WACC for display (only if ALL required components available)
    beta = extractor.beta()
    cost_of_debt = extractor.cost_of_debt()
    tax_rate = extractor.tax_rate()
    market_cap = extractor.market_cap()
    total_debt = extractor.total_debt()
    
    # WACC requires: beta, market_cap, and cost_of_debt - no defaults!
    wacc = None
    if beta is not None and market_cap is not None and market_cap > 0 and cost_of_debt is not None:
        wacc_calculator = WACCCalculator(
            risk_free_rate=risk_free_rate,
            beta=beta,
            market_risk_premium=0.06,  # Default market risk premium is OK
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate if tax_rate is not None else 0.25,  # Tax rate default is OK
            market_cap=market_cap,
            total_debt=total_debt if total_debt is not None else 0,
        )
        wacc = wacc_calculator.calculate()

    return StockDataResponse(
        symbol=symbol.upper(),
        company_name=data.get("profile", {}).get("companyName"),
        industry=data.get("profile", {}).get("industry"),
        sector=data.get("profile", {}).get("sector"),
        data_provider=stock_data.provider,
        data=CompanyData(
            beta=extractor.beta(),
            market_cap=extractor.market_cap(),
            total_debt=extractor.total_debt(),
            cash=extractor.cash(),
            tax_rate=extractor.tax_rate(),
            cost_of_debt=extractor.cost_of_debt(),
            shares_outstanding=extractor.shares_outstanding(),
            risk_free_rate=risk_free_rate,
            wacc=wacc,
        ),
        hints=HistoricalHints(
            revenue_growth=fcf_projector.revenue_cagr() if extractor.revenue_history() else None,
            operating_margin=fcf_projector.operating_margin() if extractor.ebit_history() else None,
            da_ratio=fcf_projector.da_to_revenue_ratio() if extractor.da_history() else None,
            capex_ratio=fcf_projector.capex_to_revenue_ratio() if extractor.capex_history() else None,
            wc_ratio=fcf_projector.wc_to_revenue_ratio() if extractor.working_capital_history() else None,
        ),
        validation=ValidationResponse(**validation_result.to_dict()),
    )


@app.post("/api/stock/{symbol}/valuation")
async def run_valuation(symbol: str, provider: str, request: ValuationRequest):
    """
    Run DCF valuation with user-provided assumptions.
    
    Args:
        symbol: Stock ticker symbol
        provider: Data provider to use (fmp or yahoo) - REQUIRED
        request: Valuation assumptions from user
    """
    client = get_client_for_provider(provider)
    service = ValuationService(client=client)

    try:
        result = await service.value_stock(
            symbol=symbol.upper(),
            projection_years=request.projection_years,
            terminal_growth_rate=request.terminal_growth_rate,
            revenue_growth=request.revenue_growth,
            operating_margin=request.operating_margin,
            market_risk_premium=request.market_risk_premium,
            discount_rate_override=request.discount_rate_override,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Valuation error: {str(e)}")

    return result


@app.post("/api/stock/{symbol}/scenarios")
async def run_scenarios(symbol: str, provider: str, request: ScenarioRequest):
    """
    Run scenario analysis (Bear/Base/Bull cases).
    
    Args:
        symbol: Stock ticker symbol
        provider: Data provider to use (fmp or yahoo) - REQUIRED
        request: Scenario parameters
    
    If no scenarios provided, generates smart defaults based on historical data.
    Returns intrinsic values for each scenario and probability-weighted average.
    """
    client = get_client_for_provider(provider)
    
    # Record API call for rate limiting
    rate_limiter.record_call(provider)
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
        risk_free_rate = await client.get_treasury_rate()
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RateLimitError as e:
        rate_limiter.mark_api_limited(provider)
        raise HTTPException(status_code=429, detail=str(e))
    except DataNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock data: {str(e)}")

    # Convert to legacy format and extract data
    data = stock_data_to_legacy(stock_data)
    extractor = DataExtractor(data, market_risk_premium=request.market_risk_premium)
    
    # Calculate WACC (requires all components - no defaults)
    beta = extractor.beta()
    cost_of_debt = extractor.cost_of_debt()
    tax_rate = extractor.tax_rate()
    market_cap = extractor.market_cap()
    total_debt = extractor.total_debt()
    cash = extractor.cash() or 0
    shares = extractor.shares_outstanding() or 1
    
    # Calculate WACC or use custom discount rate
    if request.discount_rate_override is not None:
        # User provided custom discount rate
        base_wacc = request.discount_rate_override
    elif beta is None or market_cap is None or market_cap <= 0 or cost_of_debt is None:
        raise HTTPException(
            status_code=400, 
            detail="Cannot calculate WACC. Missing beta, market cap, or cost of debt. Please provide a custom discount rate."
        )
    else:
        wacc_calculator = WACCCalculator(
            risk_free_rate=risk_free_rate,
            beta=beta,
            market_risk_premium=request.market_risk_premium,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate if tax_rate is not None else 0.25,
            market_cap=market_cap,
            total_debt=total_debt if total_debt is not None else 0,
        )
        base_wacc = wacc_calculator.calculate()
    
    # Get current price
    current_price = stock_data.profile.price
    
    # Historical hints for default scenarios
    fcf_projector = FCFProjector(
        historical_revenue=extractor.revenue_history() or [0],
        historical_ebit=extractor.ebit_history() or [0],
        historical_da=extractor.da_history() or [0],
        historical_capex=extractor.capex_history() or [0],
        historical_working_capital=extractor.working_capital_history() or [0],
        tax_rate=tax_rate,
    )
    hints = {
        "revenue_growth": fcf_projector.revenue_cagr(),
        "operating_margin": fcf_projector.operating_margin(),
    }
    
    # Initialize calculator
    calculator = ScenarioCalculator(
        historical_revenue=extractor.revenue_history() or [0],
        historical_ebit=extractor.ebit_history() or [0],
        historical_da=extractor.da_history() or [0],
        historical_capex=extractor.capex_history() or [0],
        historical_working_capital=extractor.working_capital_history() or [0],
        tax_rate=tax_rate,
        shares_outstanding=shares,
        total_debt=total_debt,
        cash=cash,
        base_wacc=base_wacc,
        projection_years=request.projection_years,
        current_price=current_price,
    )
    
    # Build scenarios
    if request.scenarios:
        scenarios = [
            Scenario(
                name=s.name,
                revenue_growth=s.revenue_growth,
                operating_margin=s.operating_margin,
                terminal_growth=s.terminal_growth,
                probability=s.probability,
                description=s.description,
            )
            for s in request.scenarios
        ]
    else:
        scenarios = calculator.get_default_scenarios(hints)
    
    # Run analysis
    result = calculator.run_analysis(scenarios)
    result.symbol = symbol.upper()
    
    return {
        "symbol": result.symbol,
        "current_price": result.current_price,
        "wacc": base_wacc,
        "projection_years": request.projection_years,
        "scenarios": [
            {
                "name": s.name,
                "intrinsic_value": s.intrinsic_value,
                "upside_percent": ((s.intrinsic_value - result.current_price) / result.current_price * 100) if result.current_price else None,
                "enterprise_value": s.enterprise_value,
                "equity_value": s.equity_value,
                "probability": s.probability,
                "assumptions": {
                    "revenue_growth": s.revenue_growth,
                    "operating_margin": s.operating_margin,
                    "terminal_growth": s.terminal_growth,
                    "discount_rate": s.discount_rate,
                },
                "description": s.description,
            }
            for s in result.scenarios
        ],
        "probability_weighted_value": result.probability_weighted_value,
        "upside_range": {
            "min_percent": result.upside_range[0],
            "max_percent": result.upside_range[1],
        },
    }


@app.get("/api/stock/{symbol}/comparables")
async def get_comparables(symbol: str, provider: str, max_peers: int = 5):
    """
    Run comparable company analysis.
    
    Args:
        symbol: Stock ticker symbol
        provider: Data provider to use (fmp or yahoo) - REQUIRED
        max_peers: Maximum number of peer companies to include
    
    Compares the stock against sector peers using valuation multiples:
    - P/E (Price to Earnings)
    - EV/EBITDA (Enterprise Value to EBITDA)
    - P/S (Price to Sales)
    - P/B (Price to Book)
    
    Returns implied fair value based on peer median multiples.
    """
    client = get_client_for_provider(provider)
    analyzer = ComparableAnalyzer(client, provider)
    
    # Record API call for rate limiting
    rate_limiter.record_call(provider)
    
    try:
        result = await analyzer.analyze(symbol.upper(), max_peers=max_peers)
    except RateLimitError as e:
        rate_limiter.mark_api_limited(provider)
        raise HTTPException(status_code=429, detail=str(e))
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Comparable analysis error: {str(e)}")
    
    return {
        "symbol": result.target.symbol,
        "company_name": result.target.name,
        "current_price": result.target.price,
        "sector": result.sector,
        "industry": result.industry,
        "target_metrics": {
            "pe_ratio": result.target.pe_ratio,
            "ev_to_ebitda": result.target.ev_to_ebitda,
            "price_to_sales": result.target.price_to_sales,
            "price_to_book": result.target.price_to_book,
        },
        "peer_medians": result.peer_medians,
        "peers": [
            {
                "symbol": p.symbol,
                "name": p.name,
                "market_cap": p.market_cap,
                "pe_ratio": p.pe_ratio,
                "ev_to_ebitda": p.ev_to_ebitda,
                "price_to_sales": p.price_to_sales,
                "price_to_book": p.price_to_book,
            }
            for p in result.peers
        ],
        "implied_valuations": [
            {
                "metric": iv.metric_name,
                "peer_median": iv.peer_median,
                "company_value": iv.company_value,
                "implied_price": iv.implied_price,
                "upside_percent": iv.upside_percent,
            }
            for iv in result.implied_valuations
        ],
        "summary": {
            "average_implied_price": result.average_implied_price,
            "average_upside_percent": result.average_upside,
        },
    }


@app.get("/api/stock/{symbol}/ratios")
async def get_ratios(symbol: str, provider: str):
    """
    Get comprehensive financial ratios for a stock.
    
    Args:
        symbol: Stock ticker symbol
        provider: Data provider to use (fmp or yahoo) - REQUIRED
    
    Returns ratios organized by category:
    - Valuation: P/E, Earnings Yield, P/S, P/B, EV/EBITDA, EV/Revenue
    - Dividend: Dividend Yield, Payout Ratio
    - Profitability: Gross/Operating/Net Margins, ROE, ROA, ROIC
    - Liquidity: Current Ratio, Quick Ratio, Debt/Equity, Interest Coverage
    - Efficiency: Asset Turnover, Inventory Turnover
    """
    client = get_client_for_provider(provider)
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
        data = stock_data_to_legacy(stock_data)
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching data: {str(e)}")
    
    calculator = RatioCalculator()
    ratios = calculator.calculate(data)
    
    return {
        "symbol": symbol.upper(),
        "company_name": data.get("profile", {}).get("companyName"),
        "valuation": {
            "pe_ratio": ratios.valuation.pe_ratio,
            "earnings_yield": ratios.valuation.earnings_yield,
            "ps_ratio": ratios.valuation.ps_ratio,
            "pb_ratio": ratios.valuation.pb_ratio,
            "ev_to_ebitda": ratios.valuation.ev_to_ebitda,
            "ev_to_revenue": ratios.valuation.ev_to_revenue,
        },
        "dividend": {
            "dividend_yield": ratios.dividend.dividend_yield,
            "payout_ratio": ratios.dividend.payout_ratio,
        },
        "profitability": {
            "gross_margin": ratios.profitability.gross_margin,
            "operating_margin": ratios.profitability.operating_margin,
            "net_margin": ratios.profitability.net_margin,
            "roe": ratios.profitability.roe,
            "roa": ratios.profitability.roa,
            "roic": ratios.profitability.roic,
        },
        "liquidity": {
            "current_ratio": ratios.liquidity.current_ratio,
            "quick_ratio": ratios.liquidity.quick_ratio,
            "debt_to_equity": ratios.liquidity.debt_to_equity,
            "interest_coverage": ratios.liquidity.interest_coverage,
        },
        "efficiency": {
            "asset_turnover": ratios.efficiency.asset_turnover,
            "inventory_turnover": ratios.efficiency.inventory_turnover,
        },
    }


@app.get("/api/stock/{symbol}/dividends")
async def get_dividends(symbol: str, provider: str):
    """
    Get dividend history and metrics for a stock.
    
    Args:
        symbol: Stock ticker symbol
        provider: Data provider to use (yahoo recommended for dividend data)
    
    Returns dividend analysis including:
    - Current annual dividend and yield
    - Dividend growth rate (CAGR)
    - Consecutive years of payments
    - Annual dividend history
    """
    # Use Yahoo for dividend data as it has the best coverage
    if provider not in ["yahoo", "fmp"]:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported for dividend data")
    
    try:
        # Fetch dividend data using yfinance directly (best dividend data source)
        import yfinance as yf
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        def fetch_dividends():
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            dividends = ticker.dividends
            return info, dividends
        
        info, dividends_series = await loop.run_in_executor(None, fetch_dividends)
        
        # Convert pandas series to list of payments
        payments = []
        if dividends_series is not None and not dividends_series.empty:
            for date, amount in dividends_series.items():
                payments.append(DividendPayment(
                    date=date.strftime("%Y-%m-%d"),
                    amount=float(amount),
                ))
        
        # Get current price, shares, and net income
        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        shares = info.get("sharesOutstanding")
        net_income = info.get("netIncomeToCommon")  # For payout ratio
        
        # Analyze
        analyzer = DividendAnalyzer()
        result = analyzer.analyze(payments, current_price, shares, net_income)
        
        return {
            "symbol": symbol.upper(),
            "has_dividends": result.has_dividends,
            "current_annual_dividend": result.current_annual_dividend,
            "current_yield": result.current_yield,
            "payout_ratio": result.payout_ratio,
            "dividend_cagr": result.dividend_cagr,
            "consecutive_years": result.consecutive_years,
            "annual_dividends": result.annual_dividends,
            "payments": [
                {"date": p.date, "amount": p.amount}
                for p in result.payments[-20:]  # Last 20 payments
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dividend analysis error: {str(e)}")


@app.get("/api/stock/{symbol}/historical-valuation")
async def get_historical_valuation(symbol: str, provider: str):
    """
    Get historical valuation context for a stock.
    
    Args:
        symbol: Stock ticker symbol
        provider: Data provider to use (fmp or yahoo)
    
    Compares current valuation multiples (P/E, P/S, P/B, EV/EBITDA)
    to 5-year averages to assess if stock is cheap or expensive
    relative to its own history.
    """
    client = get_client_for_provider(provider)
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
        data = stock_data_to_legacy(stock_data)
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching data: {str(e)}")
    
    # Convert financials to list of dicts
    financials = data.get("income_statement", [])
    balance_sheet = data.get("balance_sheet", [])
    cash_flow = data.get("cash_flow", [])
    
    # Merge financial data by date
    merged_financials = []
    balance_by_date = {b.get("date"): b for b in balance_sheet} if balance_sheet else {}
    cash_by_date = {c.get("date"): c for c in cash_flow} if cash_flow else {}
    
    for inc in financials:
        date = inc.get("date")
        bal = balance_by_date.get(date, {})
        cf = cash_by_date.get(date, {})
        
        merged = {**inc, **bal, **cf, "date": date}
        merged_financials.append(merged)
    
    profile = data.get("profile", {})
    
    analyzer = HistoricalValuationAnalyzer()
    result = analyzer.analyze(merged_financials, profile)
    
    return {
        "symbol": symbol.upper(),
        "current": {
            "pe": result.current_pe,
            "ps": result.current_ps,
            "pb": result.current_pb,
            "ev_ebitda": result.current_ev_ebitda,
        },
        "average_5yr": {
            "pe": result.avg_pe_5yr,
            "ps": result.avg_ps_5yr,
            "pb": result.avg_pb_5yr,
            "ev_ebitda": result.avg_ev_ebitda_5yr,
        },
        "premium_discount": {
            "pe": result.premium_discount_pe,
            "ps": result.premium_discount_ps,
            "pb": result.premium_discount_pb,
            "ev_ebitda": result.premium_discount_ev_ebitda,
        },
        "assessment": {
            "pe": result.pe_assessment,
            "ps": result.ps_assessment,
            "pb": result.pb_assessment,
            "ev_ebitda": result.ev_ebitda_assessment,
        },
        "yearly_metrics": [
            {
                "year": ym.year,
                "revenue": ym.revenue,
                "net_income": ym.net_income,
                "ebitda": ym.ebitda,
                "pe": ym.pe,
                "ps": ym.ps,
                "pb": ym.pb,
                "ev_ebitda": ym.ev_ebitda,
            }
            for ym in result.yearly_metrics
        ],
    }


@app.get("/api/stock/{symbol}/technical")
async def get_technical_analysis(symbol: str, provider: str = "massive", days: int = 365):
    """
    Run technical analysis on a stock.
    
    Args:
        symbol: Stock ticker symbol
        provider: Technical analysis provider (yahoo, fmp, massive)
        days: Days of historical data (default 365)
    
    Returns:
        Price data, moving averages, RSI, MACD, and trend signals.
    """
    tech_provider = get_technical_provider(provider)
    service = TechnicalService(tech_provider)
    
    # Record API call for rate limiting
    rate_limiter.record_call(provider)
    
    try:
        result = await service.analyze(symbol.upper(), days=days)
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RateLimitError as e:
        rate_limiter.mark_api_limited(provider)
        raise HTTPException(status_code=429, detail=str(e))
    except DataNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Technical analysis error: {str(e)}")
    
    return {
        "symbol": result.symbol,
        "provider": provider,
        "period_days": result.period_days,
        "current_price": result.current_price,
        "price_change_pct": result.price_change_pct,
        "prices": result.prices,
        "indicators": {
            "sma_20": [{"timestamp": v.timestamp, "value": v.value} for v in result.sma_20],
            "sma_50": [{"timestamp": v.timestamp, "value": v.value} for v in result.sma_50],
            "ema_12": [{"timestamp": v.timestamp, "value": v.value} for v in result.ema_12],
            "ema_26": [{"timestamp": v.timestamp, "value": v.value} for v in result.ema_26],
            "rsi_14": [{"timestamp": v.timestamp, "value": v.value} for v in result.rsi_14],
            "macd": [
                {"timestamp": v.timestamp, "macd": v.macd, "signal": v.signal, "histogram": v.histogram}
                for v in result.macd
            ],
        },
        "signals": {
            "trend": result.trend,
            "rsi": result.rsi_signal,
            "macd": result.macd_signal,
        },
    }


# ============================================================
# BATCH ANALYZE ENDPOINT - Reduces API calls
# ============================================================

@app.get("/api/stock/{symbol}/analyze")
async def batch_analyze(symbol: str, provider: str):
    """
    Batch analyze endpoint - returns all fundamental data in a single call.
    
    This reduces API calls by fetching stock data once and computing all
    derived metrics (ratios, dividends, historical valuation) from that data.
    
    Returns:
        - stock: Basic stock data and validation
        - ratios: Financial ratios
        - dividends: Dividend history and metrics
        - historical_valuation: Historical valuation context
        - rate_limit: Current rate limit status for the provider
    """
    client = get_client_for_provider(provider)
    
    # Record API call for accurate rate limiting
    rate_limiter.record_call(provider)
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
        risk_free_rate = await client.get_treasury_rate()
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RateLimitError as e:
        # Mark provider as rate-limited (source of truth from actual API)
        rate_limiter.mark_api_limited(provider)
        raise HTTPException(status_code=429, detail=str(e))
    except DataNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock data: {str(e)}")

    # Convert to legacy format for extractors
    data = stock_data_to_legacy(stock_data)
    extractor = DataExtractor(data)
    
    # === Build stock response ===
    beta = extractor.beta()
    cost_of_debt = extractor.cost_of_debt()
    tax_rate = extractor.tax_rate()
    market_cap = extractor.market_cap()
    total_debt = extractor.total_debt()
    
    wacc = None
    if beta is not None and market_cap is not None and market_cap > 0 and cost_of_debt is not None:
        wacc_calculator = WACCCalculator(
            risk_free_rate=risk_free_rate,
            beta=beta,
            market_risk_premium=0.06,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate if tax_rate is not None else 0.25,
            market_cap=market_cap,
            total_debt=total_debt if total_debt is not None else 0,
        )
        wacc = wacc_calculator.calculate()
    
    fcf_projector = FCFProjector(
        historical_revenue=extractor.revenue_history() or [0],
        historical_ebit=extractor.ebit_history() or [0],
        historical_da=extractor.da_history() or [0],
        historical_capex=extractor.capex_history() or [0],
        historical_working_capital=extractor.working_capital_history() or [0],
        tax_rate=tax_rate,
    )
    
    validator = DataValidator(
        beta=beta,
        market_cap=market_cap,
        shares_outstanding=extractor.shares_outstanding(),
        total_debt=total_debt,
        cash=extractor.cash(),
        tax_rate=tax_rate,
        cost_of_debt=cost_of_debt,
        revenue_history=extractor.revenue_history() or [],
        ebit_history=extractor.ebit_history() or [],
        da_history=extractor.da_history() or [],
        capex_history=extractor.capex_history() or [],
        working_capital_history=extractor.working_capital_history() or [],
    )
    validation_result = validator.validate()
    
    stock_response = {
        "symbol": symbol.upper(),
        "company_name": data.get("profile", {}).get("companyName"),
        "industry": data.get("profile", {}).get("industry"),
        "sector": data.get("profile", {}).get("sector"),
        "data": {
            "beta": beta,
            "market_cap": market_cap,
            "total_debt": total_debt,
            "cash": extractor.cash(),
            "tax_rate": tax_rate,
            "cost_of_debt": cost_of_debt,
            "shares_outstanding": extractor.shares_outstanding(),
            "risk_free_rate": risk_free_rate,
            "wacc": wacc,
        },
        "hints_annual": {
            "revenue_growth": fcf_projector.revenue_cagr(),
            "operating_margin": fcf_projector.operating_margin(),
            "da_to_revenue": fcf_projector.da_to_revenue_ratio(),
            "capex_to_revenue": fcf_projector.capex_to_revenue_ratio(),
            "wc_to_revenue": fcf_projector.wc_to_revenue_ratio(),
        },
        "hints_ttm": None,  # Will be populated below for Yahoo
        "validation": validation_result.to_dict(),
        "data_provider": stock_data.provider,
    }
    
    # === Common variables for multiple sections ===
    financials = stock_data.financials
    current_price = stock_data.profile.price
    shares = stock_data.profile.shares_outstanding
    
    # === Build ratios response (ANNUAL - from most recent annual report) ===
    ratio_calculator = RatioCalculator()
    ratios = ratio_calculator.calculate(data)
    
    ratios_annual = {
        "symbol": symbol.upper(),
        "period": "annual",
        "valuation": {
            "pe_ratio": ratios.valuation.pe_ratio,
            "earnings_yield": ratios.valuation.earnings_yield,
            "ps_ratio": ratios.valuation.ps_ratio,
            "pb_ratio": ratios.valuation.pb_ratio,
        },
        "profitability": {
            "gross_margin": ratios.profitability.gross_margin,
            "operating_margin": ratios.profitability.operating_margin,
            "net_margin": ratios.profitability.net_margin,
            "roe": ratios.profitability.roe,
            "roa": ratios.profitability.roa,
        },
        "liquidity": {
            "current_ratio": ratios.liquidity.current_ratio,
            "quick_ratio": ratios.liquidity.quick_ratio,
            "debt_to_equity": ratios.liquidity.debt_to_equity,
        },
        "efficiency": {
            "asset_turnover": ratios.efficiency.asset_turnover,
            "inventory_turnover": ratios.efficiency.inventory_turnover,
        },
    }
    
    # === Build TTM data (ratios and hints from quarterly data) ===
    ratios_ttm = None
    hints_ttm = None
    
    if provider == "yahoo":
        from app.services.yahoo_provider import YahooProvider
        yahoo = YahooProvider()
        ttm_financials = yahoo.get_ttm_financials_sync(symbol)
        
        if ttm_financials:
            # Build legacy format for TTM (keys must match ratio_calculator expectations)
            ttm_data = {
                "profile": data.get("profile", {}),
                "income_statement": [{
                    "revenue": ttm_financials.revenue,
                    "grossProfit": ttm_financials.gross_profit,
                    "operatingIncome": ttm_financials.operating_income,
                    "netIncome": ttm_financials.net_income,
                    "interestExpense": ttm_financials.interest_expense,
                }],
                "balance_sheet": [{
                    "totalAssets": ttm_financials.total_assets,
                    "totalLiabilities": ttm_financials.total_liabilities,
                    "totalStockholdersEquity": ttm_financials.total_equity,
                    "totalDebt": ttm_financials.total_debt,
                    "cashAndCashEquivalents": ttm_financials.cash_and_equivalents,
                    "totalCurrentAssets": ttm_financials.current_assets,
                    "totalCurrentLiabilities": ttm_financials.current_liabilities,
                }],
            }
            ttm_ratios = ratio_calculator.calculate(ttm_data)
            
            ratios_ttm = {
                "symbol": symbol.upper(),
                "period": "ttm",
                "valuation": {
                    "pe_ratio": ttm_ratios.valuation.pe_ratio,
                    "earnings_yield": ttm_ratios.valuation.earnings_yield,
                    "ps_ratio": ttm_ratios.valuation.ps_ratio,
                    "pb_ratio": ttm_ratios.valuation.pb_ratio,
                },
                "profitability": {
                    "gross_margin": ttm_ratios.profitability.gross_margin,
                    "operating_margin": ttm_ratios.profitability.operating_margin,
                    "net_margin": ttm_ratios.profitability.net_margin,
                    "roe": ttm_ratios.profitability.roe,
                    "roa": ttm_ratios.profitability.roa,
                },
                "liquidity": {
                    "current_ratio": ttm_ratios.liquidity.current_ratio,
                    "quick_ratio": ttm_ratios.liquidity.quick_ratio,
                    "debt_to_equity": ttm_ratios.liquidity.debt_to_equity,
                },
                "efficiency": {
                    "asset_turnover": ttm_ratios.efficiency.asset_turnover,
                    "inventory_turnover": ttm_ratios.efficiency.inventory_turnover,
                },
            }
            
            # Calculate TTM hints for DCF projections
            ttm_revenue = ttm_financials.revenue
            ttm_operating_income = ttm_financials.operating_income
            ttm_da = ttm_financials.depreciation_amortization
            ttm_capex = ttm_financials.capital_expenditure
            ttm_current_assets = ttm_financials.current_assets
            ttm_current_liabilities = ttm_financials.current_liabilities
            
            # Calculate working capital change (simplified - uses current period)
            ttm_wc = None
            if ttm_current_assets is not None and ttm_current_liabilities is not None:
                ttm_wc = ttm_current_assets - ttm_current_liabilities
            
            hints_ttm = {
                "revenue_growth": stock_response["hints_annual"]["revenue_growth"],  # Use annual CAGR (TTM YoY is complex)
                "operating_margin": (ttm_operating_income / ttm_revenue) if ttm_revenue and ttm_operating_income else None,
                "da_to_revenue": (ttm_da / ttm_revenue) if ttm_revenue and ttm_da else None,
                "capex_to_revenue": (abs(ttm_capex) / ttm_revenue) if ttm_revenue and ttm_capex else None,  # CapEx is negative
                "wc_to_revenue": (ttm_wc / ttm_revenue) if ttm_revenue and ttm_wc else None,
            }
    
    # Update stock_response with TTM hints
    stock_response["hints_ttm"] = hints_ttm
    
    ratios_response = {
        "annual": ratios_annual,
        "ttm": ratios_ttm,
    }
    
    # === Build dividends response ===
    analyzer = DividendAnalyzer()
    payments = []
    for fin in financials:
        if fin.dividends_paid is not None and fin.dividends_paid != 0 and shares and shares > 0:
            # IMPORTANT: dividends_paid is TOTAL company dividends, not per-share
            # Convert to per-share by dividing by shares outstanding
            per_share_dividend = abs(fin.dividends_paid) / shares
            payments.append(DividendPayment(
                date=fin.date,
                amount=per_share_dividend,
            ))
    
    net_income = financials[0].net_income if financials else None
    dividend_result = analyzer.analyze(payments, current_price, shares, net_income)
    
    dividends_response = {
        "symbol": symbol.upper(),
        "has_dividends": dividend_result.has_dividends,
        "current_annual_dividend": dividend_result.current_annual_dividend,
        "current_yield": dividend_result.current_yield,
        "dividend_cagr": dividend_result.dividend_cagr,
        "consecutive_years": dividend_result.consecutive_years,
        "payout_ratio": dividend_result.payout_ratio,
        "annual_dividends": dividend_result.annual_dividends,
        "payments": [{"date": p.date, "amount": p.amount} for p in payments],
    }
    
    # === Build historical valuation response ===
    # Merge financials for historical analyzer (needs legacy format)
    income_statements = data.get("income_statement", [])
    balance_sheets = data.get("balance_sheet", [])
    cash_flows = data.get("cash_flow", [])
    
    balance_by_date = {b.get("date"): b for b in balance_sheets}
    cash_by_date = {c.get("date"): c for c in cash_flows}
    
    merged_financials = []
    for inc in income_statements:
        date = inc.get("date")
        bal = balance_by_date.get(date, {})
        cf = cash_by_date.get(date, {})
        merged = {**inc, **bal, **cf, "date": date}
        merged_financials.append(merged)
    
    profile = data.get("profile", {})
    
    hist_analyzer = HistoricalValuationAnalyzer()
    hist_result = hist_analyzer.analyze(merged_financials, profile)
    
    historical_response = {
        "symbol": symbol.upper(),
        "current": {
            "pe": hist_result.current_pe,
            "ps": hist_result.current_ps,
            "pb": hist_result.current_pb,
            "ev_ebitda": hist_result.current_ev_ebitda,
        },
        "average_5yr": {
            "pe": hist_result.avg_pe_5yr,
            "ps": hist_result.avg_ps_5yr,
            "pb": hist_result.avg_pb_5yr,
            "ev_ebitda": hist_result.avg_ev_ebitda_5yr,
        },
        "assessment": {
            "pe": hist_result.pe_assessment,
            "ps": hist_result.ps_assessment,
            "pb": hist_result.pb_assessment,
            "ev_ebitda": hist_result.ev_ebitda_assessment,
        },
    }
    
    return {
        "stock": stock_response,
        "ratios": ratios_response,
        "dividends": dividends_response,
        "historical_valuation": historical_response,
        "rate_limit": rate_limiter.get_usage_stats(provider),
    }


# ============================================================
# RATE LIMIT ENDPOINTS
# ============================================================

@app.get("/api/rate-limits")
async def get_rate_limits():
    """Get current rate limit statistics for all providers."""
    return rate_limiter.get_all_stats()


@app.post("/api/rate-limits/reset")
async def reset_rate_limits():
    """Reset all rate limit counters (e.g., for a new day)."""
    rate_limiter.reset_all()
    return {"status": "ok", "message": "All rate limits reset"}


# ============================================================
# ASSUMPTION AUDIT TRAIL ENDPOINTS
# ============================================================

class AuditRequest(BaseModel):
    """Request to record assumption changes."""
    assumptions: dict  # Field name -> value
    note: Optional[str] = None
    # Market context at time of recording (for thesis tracking)
    price_at_time: Optional[float] = None
    intrinsic_value_at_time: Optional[float] = None
    pe_ratio_at_time: Optional[float] = None


@app.post("/api/audit/{symbol}", status_code=201)
async def record_assumptions(
    symbol: str,
    request: AuditRequest,
    response: Response,
    repo: AuditRepository = Depends(get_audit_repository),
):
    """
    Record assumption changes for a stock.
    
    Args:
        symbol: Stock ticker symbol
        request: New assumptions and optional note
    
    On first call for a symbol, creates an initial entry (baseline).
    On subsequent calls, only records fields that changed from previous snapshot.
    
    Returns:
        - 201 with saved audit entry when changes recorded
        - 200 with empty changes if nothing changed
    """
    symbol = symbol.upper()
    
    # Get previous snapshot (or empty if first analysis)
    previous = repo.get_latest_snapshot(symbol)
    is_initial = previous is None
    
    if previous is None:
        previous = AssumptionSnapshot(symbol=symbol)
    
    # Detect what changed
    changes = previous.diff(request.assumptions)
    
    if not changes and not is_initial:
        # Nothing changed - don't create an entry
        response.status_code = 200
        return {"message": "No changes detected", "changes": []}
    
    # Create and save the entry
    entry = AuditEntry(
        id=None,
        symbol=symbol,
        timestamp=datetime.now(),
        changes=changes,
        note=request.note,
        is_initial=is_initial,
        price_at_time=request.price_at_time,
        intrinsic_value_at_time=request.intrinsic_value_at_time,
        pe_ratio_at_time=request.pe_ratio_at_time,
    )
    
    saved = repo.save_entry(entry)
    
    return saved.to_dict()


@app.get("/api/audit/{symbol}/history")
async def get_audit_history(
    symbol: str,
    limit: int = 50,
    repo: AuditRepository = Depends(get_audit_repository),
):
    """
    Get assumption change history for a stock.
    
    Args:
        symbol: Stock ticker symbol
        limit: Maximum entries to return (default 50)
    
    Returns:
        List of audit entries, most recent first.
    """
    history = repo.get_history(symbol.upper(), limit=limit)
    return [entry.to_dict() for entry in history]


@app.get("/api/audit/{symbol}/snapshot")
async def get_audit_snapshot(
    symbol: str,
    repo: AuditRepository = Depends(get_audit_repository),
):
    """
    Get the current assumption snapshot for a stock.
    
    Reconstructs the current state by replaying all changes.
    
    Returns:
        Current assumption values, or 404 if no history exists.
    """
    snapshot = repo.get_latest_snapshot(symbol.upper())
    
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No audit history for {symbol}")
    
    return {
        "symbol": snapshot.symbol,
        "revenue_growth": snapshot.revenue_growth,
        "operating_margin": snapshot.operating_margin,
        "terminal_growth": snapshot.terminal_growth,
        "discount_rate": snapshot.discount_rate,
        "projection_years": snapshot.projection_years,
        "market_risk_premium": snapshot.market_risk_premium,
    }


@app.get("/api/audit/{symbol}/field/{field}")
async def get_field_history(
    symbol: str,
    field: str,
    repo: AuditRepository = Depends(get_audit_repository),
):
    """
    Get change history for a specific assumption field.
    
    Args:
        symbol: Stock ticker symbol
        field: Field name (revenue_growth, operating_margin, etc.)
    
    Returns:
        List of changes for that field, most recent first.
    """
    # Validate field name
    try:
        field_enum = AssumptionField(field)
    except ValueError:
        valid_fields = [f.value for f in AssumptionField]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field '{field}'. Valid fields: {valid_fields}"
        )
    
    changes = repo.get_field_history(symbol.upper(), field_enum)
    
    return [
        {
            "field": c.field.value,
            "old_value": c.old_value,
            "new_value": c.new_value,
        }
        for c in changes
    ]
