# Architecture

> **Auto-generated** from source code structure.
> 
> Last updated: 2026-01-09 18:31
> 
> Do not edit manually. Run `python scripts/generate_all_docs.py` to regenerate.

## Overview

Stock Screens is a full-stack stock analysis application with:
- **Backend**: FastAPI (Python) - DCF valuation, financial analysis
- **Frontend**: React + TypeScript + Vite - Interactive UI
- **Database**: SQLite - Rate limits, audit trails, memos

## Backend Architecture

### Services (`backend/app/services/`)

| Service | Purpose |
|---------|---------|
| `audit_repository.py` | SQLite-based repository for assumption audit entries. |
| `base_provider.py` | Standardized company profile data. |
| `cache.py` | Simple in-memory cache with TTL and size limits. |
| `capital_efficiency.py` | Calculator for capital efficiency metrics. |
| `comparable_analyzer.py` | Key valuation metrics for a company. |
| `data_adapter.py` | — |
| `data_extractor.py` | Extracts financial metrics from FMP data for use in valuatio |
| `data_validator.py` | Severity levels for validation issues. |
| `database.py` | — |
| `dcf_calculator.py` | Discounted Cash Flow calculator with optional mid-year disco |
| `dividend_analyzer.py` | A single dividend payment. |
| `fcf_projector.py` | Projects Free Cash Flow from first principles. |
| `fmp_client.py` | Custom exception for FMP API errors. |
| `fmp_provider.py` | Financial Modeling Prep data provider. |
| `historical_valuation.py` | Valuation metrics for a single year. |
| `massive_provider.py` | Massive (Polygon.io) data provider. |
| `memo_repository.py` | SQLite-based repository for investment memos. |
| `monte_carlo.py` | Configuration for a single Monte Carlo input variable. |
| `monte_carlo_full.py` | Input parameter with bounded distribution. |
| `multi_stage_growth.py` | A single growth phase in a multi-stage model. |
| `rate_limiter_sqlite.py` | When the rate limit resets. |
| `ratio_calculator.py` | Valuation metrics. |
| `scenario_calculator.py` | A single scenario with its assumptions. |
| `sensitivity_calculator.py` | Calculates sensitivity matrix for DCF valuation. |
| `stock_data_client.py` | Smart stock data client with automatic fallback between prov |
| `technical_indicators.py` | Single indicator data point. |
| `technical_service.py` | Service for running technical analysis on a stock. |
| `valuation_service.py` | Orchestrates the full DCF valuation: |
| `wacc_calculator.py` | Weighted Average Cost of Capital calculator. |
| `yahoo_provider.py` | Yahoo Finance data provider using yfinance library. |

### Key Services Detail

#### `data_extractor.py` - DataExtractor

Extracts financial metrics from FMP data for use in valuation models.

**Key Methods:**
- `is_using_ltm()` - Check if LTM/TTM data is available for flow items.
- `beta()` - Stock beta from profile.
- `market_cap()` - Market capitalization from profile.
- `sector()` - Company sector from profile (e.g., 'Technology', 'Financial Services').
- `industry()` - Company industry from profile (e.g., 'Software—Application', 'Banks—Regional').

#### `dcf_calculator.py` - DCFCalculator

Discounted Cash Flow calculator with optional mid-year discounting.

**Key Methods:**
- `calculate()` - Calculate intrinsic value per share using DCF model.

#### `fcf_projector.py` - FCFProjector

Projects Free Cash Flow from first principles.

**Key Methods:**
- `effective_tax_rate()` - Return tax rate or default if not available.
- `revenue_cagr()` - Calculate Compound Annual Growth Rate of revenue.
- `operating_margin()` - Calculate average operating margin (EBIT / Revenue).
- `da_to_revenue_ratio()` - Calculate average D&A as percentage of revenue.
- `capex_to_revenue_ratio()` - Calculate average CapEx as percentage of revenue.

#### `monte_carlo.py` - MonteCarloInput

Configuration for a single Monte Carlo input variable.

**Key Methods:**
- `sample()` - Draw a random sample for this input.

#### `valuation_service.py` - ValuationService

Orchestrates the full DCF valuation:

#### `wacc_calculator.py` - WACCCalculator

Weighted Average Cost of Capital calculator.

**Key Methods:**
- `cost_of_equity()` - Calculate cost of equity using CAPM.
- `after_tax_cost_of_debt()` - Calculate after-tax cost of debt.
- `calculate()` - Calculate WACC.

## Frontend Architecture

### Components (`frontend/src/components/`)

| Component | Description |
|-----------|-------------|
| `AssumptionCommitModal.tsx` | AssumptionCommitModal |
| `AssumptionHistoryDrawer.tsx` | AssumptionHistoryDrawer |
| `AssumptionHistoryIndicator.tsx` | AssumptionHistoryIndicator |
| `DiscountRateModal.tsx` | DiscountRateModal |
| `FinancialRatiosTable.tsx` | FinancialRatiosTable |
| `GlossaryPage.tsx` | GlossaryPage |
| `GlossaryRef.tsx` | GlossaryRef |
| `Layout.tsx` | Layout |
| `MemoCreateModal.tsx` | MemoCreateModal |
| `MemoDetailPage.tsx` | MemoDetailPage |
| `MemoDetailView.tsx` | MemoDetailView |
| `MemosPage.tsx` | MemosPage |
| `MonteCarloPanel.tsx` | MonteCarloPanel |
| `MultiStageGrowth.tsx` | MultiStageGrowth |

### Hooks (`frontend/src/hooks/`)

| Hook | Purpose |
|------|---------|
| `useAssumptionTracker.ts` | Assumptiontracker |
| `useProviders.ts` | Providers |
| `useStockAnalysis.ts` | Stockanalysis |

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│  Providers  │
│   (React)   │◀────│   Backend   │◀────│ (FMP/Yahoo) │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌─────────┐  ┌─────────────┐
              │ SQLite  │  │ Calculators │
              │   DB    │  │  & Models   │
              └─────────┘  └─────────────┘
```

## Test Coverage

| Layer | Test Files | Framework |
|-------|------------|-----------|
| Backend | 31 test files | pytest |
| Frontend | 13 test files | vitest |

## Constants (`backend/app/constants.py`)

All magic numbers are centralized:
- `DEFAULT_TREASURY_RATE` - Risk-free rate fallback
- `DEFAULT_TAX_RATE` - Tax rate when data missing
- `DEFAULT_MARKET_RISK_PREMIUM` - Historical market premium
- `DEFAULT_TERMINAL_GROWTH` - Long-term GDP growth
