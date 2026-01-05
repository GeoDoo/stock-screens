import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv

from app.services.stock_data_client import StockDataClient
from app.services.data_adapter import stock_data_to_legacy
from app.services.base_provider import ProviderError, TickerNotFoundError, DataNotAvailableError
from app.services.data_extractor import DataExtractor
from app.services.valuation_service import ValuationService
from app.services.fcf_projector import FCFProjector
from app.services.data_validator import DataValidator
from app.services.wacc_calculator import WACCCalculator

load_dotenv()

app = FastAPI(title="Stock Screens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get API key from environment
FMP_API_KEY = os.getenv("FMP_API_KEY", "")


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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/stock/{symbol}", response_model=StockDataResponse)
async def get_stock(symbol: str):
    """
    Get stock data and historical hints.
    
    Uses multiple data providers with automatic fallback:
    1. FMP (Financial Modeling Prep) - primary
    2. Yahoo Finance - fallback for tickers not on FMP
    
    Returns:
    - data: Read-only values (beta, debt, cash, etc.)
    - hints: Historical averages for reference (user decides what to use)
    """
    client = StockDataClient(fmp_api_key=FMP_API_KEY if FMP_API_KEY else None)
    
    try:
        stock_data = await client.get_stock_data(symbol.upper())
        risk_free_rate = await client.get_treasury_rate()
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
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

    # Calculate WACC for display
    beta = extractor.beta()
    cost_of_debt = extractor.cost_of_debt()
    tax_rate = extractor.tax_rate()
    market_cap = extractor.market_cap()
    total_debt = extractor.total_debt()
    
    wacc = None
    if beta is not None and market_cap is not None:
        wacc_calculator = WACCCalculator(
            risk_free_rate=risk_free_rate,
            beta=beta,
            market_risk_premium=0.06,  # Default
            cost_of_debt=cost_of_debt if cost_of_debt is not None else 0.05,
            tax_rate=tax_rate if tax_rate is not None else 0.25,
            market_cap=market_cap,
            total_debt=total_debt if total_debt is not None else 0,
        )
        wacc = wacc_calculator.calculate()

    return StockDataResponse(
        symbol=symbol.upper(),
        company_name=data.get("profile", {}).get("companyName"),
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
async def run_valuation(symbol: str, request: ValuationRequest):
    """
    Run DCF valuation with user-provided assumptions.
    
    ALL assumptions must be provided by the user.
    """
    if not FMP_API_KEY:
        raise HTTPException(status_code=500, detail="FMP_API_KEY not configured")

    service = ValuationService(api_key=FMP_API_KEY)

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
