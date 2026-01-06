import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
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
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
        risk_free_rate = await client.get_treasury_rate()
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RateLimitError as e:
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
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
        risk_free_rate = await client.get_treasury_rate()
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RateLimitError as e:
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
    
    # Check if we can calculate WACC
    if beta is None or market_cap is None or market_cap <= 0 or cost_of_debt is None:
        raise HTTPException(
            status_code=400, 
            detail="Cannot calculate WACC. Missing beta, market cap, or cost of debt."
        )
    
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
    
    try:
        result = await analyzer.analyze(symbol.upper(), max_peers=max_peers)
    except RateLimitError as e:
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
        
        # Get current price and shares
        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        shares = info.get("sharesOutstanding")
        
        # Analyze
        analyzer = DividendAnalyzer()
        result = analyzer.analyze(payments, current_price, shares)
        
        return {
            "symbol": symbol.upper(),
            "has_dividends": result.has_dividends,
            "current_annual_dividend": result.current_annual_dividend,
            "current_yield": result.current_yield,
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
    
    try:
        result = await service.analyze(symbol.upper(), days=days)
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RateLimitError as e:
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
