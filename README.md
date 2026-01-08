# Stock Analysis Platform

A comprehensive stock valuation and analysis tool combining DCF modeling, technical analysis, and investment memo tracking.

## Overview

This platform provides professional-grade equity analysis capabilities:

- **DCF Valuation** — Revenue-driven free cash flow projections with WACC calculation
- **Scenario Analysis** — Bull/Base/Bear cases with sensitivity tables
- **Technical Analysis** — Price trends, moving averages, and momentum indicators
- **Investment Memos** — Track investment theses with performance monitoring
- **Multi-Provider Support** — FMP, Yahoo Finance, and Massive with automatic fallback

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- API key from [Financial Modeling Prep](https://financialmodelingprep.com/)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set API key
export FMP_API_KEY=your_key_here

# Run server
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`

## Features

### Fundamental Analysis

| Feature | Description |
|---------|-------------|
| DCF Model | NOPAT-based FCF projections with terminal value |
| WACC Calculator | CAPM cost of equity + after-tax cost of debt |
| Scenario Manager | Compare bull/base/bear valuations side by side |
| Sensitivity Analysis | WACC vs terminal growth matrix |
| Historical Hints | Auto-populated assumptions from financial history |
| Financial Ratios | Profitability, liquidity, leverage metrics |
| Comparable Analysis | P/E, EV/EBITDA, P/S, P/B vs sector peers |

### Technical Analysis

| Feature | Description |
|---------|-------------|
| Trend Analysis | 52-week range, moving averages, momentum |
| Volume Analysis | Average volume, relative volume |
| Support/Resistance | Key price levels identification |

### Investment Tracking

| Feature | Description |
|---------|-------------|
| Investment Memos | Document thesis, assumptions, catalysts, risks |
| Performance Tracking | Entry price vs current, return calculation |
| Post-Mortems | Track decisions and learnings over time |
| Assumption Audit Trail | Version history of DCF inputs with notes |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│                   React + TypeScript                        │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Analysis│  │  Memos  │  │ Glossary│  │ Layout  │       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
        └────────────┴─────┬──────┴────────────┘
                           │
                    ┌──────▼──────┐
                    │   REST API  │
                    │   FastAPI   │
                    └──────┬──────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                          │           Backend                │
│         ┌────────────────┼────────────────┐                │
│         │                │                │                │
│   ┌─────▼─────┐   ┌──────▼──────┐   ┌─────▼─────┐         │
│   │ Valuation │   │   Memos     │   │ Technical │         │
│   │  Service  │   │ Repository  │   │  Service  │         │
│   └─────┬─────┘   └──────┬──────┘   └─────┬─────┘         │
│         │                │                │                │
│   ┌─────▼─────┐   ┌──────▼──────┐   ┌─────▼─────┐         │
│   │    DCF    │   │   SQLite    │   │ Indicators│         │
│   │ Calculator│   │  Database   │   │ Calculator│         │
│   └─────┬─────┘   └─────────────┘   └───────────┘         │
│         │                                                  │
│   ┌─────▼─────────────────────────────────────────┐       │
│   │              Data Providers                    │       │
│   │  ┌───────┐  ┌───────┐  ┌───────┐             │       │
│   │  │  FMP  │  │ Yahoo │  │Massive│             │       │
│   │  └───────┘  └───────┘  └───────┘             │       │
│   └───────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────┘
```

## Project Structure

```
stock-screens/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── models/              # Data models
│   │   │   ├── assumption_audit.py
│   │   │   └── memo.py
│   │   └── services/            # Business logic
│   │       ├── valuation_service.py
│   │       ├── dcf_calculator.py
│   │       ├── wacc_calculator.py
│   │       ├── fcf_projector.py
│   │       ├── scenario_calculator.py
│   │       ├── sensitivity_calculator.py
│   │       ├── technical_service.py
│   │       ├── memo_repository.py
│   │       ├── audit_repository.py
│   │       ├── fmp_provider.py
│   │       ├── yahoo_provider.py
│   │       └── ...
│   ├── tests/                   # Pytest test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main application
│   │   ├── components/          # React components
│   │   │   ├── Layout.tsx
│   │   │   ├── MemosPage.tsx
│   │   │   ├── MemoDetailPage.tsx
│   │   │   ├── GlossaryPage.tsx
│   │   │   └── ...
│   │   ├── hooks/               # Custom hooks
│   │   └── types.ts             # TypeScript types
│   └── package.json
└── docs/                        # Documentation
```

## Documentation

- [API Reference](docs/API.md) — Full endpoint documentation
- [Architecture](docs/ARCHITECTURE.md) — System design and data flow
- [Development Guide](docs/DEVELOPMENT.md) — Setup, testing, contributing
- [DCF Model](docs/DCF_MODEL.md) — Valuation methodology explained

## Testing

### Backend

```bash
cd backend
source venv/bin/activate
pytest -v
```

64+ tests covering services, calculators, and API endpoints.

### Frontend

```bash
cd frontend
npm test
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.12, FastAPI, SQLite |
| Data | FMP API, Yahoo Finance, Massive |
| Testing | Pytest (backend), Vitest (frontend) |

## License

MIT
