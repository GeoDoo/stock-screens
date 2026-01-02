# Stock Screener

A value investing tool for fundamental and technical analysis with margin of safety calculations.

## Features

- **Valuation Analysis**: Graham's formula, DCF, Asset-based, and Earnings Power Value (EPV)
- **Technical Indicators**: SMA, RSI, MACD, Bollinger Bands, ATR, Volume analysis
- **Stock Screening**: Predefined screens (Graham Defensive, Deep Value) + custom filters
- **Spinoff Detection**: Automated SEC EDGAR monitoring with alerts
- **Watchlist**: Track stocks with notes and target prices
- **Data Quality**: Shows warnings for missing data

## Tech Stack

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy (async) + SQLite
- yfinance for market data
- APScheduler for background jobs

### Frontend
- React 18 + TypeScript
- TanStack Query
- Recharts
- Lucide icons

## Getting Started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm start
```

App will be available at `http://localhost:3000`

## API Endpoints

### Watchlist
- `GET /api/watchlist` - Get all watchlist items
- `POST /api/watchlist` - Add stock to watchlist
- `DELETE /api/watchlist/{symbol}` - Remove from watchlist
- `GET /api/watchlist/{symbol}/notes` - Get notes for a stock
- `POST /api/watchlist/{symbol}/notes` - Add note

### Screening
- `GET /api/screening/screens` - List predefined screens
- `GET /api/screening/screens/{id}` - Get screen details

### Spinoffs
- `GET /api/spinoffs` - List tracked spinoffs
- `GET /api/spinoffs/alerts` - Get unread alerts
- `POST /api/spinoffs/alerts/{id}/read` - Mark alert as read

### Health
- `GET /health` - Health check

## Predefined Screens

| Screen | Criteria |
|--------|----------|
| Graham Defensive | P/E < 15, P/B < 1.5, Current Ratio > 2 |
| Graham Enterprising | P/E < 20, P/B < 2.5, Current Ratio > 1.5 |
| Low Debt High ROE | D/E < 0.5, ROE > 15% |
| Deep Value | P/E < 10, P/B < 1 |

## Valuation Methods

### Graham's Formula
```
V = EPS × (8.5 + 2g) × 4.4 / Y
```
Where g = growth rate, Y = AAA bond yield

### DCF
Projects free cash flows and discounts to present value using WACC.

### Asset-Based
```
NAV = Total Assets - Total Liabilities
```

### Earnings Power Value
```
EPV = Normalized Earnings / Cost of Capital
```

## Testing

```bash
cd backend
pytest tests/ -v
```

## License

MIT

