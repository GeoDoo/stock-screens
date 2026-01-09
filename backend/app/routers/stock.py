"""Stock data and valuation endpoints."""
import os
from fastapi import APIRouter, HTTPException

from app.constants import DEFAULT_TAX_RATE, DEFAULT_MARKET_RISK_PREMIUM
from app.schemas.stock import (
    StockDataResponse,
    CompanyData,
    HistoricalHints,
    ValuationRequest,
    ScenarioRequest,
    ScenarioInput,
    MonteCarloRequest,
    FullMonteCarloRequest,
    CapitalEfficiencyRequest,
)
from app.schemas.common import ValidationResponse
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
from app.services.technical_service import TechnicalService
from app.services.fmp_provider import FMPProvider
from app.services.yahoo_provider import YahooProvider
from app.services.massive_provider import MassiveProvider
from app.services.rate_limiter_sqlite import rate_limiter
from app.services.monte_carlo import run_monte_carlo_valuation
from app.services.monte_carlo_full import run_full_monte_carlo
from app.services.capital_efficiency import analyze_value_creation

router = APIRouter(prefix="/api/stock", tags=["stock"])

# Get API keys from environment
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
MASSIVE_API_KEY = os.getenv("POLYGON_API_KEY", "")


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
    """Get a StockDataClient configured for a specific provider only."""
    if provider == "fmp":
        if not FMP_API_KEY:
            raise HTTPException(status_code=400, detail="FMP provider requires API key")
        return StockDataClient(providers=[FMPProvider(FMP_API_KEY)])
    elif provider == "yahoo":
        return StockDataClient(providers=[YahooProvider()])
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


async def _fetch_year_end_prices(
    symbol: str, 
    financials: list, 
    client: StockDataClient,
) -> dict:
    """
    Fetch year-end stock prices for true historical valuation.
    
    For each fiscal year-end date in financials, finds the closing price
    on or near that date from historical price data.
    
    Args:
        symbol: Stock ticker symbol
        financials: List of merged financial statements with date field
        client: StockDataClient with providers that support historical prices
        
    Returns:
        Dict mapping year to year-end price: {2023: 150.0, 2022: 120.0, ...}
        Empty dict if historical prices cannot be fetched.
    """
    if not financials:
        return {}
    
    # Extract fiscal year-end dates
    fiscal_dates = []
    for fin in financials:
        date_str = fin.get("date")
        if date_str:
            fiscal_dates.append(date_str)
    
    if not fiscal_dates:
        return {}
    
    # Need about 5 years of price data (1825 days, round up to 2000)
    try:
        # Use the first available provider that supports historical prices
        provider = client.providers[0] if client.providers else None
        if not provider or not getattr(provider, 'supports_technical', False):
            return {}
        
        historical = await provider.get_historical_prices(symbol.upper(), days=2000)
        
        if not historical.bars:
            return {}
        
        # Build a date -> price lookup
        price_by_date = {bar.timestamp: bar.close for bar in historical.bars}
        
        # For each fiscal year-end, find the closest price
        year_end_prices = {}
        for date_str in fiscal_dates:
            try:
                year = int(date_str[:4])
            except (ValueError, TypeError):
                continue
            
            # Try exact match first
            if date_str in price_by_date:
                year_end_prices[year] = price_by_date[date_str]
                continue
            
            # Find closest date within 10 days
            from datetime import datetime, timedelta
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            
            best_price = None
            best_delta = None
            for bar_date_str, price in price_by_date.items():
                try:
                    bar_date = datetime.strptime(bar_date_str, "%Y-%m-%d")
                except ValueError:
                    continue
                
                delta = abs((bar_date - target_date).days)
                if delta <= 10 and (best_delta is None or delta < best_delta):
                    best_delta = delta
                    best_price = price
            
            if best_price is not None:
                year_end_prices[year] = best_price
        
        return year_end_prices
        
    except Exception:
        # If historical prices fail, return empty dict to fall back to proxy mode
        return {}


@router.get("/{symbol}", response_model=StockDataResponse)
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
            market_risk_premium=DEFAULT_MARKET_RISK_PREMIUM,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate if tax_rate is not None else DEFAULT_TAX_RATE,
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
            total_equity=extractor.total_equity(),
            cash=extractor.cash(),
            tax_rate=extractor.tax_rate(),
            cost_of_debt=extractor.cost_of_debt(),
            shares_outstanding=extractor.shares_outstanding(),
            risk_free_rate=risk_free_rate,
            wacc=wacc,
            revenue=extractor.latest_revenue(),
            working_capital=extractor.latest_working_capital(),
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


@router.post("/{symbol}/valuation")
async def run_valuation(symbol: str, provider: str, request: ValuationRequest):
    """
    Run DCF valuation with user-provided assumptions.
    
    Supports two modes:
    1. Single growth rate: Uses revenue_growth for all projection_years
    2. Multi-stage growth: Uses growth_stages to define phases (overrides revenue_growth)
    """
    from app.services.multi_stage_growth import GrowthStage, MultiStageGrowthModel
    
    client = get_client_for_provider(provider)
    service = ValuationService(client=client)

    # Determine if using multi-stage growth
    growth_schedule = None
    projection_years = request.projection_years
    
    if request.growth_stages and len(request.growth_stages) > 0:
        # Convert API stages to model stages
        stages = [
            GrowthStage(
                name=s.name,
                years=s.years,
                growth_rate=s.growth_rate,
                end_growth_rate=s.end_growth_rate,
            )
            for s in request.growth_stages
        ]
        model = MultiStageGrowthModel(
            stages=stages,
            terminal_growth_rate=request.terminal_growth_rate,
        )
        growth_schedule = model.growth_schedule
        projection_years = model.total_projection_years

    try:
        result = await service.value_stock(
            symbol=symbol.upper(),
            projection_years=projection_years,
            terminal_growth_rate=request.terminal_growth_rate,
            revenue_growth=request.revenue_growth,
            operating_margin=request.operating_margin,
            market_risk_premium=request.market_risk_premium,
            discount_rate_override=request.discount_rate_override,
            da_ratio=request.da_ratio,
            capex_ratio=request.capex_ratio,
            wc_ratio=request.wc_ratio,
            use_mid_year_discounting=request.use_mid_year_discounting,
            wc_mode=request.wc_mode,
            growth_schedule=growth_schedule,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Valuation error: {str(e)}")

    return result


@router.post("/{symbol}/scenarios")
async def run_scenarios(symbol: str, provider: str, request: ScenarioRequest):
    """
    Run scenario analysis (Bear/Base/Bull cases).
    
    If no scenarios provided, generates smart defaults based on historical data.
    Returns intrinsic values for each scenario and probability-weighted average.
    """
    client = get_client_for_provider(provider)
    
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

    data = stock_data_to_legacy(stock_data)
    extractor = DataExtractor(data, market_risk_premium=request.market_risk_premium)
    
    beta = extractor.beta()
    cost_of_debt = extractor.cost_of_debt()
    tax_rate = extractor.tax_rate()
    market_cap = extractor.market_cap()
    total_debt = extractor.total_debt()
    cash = extractor.cash() or 0
    shares = extractor.shares_outstanding() or 1
    
    if request.discount_rate_override is not None:
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
            tax_rate=tax_rate if tax_rate is not None else DEFAULT_TAX_RATE,
            market_cap=market_cap,
            total_debt=total_debt if total_debt is not None else 0,
        )
        base_wacc = wacc_calculator.calculate()
    
    current_price = stock_data.profile.price
    
    fcf_projector = FCFProjector(
        historical_revenue=extractor.revenue_history() or [0],
        historical_ebit=extractor.ebit_history() or [0],
        historical_da=extractor.da_history() or [0],
        historical_capex=extractor.capex_history() or [0],
        historical_working_capital=extractor.working_capital_history() or [0],
        tax_rate=tax_rate,
    )
    hints = {
        "revenue_growth": request.revenue_growth_hint if request.revenue_growth_hint is not None else fcf_projector.revenue_cagr(),
        "operating_margin": request.operating_margin_hint if request.operating_margin_hint is not None else fcf_projector.operating_margin(),
    }
    
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
        da_ratio=request.da_ratio,
        capex_ratio=request.capex_ratio,
        wc_ratio=request.wc_ratio,
    )
    
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


@router.get("/{symbol}/comparables")
async def get_comparables(symbol: str, provider: str, max_peers: int = 5):
    """
    Run comparable company analysis.
    
    Compares the stock against sector peers using valuation multiples.
    Returns implied fair value based on peer median multiples.
    """
    client = get_client_for_provider(provider)
    analyzer = ComparableAnalyzer(client, provider)
    
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


@router.get("/{symbol}/ratios")
async def get_ratios(symbol: str, provider: str):
    """
    Get comprehensive financial ratios for a stock.
    
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


@router.get("/{symbol}/dividends")
async def get_dividends(symbol: str, provider: str):
    """
    Get dividend history and metrics for a stock.
    
    Returns dividend analysis including:
    - Current annual dividend and yield
    - Dividend growth rate (CAGR)
    - Consecutive years of payments
    - Annual dividend history
    """
    if provider not in ["yahoo", "fmp"]:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported for dividend data")
    
    try:
        import yfinance as yf
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        def fetch_dividends():
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            dividends = ticker.dividends
            return info, dividends
        
        info, dividends_series = await loop.run_in_executor(None, fetch_dividends)
        
        payments = []
        if dividends_series is not None and not dividends_series.empty:
            for date, amount in dividends_series.items():
                payments.append(DividendPayment(
                    date=date.strftime("%Y-%m-%d"),
                    amount=float(amount),
                ))
        
        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        shares = info.get("sharesOutstanding")
        net_income = info.get("netIncomeToCommon")
        
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
                for p in result.payments[-20:]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dividend analysis error: {str(e)}")


@router.get("/{symbol}/historical-valuation")
async def get_historical_valuation(symbol: str, provider: str):
    """
    Get historical valuation context for a stock.
    
    Compares current valuation multiples (P/E, P/S, P/B, EV/EBITDA)
    to 5-year averages to assess if stock is cheap or expensive
    relative to its own history.
    
    Uses true historical prices when available for accurate historical
    multiples, falling back to current market cap proxy if historical
    prices cannot be fetched.
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
    
    financials = data.get("income_statement", [])
    balance_sheet = data.get("balance_sheet", [])
    cash_flow = data.get("cash_flow", [])
    
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
    
    # Fetch historical prices for true historical valuation
    historical_prices = await _fetch_year_end_prices(symbol, merged_financials, client)
    
    analyzer = HistoricalValuationAnalyzer()
    result = analyzer.analyze(merged_financials, profile, historical_prices=historical_prices)
    
    return {
        "symbol": symbol.upper(),
        "uses_true_historical_prices": result.uses_true_historical_prices,
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


@router.get("/{symbol}/technical")
async def get_technical_analysis(symbol: str, provider: str = "massive", days: int = 365):
    """
    Run technical analysis on a stock.
    
    Returns:
        Price data, moving averages, RSI, MACD, and trend signals.
    """
    tech_provider = get_technical_provider(provider)
    service = TechnicalService(tech_provider)
    
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


@router.get("/{symbol}/analyze")
async def batch_analyze(symbol: str, provider: str):
    """
    Batch analyze endpoint - returns all fundamental data in a single call.
    
    This reduces API calls by fetching stock data once and computing all
    derived metrics (ratios, dividends, historical valuation) from that data.
    
    Note: All blocking I/O (yfinance calls) is run via run_in_executor()
    to avoid blocking the event loop.
    """
    client = get_client_for_provider(provider)
    
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

    data = stock_data_to_legacy(stock_data)
    extractor = DataExtractor(data)
    
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
            market_risk_premium=DEFAULT_MARKET_RISK_PREMIUM,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate if tax_rate is not None else DEFAULT_TAX_RATE,
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
            "total_equity": extractor.total_equity(),
            "cash": extractor.cash(),
            "tax_rate": tax_rate,
            "cost_of_debt": cost_of_debt,
            "shares_outstanding": extractor.shares_outstanding(),
            "risk_free_rate": risk_free_rate,
            "wacc": wacc,
            "revenue": extractor.latest_revenue(),
            "working_capital": extractor.latest_working_capital(),
        },
        "hints_annual": {
            "revenue_growth": fcf_projector.revenue_cagr(),
            "operating_margin": fcf_projector.operating_margin(),
            "da_ratio": fcf_projector.da_to_revenue_ratio(),
            "capex_ratio": fcf_projector.capex_to_revenue_ratio(),
            "wc_ratio": fcf_projector.wc_to_revenue_ratio(),
        },
        "hints_ttm": None,
        "validation": validation_result.to_dict(),
        "data_provider": stock_data.provider,
    }
    
    financials = stock_data.financials
    current_price = stock_data.profile.price
    shares = stock_data.profile.shares_outstanding
    
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
    
    ratios_ttm = None
    hints_ttm = None
    
    if provider == "yahoo":
        yahoo = YahooProvider()
        ttm_financials = await yahoo.get_ttm_financials(symbol)
        
        if ttm_financials:
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
            
            ttm_revenue = ttm_financials.revenue
            ttm_operating_income = ttm_financials.operating_income
            ttm_da = ttm_financials.depreciation_amortization
            ttm_capex = ttm_financials.capital_expenditure
            ttm_current_assets = ttm_financials.current_assets
            ttm_current_liabilities = ttm_financials.current_liabilities
            
            ttm_wc = None
            if ttm_current_assets is not None and ttm_current_liabilities is not None:
                ttm_wc = ttm_current_assets - ttm_current_liabilities
            
            hints_ttm = {
                "revenue_growth": stock_response["hints_annual"]["revenue_growth"],
                "operating_margin": (ttm_operating_income / ttm_revenue) if ttm_revenue and ttm_operating_income else None,
                "da_ratio": (ttm_da / ttm_revenue) if ttm_revenue and ttm_da else None,
                "capex_ratio": (abs(ttm_capex) / ttm_revenue) if ttm_revenue and ttm_capex else None,
                "wc_ratio": (ttm_wc / ttm_revenue) if ttm_revenue and ttm_wc else None,
            }
    
    stock_response["hints_ttm"] = hints_ttm
    
    ratios_response = {
        "annual": ratios_annual,
        "ttm": ratios_ttm,
    }
    
    analyzer = DividendAnalyzer()
    payments = []
    
    # Use async-safe dividend fetcher to avoid blocking event loop
    yahoo_dividends = YahooProvider()
    try:
        dividend_data = await yahoo_dividends.get_dividends(symbol)
        for div in dividend_data:
            payments.append(DividendPayment(
                date=div["date"],
                amount=div["amount"],
            ))
    except Exception:
        # Fallback to financials-based dividend calculation
        for fin in financials:
            if fin.dividends_paid is not None and fin.dividends_paid != 0 and shares and shares > 0:
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


@router.post("/{symbol}/monte-carlo")
async def run_monte_carlo(
    symbol: str,
    request: MonteCarloRequest,
    provider: str = "yahoo",
):
    """
    Run Monte Carlo simulation on DCF valuation (simplified/quick mode).
    
    Varies growth, margin, and discount rate to produce a probability
    distribution of intrinsic values.
    """
    actual_provider = provider
    if rate_limiter.is_api_limited(provider):
        actual_provider = "yahoo"
    
    client = get_client_for_provider(actual_provider)
    rate_limiter.record_call(actual_provider)
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
    except (RateLimitError, DataNotAvailableError) as e:
        if actual_provider != "yahoo":
            client = get_client_for_provider("yahoo")
            rate_limiter.record_call("yahoo")
            try:
                stock_data = await client.get_stock_data(symbol.upper())
                actual_provider = "yahoo"
            except Exception:
                raise HTTPException(status_code=429, detail=f"Rate limit exceeded for {provider}. Try again later or switch provider.")
        else:
            raise HTTPException(status_code=429, detail=str(e))
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    data = stock_data_to_legacy(stock_data)
    extractor = DataExtractor(data)
    
    revenue_history = extractor.revenue_history()
    if not revenue_history:
        raise HTTPException(status_code=400, detail="No revenue data available")
    
    base_revenue = revenue_history[-1]
    
    result = run_monte_carlo_valuation(
        base_revenue=base_revenue,
        base_growth=request.base_growth,
        growth_std=request.growth_std,
        base_margin=request.base_margin,
        margin_std=request.margin_std,
        base_discount_rate=request.base_discount_rate,
        discount_std=request.discount_std,
        terminal_growth=request.terminal_growth,
        projection_years=request.projection_years,
        iterations=request.iterations,
    )
    
    shares = extractor.shares_outstanding() or 1
    net_debt = (extractor.total_debt() or 0) - (extractor.cash() or 0)
    
    def ev_to_per_share(ev: float) -> float:
        equity = ev - net_debt
        return equity / shares
    
    return {
        "symbol": symbol.upper(),
        "iterations": result.iterations,
        "valid_simulations": result.valid_simulations,
        "enterprise_value": {
            "mean": result.mean,
            "std_dev": result.std_dev,
            "percentiles": result.percentiles,
        },
        "per_share": {
            "mean": ev_to_per_share(result.mean),
            "percentiles": {
                k: ev_to_per_share(v) for k, v in result.percentiles.items()
            },
        },
        "inputs": {
            "base_revenue": base_revenue,
            "base_growth": request.base_growth,
            "growth_std": request.growth_std,
            "base_margin": request.base_margin,
            "margin_std": request.margin_std,
            "base_discount_rate": request.base_discount_rate,
            "discount_std": request.discount_std,
            "terminal_growth": request.terminal_growth,
            "projection_years": request.projection_years,
        },
    }


@router.post("/{symbol}/monte-carlo-full")
async def run_full_monte_carlo_endpoint(
    symbol: str,
    request: FullMonteCarloRequest,
    provider: str = "yahoo",
):
    """
    Run Full-Model Monte Carlo simulation using complete DCF engine.
    
    This is the DECISION-GRADE Monte Carlo that:
    1. Uses FCFProjector for proper FCF calculations (NOPAT + D&A - CapEx - ΔWC)
    2. Samples ALL DCF inputs with bounded distributions
    3. Implements correlations between inputs (growth↔margin, growth↔reinvestment)
    4. Computes comprehensive decision-support outputs
    
    Use this for actual investment decisions.
    Use /monte-carlo (simplified) for quick intuition only.
    """
    actual_provider = provider
    if rate_limiter.is_api_limited(provider):
        actual_provider = "yahoo"
    
    client = get_client_for_provider(actual_provider)
    rate_limiter.record_call(actual_provider)
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
    except (RateLimitError, DataNotAvailableError) as e:
        if actual_provider != "yahoo":
            client = get_client_for_provider("yahoo")
            rate_limiter.record_call("yahoo")
            try:
                stock_data = await client.get_stock_data(symbol.upper())
                actual_provider = "yahoo"
            except Exception:
                raise HTTPException(status_code=429, detail=f"Rate limit exceeded for {provider}")
        else:
            raise HTTPException(status_code=429, detail=str(e))
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    data = stock_data_to_legacy(stock_data)
    extractor = DataExtractor(data)
    
    revenue_history = extractor.revenue_history()
    ebit_history = extractor.ebit_history()
    da_history = extractor.da_history()
    capex_history = extractor.capex_history()
    wc_history = extractor.working_capital_history()
    
    if not revenue_history or len(revenue_history) < 2:
        raise HTTPException(status_code=400, detail="Insufficient historical data for full Monte Carlo")
    
    if not ebit_history or len(ebit_history) < len(revenue_history):
        ebit_history = [r * request.base_margin for r in revenue_history]
    if not da_history or len(da_history) < len(revenue_history):
        da_history = [r * request.base_da_ratio for r in revenue_history]
    if not capex_history or len(capex_history) < len(revenue_history):
        capex_history = [r * request.base_capex_ratio for r in revenue_history]
    if not wc_history or len(wc_history) < len(revenue_history):
        wc_history = [r * request.base_wc_ratio for r in revenue_history]
    
    shares = extractor.shares_outstanding() or 1
    total_debt = extractor.total_debt() or 0
    cash = extractor.cash() or 0
    
    current_price = stock_data.profile.price if stock_data.profile and stock_data.profile.price else 0
    if not current_price:
        market_cap = extractor.market_cap()
        if market_cap and shares:
            current_price = market_cap / shares
    
    # Convert wacc_components Pydantic model to dict if provided
    wacc_components_dict = None
    if request.wacc_components:
        wacc_components_dict = {
            "risk_free_rate": request.wacc_components.risk_free_rate,
            "beta": request.wacc_components.beta,
            "market_risk_premium": request.wacc_components.market_risk_premium,
            "cost_of_debt": request.wacc_components.cost_of_debt,
            "market_cap": request.wacc_components.market_cap,
        }
        if request.wacc_components.beta_std:
            wacc_components_dict["beta_std"] = request.wacc_components.beta_std
        if request.wacc_components.market_risk_premium_std:
            wacc_components_dict["market_risk_premium_std"] = request.wacc_components.market_risk_premium_std
    
    # Convert growth_stages Pydantic models to dicts if provided
    growth_stages_dicts = None
    if request.growth_stages:
        growth_stages_dicts = [
            {
                "name": stage.name,
                "years": stage.years,
                "growth_rate": stage.growth_rate,
                "end_growth_rate": stage.end_growth_rate,
                "growth_std": stage.growth_std,
            }
            for stage in request.growth_stages
        ]
    
    result = run_full_monte_carlo(
        historical_revenue=revenue_history,
        historical_ebit=ebit_history,
        historical_da=da_history,
        historical_capex=capex_history,
        historical_working_capital=wc_history,
        shares_outstanding=shares,
        total_debt=total_debt,
        cash=cash,
        current_price=current_price,
        base_growth=request.base_growth,
        base_margin=request.base_margin,
        base_da_ratio=request.base_da_ratio,
        base_capex_ratio=request.base_capex_ratio,
        base_wc_ratio=request.base_wc_ratio,
        base_tax_rate=request.base_tax_rate,
        base_discount_rate=request.base_discount_rate,
        base_terminal_growth=request.base_terminal_growth,
        growth_std=request.growth_std,
        margin_std=request.margin_std,
        da_ratio_std=request.da_ratio_std,
        capex_ratio_std=request.capex_ratio_std,
        wc_ratio_std=request.wc_ratio_std,
        discount_std=request.discount_std,
        terminal_growth_std=request.terminal_growth_std,
        projection_years=request.projection_years,
        iterations=request.iterations,
        growth_margin_correlation=request.growth_margin_correlation,
        growth_capex_correlation=request.growth_capex_correlation,
        wacc_components=wacc_components_dict,
        growth_stages=growth_stages_dicts,
        use_mid_year_discounting=request.use_mid_year_discounting,
    )
    
    return {
        "symbol": symbol.upper(),
        "mode": "full",
        "current_price": current_price,
        "iterations": result.iterations,
        "valid_simulations": result.valid_simulations,
        "per_share": {
            "mean": result.mean,
            "median": result.median,
            "std_dev": result.std_dev,
            "percentiles": result.percentiles,
        },
        "decision_metrics": {
            "probability_positive_upside": result.probability_positive_upside,
            "probability_20pct_upside": result.probability_20pct_upside,
            "probability_20pct_downside": result.probability_20pct_downside,
            "cvar_10": result.cvar_10,
            "margin_of_safety_mean": result.margin_of_safety_mean,
            "margin_of_safety_median": result.margin_of_safety_median,
        },
        "inputs": {
            "base_growth": request.base_growth,
            "base_margin": request.base_margin,
            "base_da_ratio": request.base_da_ratio,
            "base_capex_ratio": request.base_capex_ratio,
            "base_wc_ratio": request.base_wc_ratio,
            "base_tax_rate": request.base_tax_rate,
            "base_discount_rate": request.base_discount_rate,
            "base_terminal_growth": request.base_terminal_growth,
            "projection_years": request.projection_years,
            "correlations": {
                "growth_margin": request.growth_margin_correlation,
                "growth_capex": request.growth_capex_correlation,
            },
        },
    }
