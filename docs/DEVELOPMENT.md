# Development Guide

> **Auto-generated** from package files.
> 
> Last updated: 2026-01-09 10:38
> 
> Do not edit manually. Run `python scripts/generate_all_docs.py` to regenerate.

## Prerequisites

- Python 3.12+
- Node.js 18+
- npm 9+

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Backend Dependencies

| Package | Version |
|---------|---------|
| `fastapi` | 0.109.0 |
| `uvicorn` | 0.27.0 |
| `httpx` | 0.26.0 |
| `python-dotenv` | 1.0.0 |
| `pytest` | 8.0.0 |
| `pytest-asyncio` | 0.21.0 |
| `yfinance` | latest |

## Frontend Dependencies

| Package | Version |
|---------|---------|
| `react` | ^19.2.0 |
| `react-dom` | ^19.2.0 |
| `react-router-dom` | ^7.12.0 |

## Running Tests

### Backend Tests (28 test files)

```bash
cd backend
source venv/bin/activate
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --tb=short -q      # Quick summary
pytest tests/test_api.py  # Specific file
```

### Frontend Tests (13 test files)

```bash
cd frontend
npm test                  # Watch mode
npm test -- --run         # Single run
npm test -- --coverage    # With coverage
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FMP_API_KEY` | Optional | Financial Modeling Prep API key |

## Database

SQLite database at `backend/stock_screens.db`:
- `rate_limits` - API call tracking
- `audit_trail` - Assumption change history
- `memos` - Investment memos

## Documentation

All docs are auto-generated:

```bash
python scripts/generate_all_docs.py
```

This regenerates:
- `docs/API.md` - API endpoints
- `docs/ARCHITECTURE.md` - Code structure
- `docs/DCF_MODEL.md` - Valuation math
- `docs/DEVELOPMENT.md` - This file

## Pre-commit Hook

Documentation auto-updates on every commit:

```bash
# .git/hooks/pre-commit runs:
python scripts/generate_all_docs.py
git add docs/*.md
```

## Code Style

- **Backend**: Python with type hints, docstrings required
- **Frontend**: TypeScript strict mode, ESLint
- **Tests**: TDD approach, all new code must have tests
