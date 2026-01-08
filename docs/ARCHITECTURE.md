# Architecture

## Overview

The Stock Analysis Platform follows a clean separation of concerns with a React frontend communicating with a FastAPI backend. Data is fetched from external providers and persisted locally in SQLite.

## System Components

### Frontend (React + TypeScript)

```
frontend/src/
├── main.tsx              # Router and app entry
├── App.tsx               # Main analysis page
├── components/
│   ├── Layout.tsx        # Shared layout with sidebar navigation
│   ├── MemosPage.tsx     # Investment memos list
│   ├── MemoDetailPage.tsx # Single memo view
│   ├── GlossaryPage.tsx  # Financial terms glossary
│   ├── MemoCreateModal.tsx
│   ├── DiscountRateModal.tsx
│   ├── AssumptionHistoryDrawer.tsx
│   ├── AssumptionCommitModal.tsx
│   ├── FinancialRatiosTable.tsx
│   └── GlossaryRef.tsx
├── hooks/
│   └── useAssumptionTracker.ts
├── types.ts              # TypeScript interfaces
├── glossary.ts           # Financial term definitions
├── normalizers.ts        # API response normalization
├── providerFallback.ts   # Provider fallback logic
└── utils.ts              # Formatting utilities
```

**Key Patterns:**

- **Shared Layout**: All pages use `Layout.tsx` for consistent navigation
- **Type Safety**: Strict TypeScript with defined interfaces in `types.ts`
- **Data Normalization**: All API responses pass through normalizers for consistent shape
- **Provider Fallback**: Automatic fallback from FMP to Yahoo on errors

### Backend (FastAPI + Python)

```
backend/app/
├── main.py               # FastAPI application and routes
├── constants.py          # Application constants
├── models/
│   ├── assumption_audit.py  # Audit trail data models
│   └── memo.py              # Investment memo data models
└── services/
    ├── valuation_service.py    # Orchestrates DCF valuation
    ├── dcf_calculator.py       # Core DCF math
    ├── wacc_calculator.py      # WACC calculation
    ├── fcf_projector.py        # FCF projection logic
    ├── scenario_calculator.py  # Multi-scenario analysis
    ├── sensitivity_calculator.py
    ├── ratio_calculator.py     # Financial ratios
    ├── comparable_analyzer.py  # Peer comparison
    ├── technical_service.py    # Technical analysis
    ├── technical_indicators.py
    ├── dividend_analyzer.py
    ├── historical_valuation.py
    │
    ├── stock_data_client.py    # Data fetching orchestration
    ├── data_adapter.py         # Normalizes provider responses
    ├── data_extractor.py       # Extracts fields from raw data
    ├── data_validator.py       # Validates data quality
    │
    ├── fmp_provider.py         # Financial Modeling Prep
    ├── fmp_client.py           # FMP API client
    ├── yahoo_provider.py       # Yahoo Finance
    ├── massive_provider.py     # Massive (technical)
    ├── base_provider.py        # Provider interface
    │
    ├── memo_repository.py      # Memo CRUD operations
    ├── audit_repository.py     # Audit trail storage
    ├── database.py             # SQLite connection management
    └── rate_limiter_sqlite.py  # API rate limiting
```

## Data Flow

### Valuation Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│   Provider  │
│             │     │             │     │  (FMP/Yahoo)│
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ StockData   │
                    │   Client    │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌───────────┐  ┌───────────┐  ┌───────────┐
     │   Data    │  │   Data    │  │   Data    │
     │  Adapter  │  │ Extractor │  │ Validator │
     └───────────┘  └───────────┘  └───────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Valuation   │
                    │   Service   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │    WACC     │   │     FCF     │   │     DCF     │
  │ Calculator  │   │  Projector  │   │ Calculator  │
  └─────────────┘   └─────────────┘   └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Result    │
                    │  Response   │
                    └─────────────┘
```

### Provider Fallback

```
┌──────────────────────────────────────────────────┐
│                    Frontend                       │
│                                                   │
│  1. Request with provider=fmp                    │
│                    │                              │
│                    ▼                              │
│  2. FMP returns error (rate limit/premium)       │
│                    │                              │
│                    ▼                              │
│  3. shouldFallback() → true                      │
│                    │                              │
│                    ▼                              │
│  4. getAlternativeProvider() → "yahoo"           │
│                    │                              │
│                    ▼                              │
│  5. Retry request with provider=yahoo            │
│                    │                              │
│                    ▼                              │
│  6. Display result + fallback notice             │
│                                                   │
└──────────────────────────────────────────────────┘
```

## Database Schema

All data is stored in `stock_screens.db`:

### Audit Entries

```sql
CREATE TABLE audit_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    note TEXT,
    is_initial INTEGER NOT NULL DEFAULT 0,
    price_at_time REAL,
    intrinsic_value_at_time REAL,
    pe_ratio_at_time REAL
);

CREATE TABLE audit_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    field TEXT NOT NULL,
    old_value REAL,
    new_value REAL NOT NULL,
    FOREIGN KEY (entry_id) REFERENCES audit_entries(id)
);
```

### Investment Memos

```sql
CREATE TABLE memos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    thesis TEXT NOT NULL,
    conviction TEXT NOT NULL,
    time_horizon_months INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    target_price REAL,
    catalysts TEXT,
    risks TEXT,
    what_would_change_mind TEXT,
    assumptions_json TEXT NOT NULL,
    scenarios_json TEXT,
    initial_market_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    closed_at TEXT,
    closed_reason TEXT
);

CREATE TABLE memo_post_mortems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memo_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    content TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    market_snapshot_json TEXT,
    FOREIGN KEY (memo_id) REFERENCES memos(id)
);

CREATE TABLE memo_market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memo_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    price REAL NOT NULL,
    intrinsic_value REAL,
    pe_ratio REAL,
    FOREIGN KEY (memo_id) REFERENCES memos(id)
);
```

### Rate Limits

```sql
CREATE TABLE rate_limits (
    provider TEXT PRIMARY KEY,
    calls_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## Key Design Decisions

### 1. Clean TTM/Annual Separation

All DCF inputs can come from either TTM (trailing twelve months) or annual data. The frontend passes explicit ratios to ensure consistency:

```python
# Backend accepts explicit ratios
class ValuationRequest(BaseModel):
    revenue_growth: float
    operating_margin: float
    da_ratio: Optional[float] = None      # D&A / Revenue
    capex_ratio: Optional[float] = None   # CapEx / Revenue
    wc_ratio: Optional[float] = None      # ΔWC / Revenue
```

### 2. Provider Abstraction

All data providers implement a common interface:

```python
class BaseProvider:
    async def get_company_data(self, symbol: str) -> dict:
        raise NotImplementedError
    
    async def get_financial_statements(self, symbol: str) -> dict:
        raise NotImplementedError
```

### 3. Data Normalization

Raw API responses are normalized to a consistent shape:

```typescript
// Frontend normalizer
function normalizeStockData(raw: any): StockDataResponse {
  return {
    symbol: raw.symbol,
    company_name: raw.company_name || raw.companyName,
    // ... consistent field mapping
  };
}
```

### 4. Assumption Audit Trail

Every valuation run can record assumption changes:

```
User changes revenue_growth: 8% → 10%
         │
         ▼
┌─────────────────────────────────────┐
│ AuditEntry                          │
│ - timestamp: 2024-01-15 10:30:00   │
│ - changes: [{revenue_growth: 8→10}]│
│ - note: "Updated for Q4 guidance"  │
│ - price_at_time: $178.50           │
│ - intrinsic_value: $185.50         │
└─────────────────────────────────────┘
```

### 5. Investment Memo Lifecycle

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│ Create  │────▶│  Open   │────▶│ Closed  │
│  Memo   │     │ Status  │     │ Status  │
└─────────┘     └────┬────┘     └─────────┘
                     │
                     ▼
              ┌─────────────┐
              │ Post-Mortems│
              │ (ongoing)   │
              └─────────────┘
```

## Error Handling

### Backend

```python
from fastapi import HTTPException

# Validation errors
if not data:
    raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

# Provider errors
try:
    result = await provider.fetch(symbol)
except RateLimitError:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### Frontend

```typescript
// API errors trigger fallback
const response = await fetch(url);
if (!response.ok) {
  const error = await response.json();
  if (shouldFallback(error, provider)) {
    return retryWithFallback(request);
  }
  throw new Error(error.detail);
}
```

## Testing Strategy

### Backend (Pytest)

- **Unit tests**: Individual calculators and services
- **Integration tests**: API endpoints with mocked providers
- **Repository tests**: Database operations with temp databases

```bash
pytest tests/ -v
```

### Frontend (Vitest)

- **Component tests**: Render and interaction testing
- **Hook tests**: Custom hook behavior
- **Utility tests**: Formatters and normalizers

```bash
npm test
```
