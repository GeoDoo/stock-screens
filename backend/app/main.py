import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv

from app.services.fmp_client import FMPClient
from app.services.data_extractor import DataExtractor
from app.services.valuation_service import ValuationService
from app.services.fcf_projector import FCFProjector

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


class ValuationRequest(BaseModel):
    projection_years: int = 5
    terminal_growth_rate: float = 0.03
    revenue_growth: Optional[float] = None
    operating_margin: Optional[float] = None
    market_risk_premium: Optional[float] = None


class StockInputs(BaseModel):
    symbol: str
    # From data
    beta: Optional[float]
    market_cap: Optional[float]
    total_debt: Optional[float]
    cash: Optional[float]
    tax_rate: Optional[float]
    cost_of_debt: Optional[float]
    shares_outstanding: Optional[float]
    risk_free_rate: float
    # Calculated from historical
    revenue_growth: Optional[float]
    operating_margin: Optional[float]
    da_ratio: Optional[float]
    capex_ratio: Optional[float]
    wc_ratio: Optional[float]
    # Assumptions with defaults
    market_risk_premium: float
    terminal_growth_rate: float = 0.03
    projection_years: int = 5


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/stock/{symbol}/inputs", response_model=StockInputs)
async def get_stock_inputs(symbol: str):
    """
    Get calculated inputs and assumptions for a stock.
    User can review these before running valuation.
    """
    if not FMP_API_KEY:
        raise HTTPException(status_code=500, detail="FMP_API_KEY not configured")

    fmp_client = FMPClient(api_key=FMP_API_KEY)
    
    try:
        data = await fmp_client.get_stock_data(symbol.upper())
        risk_free_rate = await fmp_client.get_treasury_rate()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching data: {str(e)}")

    extractor = DataExtractor(data)

    # Calculate historical ratios
    fcf_projector = FCFProjector(
        historical_revenue=extractor.revenue_history() or [0],
        historical_ebit=extractor.ebit_history() or [0],
        historical_da=extractor.da_history() or [0],
        historical_capex=extractor.capex_history() or [0],
        historical_working_capital=extractor.working_capital_history() or [0],
        tax_rate=extractor.tax_rate() or 0.25,
    )

    return StockInputs(
        symbol=symbol.upper(),
        beta=extractor.beta(),
        market_cap=extractor.market_cap(),
        total_debt=extractor.total_debt(),
        cash=extractor.cash(),
        tax_rate=extractor.tax_rate(),
        cost_of_debt=extractor.cost_of_debt(),
        shares_outstanding=extractor.shares_outstanding(),
        risk_free_rate=risk_free_rate,
        revenue_growth=fcf_projector.revenue_cagr() if extractor.revenue_history() else None,
        operating_margin=fcf_projector.operating_margin() if extractor.ebit_history() else None,
        da_ratio=fcf_projector.da_to_revenue_ratio() if extractor.da_history() else None,
        capex_ratio=fcf_projector.capex_to_revenue_ratio() if extractor.capex_history() else None,
        wc_ratio=fcf_projector.wc_to_revenue_ratio() if extractor.working_capital_history() else None,
        market_risk_premium=extractor.market_risk_premium(),
    )


@app.post("/api/stock/{symbol}/valuation")
async def run_valuation(symbol: str, request: ValuationRequest):
    """
    Run DCF valuation with user-provided assumptions.
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
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Valuation error: {str(e)}")

    return result
