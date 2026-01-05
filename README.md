# Stock Valuation Tool

DCF analysis for stock valuation with proper fundamental projections.

## Features

- **Proper DCF Model**: Revenue-driven FCF projections
- **WACC Calculator**: Cost of equity (CAPM) + after-tax cost of debt
- **Historical Hints**: Shows past performance as reference
- **User Assumptions**: You control growth, margins, and risk premium

## Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: React, TypeScript, Vite
- **Data**: Financial Modeling Prep API

## Quick Start

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set your FMP API key
export FMP_API_KEY=your_key_here

# Run server
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`

## API Endpoints

### GET /api/stock/{symbol}

Returns company data and historical hints.

```json
{
  "symbol": "AAPL",
  "company_name": "Apple Inc.",
  "data": {
    "beta": 1.25,
    "market_cap": 3000000000000,
    "total_debt": 111088000000,
    "cash": 29965000000,
    "tax_rate": 0.147,
    "risk_free_rate": 0.045
  },
  "hints": {
    "revenue_growth": 0.024,
    "operating_margin": 0.298
  }
}
```

### POST /api/stock/{symbol}/valuation

Run DCF with your assumptions.

```json
{
  "revenue_growth": 0.10,
  "operating_margin": 0.30,
  "terminal_growth_rate": 0.03,
  "market_risk_premium": 0.06,
  "projection_years": 5
}
```

Returns intrinsic value per share and full breakdown.

## DCF Model

```
FCF = NOPAT + D&A - CapEx - ΔWorking Capital
```

Where:
- NOPAT = EBIT × (1 - Tax Rate)
- Terminal Value = Final FCF × (1 + g) / (WACC - g)
- Equity Value = Enterprise Value - Net Debt
- Intrinsic Value = Equity Value / Shares Outstanding
